from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.asset_tool.tools.asset-tool.db.database import get_db
from app.tools.asset_tool.tools.asset-tool.schemas.asset import AssetCreateRequest, AssetUpdateRequest, AssetSearchRequest
from app.tools.asset_tool.tools.asset-tool.services import asset_service
from app.tools.asset_tool.tools.asset-tool.schemas.common import ApiResponse

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.post("", response_model=ApiResponse)
async def create_asset(req: AssetCreateRequest, db: AsyncSession = Depends(get_db)):
    asset = await asset_service.create_asset(db, req)
    return ApiResponse(data=asset.model_dump())


@router.get("", response_model=ApiResponse)
async def list_assets(
    workspace_id: str,
    project_id: str = None,
    asset_type: str = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    assets = await asset_service.list_assets(
        db, workspace_id=workspace_id, project_id=project_id,
        asset_type=asset_type, page=page, page_size=page_size,
    )
    return ApiResponse(data=[a.model_dump() for a in assets])


@router.get("/{asset_id}", response_model=ApiResponse)
async def get_asset(asset_id: str, workspace_id: str, db: AsyncSession = Depends(get_db)):
    asset = await asset_service.get_asset(db, asset_id, workspace_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return ApiResponse(data=asset.model_dump())


@router.put("/{asset_id}", response_model=ApiResponse)
async def update_asset(
    asset_id: str,
    workspace_id: str,
    req: AssetUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    asset = await asset_service.update_asset(db, asset_id, workspace_id, req)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return ApiResponse(data=asset.model_dump())


@router.delete("/{asset_id}", response_model=ApiResponse)
async def delete_asset(asset_id: str, workspace_id: str, db: AsyncSession = Depends(get_db)):
    ok = await asset_service.delete_asset(db, asset_id, workspace_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Asset not found")
    return ApiResponse(message="Asset deleted")


@router.post("/search", response_model=ApiResponse)
async def search_assets(req: AssetSearchRequest, db: AsyncSession = Depends(get_db)):
    result = await asset_service.search_assets(db, req)
    return ApiResponse(data=result.model_dump())


@router.post("/render", response_model=ApiResponse)
async def render_asset(
    asset_id: str,
    workspace_id: str,
    variables: dict = {},
    db: AsyncSession = Depends(get_db),
):
    rendered = await asset_service.render_asset(db, asset_id, workspace_id, variables)
    if rendered is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return ApiResponse(data={"rendered": rendered})
