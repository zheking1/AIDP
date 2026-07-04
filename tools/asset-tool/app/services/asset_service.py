import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AtAsset, AtAssetTag
from app.schemas.asset import (
    AssetCreateRequest, AssetUpdateRequest, AssetInfo,
    AssetSearchRequest, AssetSearchItem, AssetSearchResult,
)


async def create_asset(db: AsyncSession, req: AssetCreateRequest) -> AssetInfo:
    """Create a new asset."""
    asset = AtAsset(
        workspace_id=req.workspace_id,
        project_id=req.project_id,
        title=req.title,
        asset_type=req.asset_type,
        language=req.language,
        format=req.format,
        visibility=req.visibility,
        content=req.content,
        description=req.description,
        variables=req.variables,
        metadata_=req.metadata,
    )
    db.add(asset)
    await db.flush()

    for tag in req.tags:
        db.add(AtAssetTag(asset_id=asset.id, tag=tag))
    await db.flush()

    return _asset_to_info(asset, req.tags)


async def get_asset(db: AsyncSession, asset_id: str, workspace_id: str) -> Optional[AssetInfo]:
    """Get an asset by ID with scope check."""
    result = await db.execute(
        select(AtAsset).where(
            AtAsset.id == asset_id,
            AtAsset.workspace_id == workspace_id,
            AtAsset.deleted_at.is_(None),
        )
    )
    asset = result.scalar_one_or_none()
    if not asset:
        return None

    tags = await _get_asset_tags(db, asset.id)
    return _asset_to_info(asset, tags)


async def update_asset(
    db: AsyncSession, asset_id: str, workspace_id: str, req: AssetUpdateRequest
) -> Optional[AssetInfo]:
    """Update an asset."""
    result = await db.execute(
        select(AtAsset).where(
            AtAsset.id == asset_id,
            AtAsset.workspace_id == workspace_id,
            AtAsset.deleted_at.is_(None),
        )
    )
    asset = result.scalar_one_or_none()
    if not asset:
        return None

    if req.title is not None:
        asset.title = req.title
    if req.content is not None:
        asset.content = req.content
    if req.description is not None:
        asset.description = req.description
    if req.variables is not None:
        asset.variables = req.variables

    if req.tags is not None:
        old_tags_result = await db.execute(
            select(AtAssetTag).where(AtAssetTag.asset_id == asset.id)
        )
        for old_tag in old_tags_result.scalars().all():
            await db.delete(old_tag)

        for tag in req.tags:
            db.add(AtAssetTag(asset_id=asset.id, tag=tag))

    await db.flush()

    tags = req.tags if req.tags is not None else await _get_asset_tags(db, asset.id)
    return _asset_to_info(asset, tags)


async def delete_asset(db: AsyncSession, asset_id: str, workspace_id: str) -> bool:
    """Soft delete an asset."""
    result = await db.execute(
        select(AtAsset).where(
            AtAsset.id == asset_id,
            AtAsset.workspace_id == workspace_id,
            AtAsset.deleted_at.is_(None),
        )
    )
    asset = result.scalar_one_or_none()
    if not asset:
        return False
    asset.deleted_at = datetime.now(timezone.utc)
    return True


async def list_assets(
    db: AsyncSession,
    workspace_id: str,
    project_id: Optional[str] = None,
    asset_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> list[AssetInfo]:
    """List assets with scope filter."""
    query = select(AtAsset).where(
        AtAsset.workspace_id == workspace_id,
        AtAsset.deleted_at.is_(None),
    )

    if project_id:
        query = query.where(AtAsset.project_id == project_id)
    if asset_type:
        query = query.where(AtAsset.asset_type == asset_type)

    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    assets = result.scalars().all()

    infos = []
    for asset in assets:
        tags = await _get_asset_tags(db, asset.id)
        infos.append(_asset_to_info(asset, tags))

    return infos


async def search_assets(db: AsyncSession, req: AssetSearchRequest) -> AssetSearchResult:
    """Search assets by keyword."""
    query = select(AtAsset).where(
        AtAsset.workspace_id == req.workspace_id,
        AtAsset.deleted_at.is_(None),
    )

    if req.project_id:
        query = query.where(
            or_(
                AtAsset.project_id == req.project_id,
                AtAsset.project_id.is_(None),
            )
        )

    if req.asset_type:
        query = query.where(AtAsset.asset_type == req.asset_type)

    if req.language:
        query = query.where(AtAsset.language == req.language)

    if req.query:
        query = query.where(
            AtAsset.content.ilike(f"%{req.query}%") | AtAsset.title.ilike(f"%{req.query}%")
        )

    query = query.limit(req.top_k)

    result = await db.execute(query)
    assets = result.scalars().all()

    items = []
    for asset in assets:
        score = _calculate_score(asset, req.query)
        tags = await _get_asset_tags(db, asset.id)
        items.append(AssetSearchItem(
            id=asset.id,
            title=asset.title,
            asset_type=asset.asset_type,
            language=asset.language,
            content=asset.content,
            tags=tags,
            score=score,
        ))

    items.sort(key=lambda x: x.score, reverse=True)

    return AssetSearchResult(items=items, total=len(items))


async def render_asset(
    db: AsyncSession, asset_id: str, workspace_id: str, variables: dict
) -> Optional[str]:
    """Render an asset template with variables."""
    result = await db.execute(
        select(AtAsset).where(
            AtAsset.id == asset_id,
            AtAsset.workspace_id == workspace_id,
            AtAsset.deleted_at.is_(None),
        )
    )
    asset = result.scalar_one_or_none()
    if not asset:
        return None

    content = asset.content
    for key, value in variables.items():
        content = content.replace("{{" + key + "}}", str(value))

    return content


async def _get_asset_tags(db: AsyncSession, asset_id: str) -> list[str]:
    result = await db.execute(
        select(AtAssetTag.tag).where(AtAssetTag.asset_id == asset_id)
    )
    return [row[0] for row in result.all()]


def _calculate_score(asset: AtAsset, query: str) -> float:
    if not query:
        return 0.5
    score = 0.0
    query_lower = query.lower()
    if query_lower in asset.title.lower():
        score += 0.5
    if query_lower in asset.content.lower():
        score += 0.3
    return min(score, 1.0)


def _asset_to_info(asset: AtAsset, tags: list[str]) -> AssetInfo:
    return AssetInfo(
        id=asset.id,
        workspace_id=asset.workspace_id,
        project_id=asset.project_id,
        title=asset.title,
        asset_type=asset.asset_type,
        language=asset.language,
        format=asset.format,
        visibility=asset.visibility,
        content=asset.content,
        description=asset.description,
        tags=tags,
        variables=asset.variables or {},
        created_at=asset.created_at.isoformat() if asset.created_at else "",
        updated_at=asset.updated_at.isoformat() if asset.updated_at else "",
    )
