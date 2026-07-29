"""
Agents Module Routes
Agent CRUD + domain-based matching
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.db.database import async_session_factory
from app.modules.agents.models import Agent
from app.core.utils import get_current_user_id
from app.api.auth import get_current_user

router = APIRouter()


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    agent_key: Optional[str] = None
    role: Optional[str] = None
    instructions: Optional[str] = None
    domain_tags: List[str] = Field(default_factory=list)
    scope: str = Field("project")
    project_id: Optional[int] = None


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    agent_key: Optional[str] = None
    role: Optional[str] = None
    instructions: Optional[str] = None
    domain_tags: Optional[List[str]] = None
    is_active: Optional[bool] = None


async def get_db():
    async with async_session_factory() as session:
        yield session


def _scope_filter(model, scope: str, user_id: str = None, project_id: int = None):
    if not scope:
        return True
    if scope == "global":
        return model.scope == "global"
    elif scope == "personal":
        return and_(model.scope == "personal", model.user_id == user_id)
    elif scope == "project":
        return and_(model.scope == "project", model.project_id == project_id)
    return model.scope == scope


@router.get("/list")
async def list_agents(
    scope: str = Query("project"),
    project_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = get_current_user_id(user)
    query = select(Agent).where(and_(Agent.deleted_at.is_(None)))
    if scope:
        query = query.where(_scope_filter(Agent, scope, user_id, project_id))
    if search:
        p = f"%{search}%"
        query = query.where(or_(Agent.name.ilike(p), Agent.agent_key.ilike(p)))
    query = query.order_by(desc(Agent.created_at)).limit(100)
    result = await db.execute(query)
    return {"items": [a.to_dict() for a in result.scalars().all()]}


@router.post("/create")
async def create_agent(
    data: AgentCreate,
    project_id: Optional[int] = Query(None),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = get_current_user_id(user)
    agent = Agent(
        name=data.name,
        agent_key=data.agent_key or data.name.lower().replace(" ", "-"),
        role=data.role,
        instructions=data.instructions,
        domain_tags=json.dumps(data.domain_tags),
        scope=data.scope,
        project_id=project_id or data.project_id,
        user_id=user_id if data.scope == "personal" else None,
        source="manual",
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent.to_dict()


@router.get("/templates/list")
async def list_templates(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Agent).where(
            and_(Agent.deleted_at.is_(None), Agent.is_template == True)
        )
    )
    return {"items": [a.to_dict() for a in result.scalars().all()]}


@router.get("/match")
async def match_agent(
    domains: str = Query(""),
    project_id: int = Query(0),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """根据意图领域匹配最合适的 Agent"""
    domain_list = [d.strip() for d in domains.split(",") if d.strip()]
    if not domain_list or not project_id:
        return {"matched": None, "fallback": True}

    result = await db.execute(
        select(Agent).where(
            and_(Agent.deleted_at.is_(None), Agent.is_active == True,
                 and_(Agent.scope == "project", Agent.project_id == project_id))
        )
    )
    agents = result.scalars().all()

    best, best_score = None, 0
    for a in agents:
        agent_domains = json.loads(a.domain_tags) if a.domain_tags else []
        score = len(set(agent_domains) & set(domain_list))
        if score > best_score:
            best_score, best = score, a

    return {
        "matched": best.to_dict() if best else None,
        "score": best_score,
        "fallback": best is None,
    }


@router.get("/{agent_id}")
async def get_agent(
    agent_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Agent).where(and_(Agent.id == agent_id, Agent.deleted_at.is_(None)))
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(404, "Agent not found")
    return agent.to_dict()


@router.put("/{agent_id}")
async def update_agent(
    agent_id: str,
    data: AgentUpdate,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Agent).where(and_(Agent.id == agent_id, Agent.deleted_at.is_(None)))
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(404, "Agent not found")

    for f in ["name", "agent_key", "role", "instructions", "is_active"]:
        v = getattr(data, f)
        if v is not None:
            setattr(agent, f, v)
    if data.domain_tags is not None:
        agent.domain_tags = json.dumps(data.domain_tags)

    # Sync to agent_instructions
    await _sync_to_instructions(db, agent)

    await db.commit()
    await db.refresh(agent)
    return agent.to_dict()


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Agent).where(and_(Agent.id == agent_id, Agent.deleted_at.is_(None)))
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(404, "Agent not found")
    from datetime import datetime, timezone
    agent.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return {"success": True}


@router.get("/stats")
async def get_stats(
    project_id: Optional[int] = Query(None),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    base = select(func.count(Agent.id)).where(Agent.deleted_at.is_(None))
    if project_id:
        base = base.where(Agent.project_id == project_id)

    total = await db.execute(base)
    by_scope = await db.execute(
        select(Agent.scope, func.count(Agent.id)).where(Agent.deleted_at.is_(None)).group_by(Agent.scope)
    )
    by_source = await db.execute(
        select(Agent.source, func.count(Agent.id)).where(Agent.deleted_at.is_(None)).group_by(Agent.source)
    )
    return {
        "total": total.scalar() or 0,
        "by_scope": {r[0]: r[1] for r in by_scope.all()},
        "by_source": {r[0]: r[1] for r in by_source.all()},
    }


async def _sync_to_instructions(db: AsyncSession, agent: Agent):
    """同步 Agent 配置到 agent_instructions 表"""
    try:
        from app.models.instructions import AgentInstruction
        result = await db.execute(
            select(AgentInstruction).where(
                AgentInstruction.project_id == (agent.project_id or 0),
                AgentInstruction.agent_type == agent.agent_key,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.role = agent.role
            existing.constraints = {}
            existing.rules = [r.strip() for r in (agent.instructions or "").split("\n") if r.strip()]
        else:
            inst = AgentInstruction(
                project_id=agent.project_id or 0,
                agent_type=agent.agent_key,
                role=agent.role or "",
                constraints={},
                rules=[r.strip() for r in (agent.instructions or "").split("\n") if r.strip()],
            )
            db.add(inst)
        await db.flush()
    except Exception:
        pass