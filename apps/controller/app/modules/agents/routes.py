"""
Agents Module Routes
Agent API 路由
"""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.db.database import async_session_factory
from app.modules.agents.models import Agent, agent_skills, agent_rules, agent_knowledge
from app.modules.skills.models import Skill
from app.modules.rules.models import Rule
from app.modules.knowledge.models import KnowledgeBase
from app.core.permissions import require_permissions
from app.core.utils import get_current_user_id
from app.api.auth import get_current_user

router = APIRouter()


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    role: Optional[str] = None
    instructions: Optional[str] = None
    scope: str = Field("personal")
    parent_agent_id: Optional[str] = None
    config: Optional[dict] = Field(default_factory=dict)
    is_template: bool = False
    skill_ids: List[str] = Field(default_factory=list)
    rule_ids: List[str] = Field(default_factory=list)
    knowledge_base_ids: List[str] = Field(default_factory=list)


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    role: Optional[str] = None
    instructions: Optional[str] = None
    config: Optional[dict] = None
    is_active: Optional[bool] = None
    is_template: Optional[bool] = None
    parent_agent_id: Optional[str] = None


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        yield session


def _scope_filter(model, scope: str, user_id: str = None, project_id: int = None):
    if not scope:
        return True  # Show all scopes
    if scope == "global":
        return model.scope == "global"
    elif scope == "personal":
        return and_(model.scope == "personal", model.user_id == user_id)
    elif scope == "project":
        return and_(model.scope == "project", model.project_id == project_id)
    return model.scope == scope


# ==================== Static Routes FIRST ====================

@router.get("/list")
async def list_agents(
    scope: str = Query("personal"),
    project_id: Optional[int] = Query(None),
    is_template: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    user_id = get_current_user_id(user)
    query = select(Agent).where(and_(Agent.deleted_at.is_(None), Agent.is_active == True))
    query = query.where(_scope_filter(Agent, scope, user_id, project_id))
    if is_template is not None:
        query = query.where(Agent.is_template == is_template)
    if search:
        p = f"%{search}%"
        query = query.where(or_(Agent.name.ilike(p), Agent.role.ilike(p)))
    total_q = select(func.count()).select_from(query.subquery())
    total_r = await db.execute(total_q)
    total = total_r.scalar() or 0
    query = query.order_by(Agent.sort_order, desc(Agent.updated_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    agents = result.scalars().all()
    return {"items": [a.to_dict() for a in agents], "total": total}


@router.post("/create")
async def create_agent(
    data: AgentCreate,
    project_id: Optional[int] = Query(None),
    user=require_permissions("skills:write:personal"),
    db: AsyncSession = Depends(get_db)
):
    user_id = get_current_user_id(user)
    if data.scope == "project" and not project_id:
        raise HTTPException(status_code=400, detail="Project agent requires project_id")
    agent = Agent(
        name=data.name, role=data.role, instructions=data.instructions,
        scope=data.scope, parent_agent_id=data.parent_agent_id,
        config=json.dumps(data.config), is_template=data.is_template,
        user_id=user_id if data.scope != "global" else None,
        project_id=project_id if data.scope == "project" else None
    )
    db.add(agent)
    await db.flush()
    for sid in data.skill_ids:
        await db.execute(agent_skills.insert().values(agent_id=agent.id, skill_id=sid))
    for rid in data.rule_ids:
        await db.execute(agent_rules.insert().values(agent_id=agent.id, rule_id=rid))
    for kid in data.knowledge_base_ids:
        await db.execute(agent_knowledge.insert().values(agent_id=agent.id, knowledge_base_id=kid))
    await db.commit()
    await db.refresh(agent, ['skills', 'rules', 'knowledge_bases', 'children'])
    return agent.to_dict(include_relations=True)


@router.get("/templates/list")
async def list_templates(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Agent).where(and_(Agent.deleted_at.is_(None), Agent.is_template == True, Agent.scope == "global"))
        .order_by(Agent.sort_order)
    )
    agents = result.scalars().all()
    return {"items": [a.to_dict() for a in agents]}


@router.post("/from-template/{template_id}")
async def create_from_template(
    template_id: str,
    name: Optional[str] = Query(None),
    project_id: Optional[int] = Query(None),
    user=require_permissions("skills:write:personal"),
    db: AsyncSession = Depends(get_db)
):
    user_id = get_current_user_id(user)
    result = await db.execute(
        select(Agent).where(and_(Agent.id == template_id, Agent.deleted_at.is_(None), Agent.is_template == True))
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    await db.refresh(template, ['skills', 'rules', 'knowledge_bases'])
    agent = Agent(
        name=name or template.name, role=template.role, instructions=template.instructions,
        scope="personal" if not project_id else "project",
        config=template.config, user_id=user_id, project_id=project_id
    )
    db.add(agent)
    await db.flush()
    for s in template.skills:
        await db.execute(agent_skills.insert().values(agent_id=agent.id, skill_id=s.id))
    for r in template.rules:
        await db.execute(agent_rules.insert().values(agent_id=agent.id, rule_id=r.id))
    for k in template.knowledge_bases:
        await db.execute(agent_knowledge.insert().values(agent_id=agent.id, knowledge_base_id=k.id))
    await db.commit()
    await db.refresh(agent)
    return agent.to_dict(include_relations=True)


@router.get("/stats")
async def get_agent_stats(
    project_id: Optional[int] = Query(None),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    user_id = get_current_user_id(user)
    scope_c = or_(
        Agent.scope == "global",
        and_(Agent.scope == "personal", Agent.user_id == user_id),
        and_(Agent.scope == "project", Agent.project_id == project_id) if project_id else False
    )
    total = await db.execute(select(func.count(Agent.id)).where(and_(Agent.deleted_at.is_(None), scope_c)))
    by_scope = await db.execute(select(Agent.scope, func.count(Agent.id)).where(Agent.deleted_at.is_(None)).group_by(Agent.scope))
    return {"total": total.scalar() or 0, "by_scope": {r[0]: r[1] for r in by_scope.all()}}


# ==================== Parameterized Routes AFTER ====================

@router.get("/{agent_id}")
async def get_agent(
    agent_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Agent).where(and_(Agent.id == agent_id, Agent.deleted_at.is_(None)))
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent.to_dict(include_relations=True)


@router.put("/{agent_id}")
async def update_agent(
    agent_id: str,
    data: AgentUpdate,
    user=require_permissions("skills:write:personal"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Agent).where(and_(Agent.id == agent_id, Agent.deleted_at.is_(None)))
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    for f in ['name', 'role', 'instructions', 'is_active', 'is_template', 'parent_agent_id']:
        v = getattr(data, f)
        if v is not None:
            setattr(agent, f, v)
    if data.config is not None:
        agent.config = json.dumps(data.config)
    await db.commit()
    await db.refresh(agent)
    return agent.to_dict(include_relations=True)


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    user=require_permissions("skills:write:personal"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Agent).where(and_(Agent.id == agent_id, Agent.deleted_at.is_(None)))
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return {"success": True}


@router.get("/{agent_id}/context")
async def get_agent_context(
    agent_id: str,
    project_id: Optional[int] = Query(None),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Agent).where(and_(Agent.id == agent_id, Agent.deleted_at.is_(None)))
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    context = {"instructions": agent.instructions or "", "role": agent.role or "", "skills": [], "rules": [], "knowledge": []}
    await db.refresh(agent, ['skills', 'rules', 'knowledge_bases'])
    for s in agent.skills:
        context["skills"].append({"id": s.id, "name": s.name, "instruction": s.instruction})
    for r in agent.rules:
        context["rules"].append({"id": r.id, "name": r.name, "content": r.content, "severity": r.severity})
    for k in agent.knowledge_bases:
        context["knowledge"].append({"id": k.id, "name": k.name, "description": k.description})
    parent = agent
    visited = {agent_id}
    while parent.parent_agent_id and parent.parent_agent_id not in visited:
        visited.add(parent.parent_agent_id)
        result = await db.execute(select(Agent).where(and_(Agent.id == parent.parent_agent_id, Agent.deleted_at.is_(None))))
        parent = result.scalar_one_or_none()
        if not parent:
            break
        await db.refresh(parent, ['rules'])
        for r in parent.rules:
            if not any(x['id'] == r.id for x in context["rules"]):
                context["rules"].append({"id": r.id, "name": r.name, "content": r.content, "severity": r.severity})
        if parent.instructions:
            context["instructions"] = f"[Parent: {parent.name}]\n{parent.instructions}\n\n[Current: {agent.name}]\n{context['instructions']}"
    return context


@router.post("/{agent_id}/link-skill")
async def link_skill(agent_id: str, skill_id: str = Query(...), user=require_permissions("skills:write:personal"), db: AsyncSession = Depends(get_db)):
    await db.execute(agent_skills.insert().values(agent_id=agent_id, skill_id=skill_id))
    await db.commit()
    return {"success": True}


@router.post("/{agent_id}/unlink-skill")
async def unlink_skill(agent_id: str, skill_id: str = Query(...), user=require_permissions("skills:write:personal"), db: AsyncSession = Depends(get_db)):
    await db.execute(agent_skills.delete().where(and_(agent_skills.c.agent_id == agent_id, agent_skills.c.skill_id == skill_id)))
    await db.commit()
    return {"success": True}


@router.post("/{agent_id}/link-rule")
async def link_rule(agent_id: str, rule_id: str = Query(...), user=require_permissions("skills:write:personal"), db: AsyncSession = Depends(get_db)):
    await db.execute(agent_rules.insert().values(agent_id=agent_id, rule_id=rule_id))
    await db.commit()
    return {"success": True}


@router.post("/{agent_id}/unlink-rule")
async def unlink_rule(agent_id: str, rule_id: str = Query(...), user=require_permissions("skills:write:personal"), db: AsyncSession = Depends(get_db)):
    await db.execute(agent_rules.delete().where(and_(agent_rules.c.agent_id == agent_id, agent_rules.c.rule_id == rule_id)))
    await db.commit()
    return {"success": True}


@router.post("/{agent_id}/link-knowledge")
async def link_knowledge(agent_id: str, knowledge_base_id: str = Query(...), user=require_permissions("skills:write:personal"), db: AsyncSession = Depends(get_db)):
    await db.execute(agent_knowledge.insert().values(agent_id=agent_id, knowledge_base_id=knowledge_base_id))
    await db.commit()
    return {"success": True}


@router.post("/{agent_id}/unlink-knowledge")
async def unlink_knowledge(agent_id: str, knowledge_base_id: str = Query(...), user=require_permissions("skills:write:personal"), db: AsyncSession = Depends(get_db)):
    await db.execute(agent_knowledge.delete().where(and_(agent_knowledge.c.agent_id == agent_id, agent_knowledge.c.knowledge_base_id == knowledge_base_id)))
    await db.commit()
    return {"success": True}