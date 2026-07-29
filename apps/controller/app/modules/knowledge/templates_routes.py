"""
Document Templates Routes
文档模板 API 路由
"""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.db.database import async_session_factory
from app.modules.knowledge.models import DocumentTemplate
from app.core.permissions import require_permissions
from app.core.utils import get_current_user_id
from app.api.auth import get_current_user

router = APIRouter(prefix="/templates", tags=["templates"])


class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    category: str = Field(..., description="research/prd/arch/plan/dev/test/ops/meeting")
    content: str = Field(..., min_length=1)
    variables: List[dict] = Field(default_factory=list)
    description: Optional[str] = None
    scope: str = "global"


class TemplateRender(BaseModel):
    variables: dict = Field(default_factory=dict)


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        yield session


@router.get("/list")
async def list_templates(
    category: Optional[str] = Query(None),
    scope: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(DocumentTemplate).where(DocumentTemplate.is_active == True)
    if category:
        query = query.where(DocumentTemplate.category == category)
    if scope:
        query = query.where(DocumentTemplate.scope == scope)
    else:
        query = query.where(DocumentTemplate.scope == "global")
    if search:
        p = f"%{search}%"
        query = query.where(or_(DocumentTemplate.name.ilike(p), DocumentTemplate.description.ilike(p)))
    query = query.order_by(DocumentTemplate.category, DocumentTemplate.name)
    result = await db.execute(query)
    return {"items": [t.to_dict() for t in result.scalars().all()]}


@router.post("/create")
async def create_template(
    data: TemplateCreate,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    user_id = get_current_user_id(user)
    tpl = DocumentTemplate(
        name=data.name, category=data.category, content=data.content,
        variables=json.dumps(data.variables),
        description=data.description, scope=data.scope, user_id=user_id
    )
    db.add(tpl)
    await db.commit()
    await db.refresh(tpl)
    return tpl.to_dict()


@router.get("/{template_id}")
async def get_template(
    template_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(DocumentTemplate).where(and_(DocumentTemplate.id == template_id, DocumentTemplate.is_active == True))
    )
    tpl = result.scalar_one_or_none()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return {
        "id": tpl.id, "name": tpl.name, "category": tpl.category,
        "content": tpl.content, "variables": json.loads(tpl.variables) if tpl.variables else [],
        "description": tpl.description, "scope": tpl.scope,
        "created_at": tpl.created_at.isoformat() if tpl.created_at else None
    }


@router.post("/{template_id}/render")
async def render_template(
    template_id: str,
    data: TemplateRender,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(DocumentTemplate).where(and_(DocumentTemplate.id == template_id, DocumentTemplate.is_active == True))
    )
    tpl = result.scalar_one_or_none()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    template_vars = json.loads(tpl.variables) if tpl.variables else []
    rendered = tpl.content
    for v in template_vars:
        key = v.get("key") or v.get("name", "")
        val = data.variables.get(key, v.get("default", ""))
        rendered = rendered.replace("{{" + key + "}}", str(val))
    for key, val in data.variables.items():
        rendered = rendered.replace("{{" + key + "}}", str(val))
    return {"rendered": rendered, "variables_used": list(data.variables.keys())}


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(DocumentTemplate).where(DocumentTemplate.id == template_id))
    tpl = result.scalar_one_or_none()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    tpl.is_active = False
    await db.commit()
    return {"success": True}


@router.get("/stats")
async def get_template_stats(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    total = await db.execute(select(func.count(DocumentTemplate.id)).where(DocumentTemplate.is_active == True))
    by_category = await db.execute(
        select(DocumentTemplate.category, func.count(DocumentTemplate.id))
        .where(DocumentTemplate.is_active == True).group_by(DocumentTemplate.category)
    )
    return {"total": total.scalar() or 0, "by_category": {r[0]: r[1] for r in by_category.all()}}