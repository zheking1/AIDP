from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.config_service import ConfigService
from app.services.permission_service import PermissionChecker
from app.models.user import User

router = APIRouter(prefix="/api/projects/{project_id}/configs", tags=["configs"])


@router.get("/")
async def get_configs(request: Request, project_id: int, session: AsyncSession = Depends(get_db)):
    """获取项目配置"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    permission_checker = PermissionChecker(session, User(id=user_id))
    if not await permission_checker.can_view_project(user_id, project_id):
        raise HTTPException(status_code=403, detail="Permission denied")

    config_service = ConfigService(session)
    configs = await config_service.get_configs(project_id)

    return JSONResponse(content={
        "configs": [{
            "id": c.id,
            "env_type": c.env_type,
            "config_key": c.config_key,
            "config_value": c.config_value
        } for c in configs]
    })


@router.post("/")
async def set_config(request: Request, project_id: int, session: AsyncSession = Depends(get_db)):
    """设置项目配置"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    permission_checker = PermissionChecker(session, User(id=user_id))
    if not await permission_checker.can_manage_project(user_id, project_id):
        raise HTTPException(status_code=403, detail="Permission denied")

    body = await request.json()
    env_type = body.get("env_type")
    config_key = body.get("config_key")
    config_value = body.get("config_value")

    if not all([env_type, config_key, config_value]):
        raise HTTPException(status_code=400, detail="env_type, config_key, and config_value are required")

    config_service = ConfigService(session)
    config = await config_service.set_config(project_id, env_type, config_key, config_value)

    return JSONResponse(content={
        "id": config.id,
        "project_id": config.project_id,
        "env_type": config.env_type,
        "config_key": config.config_key,
        "config_value": config.config_value
    })


@router.get("/{env_type}")
async def get_env_config(request: Request, project_id: int, env_type: str, session: AsyncSession = Depends(get_db)):
    """获取特定环境配置"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    permission_checker = PermissionChecker(session, User(id=user_id))
    if not await permission_checker.can_view_project(user_id, project_id):
        raise HTTPException(status_code=403, detail="Permission denied")

    config_service = ConfigService(session)
    config = await config_service.get_env_config(project_id, env_type)

    return JSONResponse(content=config)


@router.post("/{env_type}/resolve")
async def resolve_config(request: Request, project_id: int, env_type: str, session: AsyncSession = Depends(get_db)):
    """Agent 自动获取配置"""
    body = await request.json()
    keys = body.get("keys", [])

    config_service = ConfigService(session)
    resolved = await config_service.resolve_config(project_id, env_type, keys)

    return JSONResponse(content=resolved)
