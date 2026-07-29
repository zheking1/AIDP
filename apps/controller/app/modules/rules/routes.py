"""
Rules Module Routes
规则模块 API 路由 - 三层架构: global/personal/project
"""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.db.database import async_session_factory
from app.modules.rules.models import Rule, RuleGroup
from app.core.permissions import require_permissions, check_scope_read_access
from app.core.utils import get_current_user_id
from app.api.auth import get_current_user

router = APIRouter()


class RuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    content: str = Field(..., min_length=1)
    category: str = Field("code_style")
    severity: str = Field("medium")
    priority: int = Field(0, ge=0)
    scope: str = Field("personal")
    pattern: Optional[str] = None
    auto_fix: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    allowed_roles: List[str] = Field(default_factory=list)
    group_id: Optional[str] = None


class RuleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[str] = None
    pattern: Optional[str] = None
    auto_fix: Optional[str] = None
    tags: Optional[List[str]] = None
    allowed_roles: Optional[List[str]] = None
    group_id: Optional[str] = None
    is_active: Optional[bool] = None
    review_status: Optional[str] = None
    review_report: Optional[str] = None
    review_log: Optional[str] = None
    promotion_status: Optional[str] = None
    promotion_report: Optional[str] = None
    promotion_source_id: Optional[str] = None
    promotion_source_scope: Optional[str] = None


class RuleGroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    scope: str = Field("personal")
    parent_id: Optional[str] = None


class RuleSearchQuery(BaseModel):
    query: str = Field(..., min_length=1)
    category: Optional[str] = None
    severity: Optional[str] = None
    scope: Optional[str] = None
    top_k: int = Field(20, ge=1, le=100)


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        yield session


def _scope_filter(model, scope: str, user_id: str = None, project_id: int = None):
    if scope == "global":
        return model.scope == "global"
    elif scope == "personal":
        return and_(model.scope == "personal", model.user_id == user_id)
    elif scope == "project":
        return and_(model.scope == "project", model.project_id == project_id)
    return model.scope == scope


# ==================== Static Routes FIRST ====================

@router.get("/list")
async def list_rules(
    scope: str = Query("personal"),
    category: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    project_id: Optional[int] = Query(None),
    group_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await check_scope_read_access(user, "skills", scope)
    user_id = get_current_user_id(user)
    query = select(Rule).where(and_(Rule.deleted_at.is_(None), Rule.is_active == True))
    query = query.where(_scope_filter(Rule, scope, user_id, project_id))
    if category:
        query = query.where(Rule.category == category)
    if severity:
        query = query.where(Rule.severity == severity)
    if group_id:
        query = query.where(Rule.group_id == group_id)
    if search:
        p = f"%{search}%"
        query = query.where(or_(Rule.name.ilike(p), Rule.description.ilike(p), Rule.content.ilike(p)))

    total_q = select(func.count()).select_from(query.subquery())
    total_r = await db.execute(total_q)
    total = total_r.scalar() or 0
    query = query.order_by(desc(Rule.updated_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    rules = result.scalars().all()
    return {"items": [r.to_dict() for r in rules], "total": total, "count": len(rules)}


@router.post("/create")
async def create_rule(
    data: RuleCreate,
    project_id: Optional[int] = Query(None),
    user=require_permissions("skills:write:personal"),
    db: AsyncSession = Depends(get_db)
):
    user_id = get_current_user_id(user)
    if data.scope == "project" and not project_id:
        raise HTTPException(status_code=400, detail="Project rule requires project_id")
    rule = Rule(
        name=data.name, description=data.description, content=data.content,
        category=data.category, severity=data.severity, priority=data.priority,
        scope=data.scope,
        pattern=data.pattern, auto_fix=data.auto_fix,
        tags=json.dumps(data.tags), allowed_roles=json.dumps(data.allowed_roles),
        group_id=data.group_id,
        user_id=user_id if data.scope != "global" else None,
        project_id=project_id if data.scope == "project" else None
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule.to_dict(include_content=True)


@router.post("/search")
async def search_rules(
    query: RuleSearchQuery,
    project_id: Optional[int] = Query(None),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await check_scope_read_access(user, "skills", query.scope or "global")
    user_id = get_current_user_id(user)
    p = f"%{query.query}%"
    conditions = [
        Rule.deleted_at.is_(None), Rule.is_active == True,
        or_(Rule.name.ilike(p), Rule.description.ilike(p), Rule.content.ilike(p))
    ]
    if query.category:
        conditions.append(Rule.category == query.category)
    if query.severity:
        conditions.append(Rule.severity == query.severity)
    if query.scope:
        conditions.append(_scope_filter(Rule, query.scope, user_id, project_id))
    else:
        conditions.append(or_(
            Rule.scope == "global",
            and_(Rule.scope == "personal", Rule.user_id == user_id),
            and_(Rule.scope == "project", Rule.project_id == project_id) if project_id else False
        ))
    sql_q = select(Rule).where(and_(*conditions)).limit(query.top_k)
    result = await db.execute(sql_q)
    rules = result.scalars().all()
    return {"query": query.query, "total": len(rules), "results": [r.to_dict(include_content=True) for r in rules]}


@router.get("/groups/list")
async def list_groups(
    scope: str = Query("personal"),
    project_id: Optional[int] = Query(None),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await check_scope_read_access(user, "skills", scope)
    user_id = get_current_user_id(user)
    query = select(RuleGroup).where(_scope_filter(RuleGroup, scope, user_id, project_id))
    query = query.order_by(RuleGroup.sort_order)
    result = await db.execute(query)
    groups = result.scalars().all()
    return {"items": [g.to_dict() for g in groups]}


@router.post("/groups/create")
async def create_group(
    data: RuleGroupCreate,
    project_id: Optional[int] = Query(None),
    user=require_permissions("skills:write:personal"),
    db: AsyncSession = Depends(get_db)
):
    user_id = get_current_user_id(user)
    group = RuleGroup(
        name=data.name, description=data.description, scope=data.scope,
        parent_id=data.parent_id, user_id=user_id if data.scope != "global" else None,
        project_id=project_id if data.scope == "project" else None
    )
    db.add(group)
    await db.commit()
    await db.refresh(group)
    return group.to_dict()


@router.delete("/groups/{group_id}")
async def delete_group(
    group_id: str,
    user=require_permissions("skills:write:personal"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(RuleGroup).where(RuleGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    await db.delete(group)
    await db.commit()
    return {"success": True}


@router.get("/stats")
async def get_rules_stats(
    project_id: Optional[int] = Query(None),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await check_scope_read_access(user, "skills", "global")
    user_id = get_current_user_id(user)
    scope_c = or_(
        Rule.scope == "global",
        and_(Rule.scope == "personal", Rule.user_id == user_id),
        and_(Rule.scope == "project", Rule.project_id == project_id) if project_id else False
    )
    total = await db.execute(select(func.count(Rule.id)).where(and_(Rule.deleted_at.is_(None), scope_c)))
    by_cat = await db.execute(select(Rule.category, func.count(Rule.id)).where(and_(Rule.deleted_at.is_(None), scope_c)).group_by(Rule.category))
    by_sev = await db.execute(select(Rule.severity, func.count(Rule.id)).where(and_(Rule.deleted_at.is_(None), scope_c)).group_by(Rule.severity))
    return {
        "total": total.scalar() or 0,
        "by_category": {r[0]: r[1] for r in by_cat.all()},
        "by_severity": {r[0]: r[1] for r in by_sev.all()}
    }


# ==================== Parameterized Routes AFTER ====================

@router.get("/{rule_id}")
async def get_rule(
    rule_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Rule).where(and_(Rule.id == rule_id, Rule.deleted_at.is_(None)))
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    await check_scope_read_access(user, "skills", rule.scope)
    rule.access_count += 1
    rule.last_accessed_at = datetime.now(timezone.utc)
    await db.commit()
    return rule.to_dict(include_content=True)


@router.put("/{rule_id}")
async def update_rule(
    rule_id: str,
    data: RuleUpdate,
    user=require_permissions("skills:write:personal"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Rule).where(and_(Rule.id == rule_id, Rule.deleted_at.is_(None)))
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    simple = ['name', 'description', 'content', 'category', 'severity', 'pattern', 'auto_fix', 'group_id', 'is_active',
              'review_status', 'review_report', 'review_log',
              'promotion_status', 'promotion_report', 'promotion_source_id', 'promotion_source_scope']
    json_fields = {'tags': data.tags, 'allowed_roles': data.allowed_roles}
    for f in simple:
        v = getattr(data, f)
        if v is not None:
            setattr(rule, f, v)
    for f, v in json_fields.items():
        if v is not None:
            setattr(rule, f, json.dumps(v))
    await db.commit()
    await db.refresh(rule)
    return rule.to_dict(include_content=True)


@router.delete("/{rule_id}")
async def delete_rule(
    rule_id: str,
    user=require_permissions("skills:write:personal"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Rule).where(and_(Rule.id == rule_id, Rule.deleted_at.is_(None)))
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    rule.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return {"success": True}


@router.post("/{rule_id}/move")
async def move_rule(
    rule_id: str,
    group_id: Optional[str] = Query(None),
    scope: Optional[str] = Query(None),
    user=require_permissions("skills:write:personal"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Rule).where(and_(Rule.id == rule_id, Rule.deleted_at.is_(None)))
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    if group_id is not None:
        rule.group_id = group_id
    if scope is not None:
        rule.scope = scope
    await db.commit()
    return rule.to_dict()