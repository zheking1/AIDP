"""
Assets Module Routes
代码资产模块 API 路由
"""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import json

from app.db.database import async_session_factory
from app.modules.assets.models import Asset, AssetTag
from app.core.permissions import require_permissions
from app.core.utils import get_current_user_id
from app.api.auth import get_current_user

router = APIRouter()


class AssetCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    asset_type: str = Field("snippet", description="snippet, template, config, component, utility, documentation")
    language: Optional[str] = None
    format: Optional[str] = "text"
    visibility: str = Field("project", description="project, workspace, global")
    content: str = Field(..., min_length=1)
    variables: Optional[dict] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    extra_data: Optional[dict] = Field(default_factory=dict)


class AssetUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    asset_type: Optional[str] = None
    language: Optional[str] = None
    format: Optional[str] = None
    visibility: Optional[str] = None
    content: Optional[str] = None
    variables: Optional[dict] = None
    tags: Optional[List[str]] = None
    extra_data: Optional[dict] = None


class AssetSearchQuery(BaseModel):
    query: str = Field(..., min_length=1)
    asset_type: Optional[str] = None
    language: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    top_k: int = Field(20, ge=1, le=100)


class AssetRenderRequest(BaseModel):
    variables: dict = Field(default_factory=dict)


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        yield session


# ==================== Static routes FIRST ====================

@router.get("/list")
async def list_assets(
    project_id: Optional[int] = Query(None),
    asset_type: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Asset).options(selectinload(Asset.tags)).where(Asset.deleted_at.is_(None))

    if project_id:
        query = query.where(Asset.project_id == project_id)
    if asset_type:
        query = query.where(Asset.asset_type == asset_type)
    if language:
        query = query.where(Asset.language == language)
    if search:
        pattern = f"%{search}%"
        query = query.where(or_(Asset.title.ilike(pattern), Asset.description.ilike(pattern)))

    total_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(total_query)
    total = total_result.scalar() or 0

    query = query.order_by(desc(Asset.updated_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    assets = result.scalars().all()

    return {"items": [a.to_dict(include_content=False) for a in assets], "total": total, "count": len(assets)}


@router.get("/stats")
async def get_assets_stats(
    project_id: Optional[int] = Query(None),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    conditions = [Asset.deleted_at.is_(None)]
    if project_id:
        conditions.append(Asset.project_id == project_id)

    total = await db.execute(
        select(func.count(Asset.id)).where(and_(*conditions))
    )

    by_type = await db.execute(
        select(Asset.asset_type, func.count(Asset.id)).where(and_(*conditions)).group_by(Asset.asset_type)
    )

    by_language = await db.execute(
        select(Asset.language, func.count(Asset.id)).where(and_(*conditions)).group_by(Asset.language)
    )

    return {
        "total": total.scalar() or 0,
        "by_type": {row[0]: row[1] for row in by_type.all()},
        "by_language": {row[0] or "unknown": row[1] for row in by_language.all()}
    }


@router.post("/create")
async def create_asset(
    data: AssetCreate,
    project_id: Optional[int] = Query(None),
    user=require_permissions("asset:write"),
    db: AsyncSession = Depends(get_db)
):
    user_id = get_current_user_id(user)

    asset = Asset(
        project_id=project_id, user_id=user_id,
        title=data.title, description=data.description,
        asset_type=data.asset_type, language=data.language,
        format=data.format, visibility=data.visibility,
        content=data.content, variables=json.dumps(data.variables),
        extra_data=json.dumps(data.extra_data), created_by=user_id, updated_by=user_id
    )
    db.add(asset)
    await db.flush()

    for tag in data.tags:
        db.add(AssetTag(asset_id=asset.id, tag=tag))

    await db.commit()
    await db.refresh(asset, ['tags'])
    return asset.to_dict()


@router.post("/search")
async def search_assets(
    query: AssetSearchQuery,
    project_id: Optional[int] = Query(None),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    search_pattern = f"%{query.query}%"

    conditions = [
        Asset.deleted_at.is_(None),
        or_(Asset.title.ilike(search_pattern), Asset.content.ilike(search_pattern))
    ]

    if project_id:
        conditions.append(Asset.project_id == project_id)
    if query.asset_type:
        conditions.append(Asset.asset_type == query.asset_type)
    if query.language:
        conditions.append(Asset.language == query.language)

    sql_query = select(Asset).options(selectinload(Asset.tags)).where(and_(*conditions)).limit(query.top_k)
    result = await db.execute(sql_query)
    assets = result.scalars().all()

    results = []
    for asset in assets:
        score = 0.5 if query.query.lower() in asset.title.lower() else 0.3
        results.append({"asset": asset.to_dict(), "score": score})

    return {"query": query.query, "total": len(results), "results": results}


# ==================== Parameterized routes AFTER ====================

@router.get("/{asset_id}")
async def get_asset(
    asset_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Asset).where(and_(Asset.id == asset_id, Asset.deleted_at.is_(None)))
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    asset.access_count += 1
    await db.commit()
    return asset.to_dict()


@router.put("/{asset_id}")
async def update_asset(
    asset_id: str,
    data: AssetUpdate,
    user=require_permissions("asset:write"),
    db: AsyncSession = Depends(get_db)
):
    user_id = get_current_user_id(user)
    result = await db.execute(
        select(Asset).where(and_(Asset.id == asset_id, Asset.deleted_at.is_(None)))
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    simple_fields = ['title', 'description', 'asset_type', 'language', 'format', 'visibility', 'content']
    json_fields = {'variables': data.variables, 'extra_data': data.extra_data}

    for field in simple_fields:
        value = getattr(data, field)
        if value is not None:
            setattr(asset, field, value)
    for field, value in json_fields.items():
        if value is not None:
            setattr(asset, field, json.dumps(value))

    if data.tags is not None:
        existing = await db.execute(select(AssetTag).where(AssetTag.asset_id == asset_id))
        for t in existing.scalars().all():
            await db.delete(t)
        for tag in data.tags:
            db.add(AssetTag(asset_id=asset_id, tag=tag))

    asset.updated_by = user_id
    await db.commit()
    await db.refresh(asset)
    return asset.to_dict()


@router.delete("/{asset_id}")
async def delete_asset(
    asset_id: str,
    user=require_permissions("asset:delete"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Asset).where(and_(Asset.id == asset_id, Asset.deleted_at.is_(None)))
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    asset.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return {"success": True, "message": "Asset deleted"}


@router.post("/{asset_id}/render")
async def render_asset(
    asset_id: str,
    data: AssetRenderRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Asset).where(and_(Asset.id == asset_id, Asset.deleted_at.is_(None)))
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    template_vars = json.loads(asset.variables) if asset.variables else {}
    template_vars.update(data.variables)

    rendered = asset.content
    for key, value in template_vars.items():
        rendered = rendered.replace("{{" + key + "}}", str(value))

    return {"rendered_content": rendered, "variables_used": list(template_vars.keys())}

