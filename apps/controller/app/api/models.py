"""AIDP - Unified Model Management API (DB-backed)"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel

from app.services.auth_service import AuthService, PermissionService
from app.services.model_service import ModelService

router = APIRouter(prefix="/api/models", tags=["models"])


class ModelCreateRequest(BaseModel):
    name: str
    provider: str
    model_name: str
    api_base: Optional[str] = None
    api_key: Optional[str] = None
    task_types: List[str] = ["chat"]
    max_tokens: int = 4096
    temperature: float = 0.7
    status: str = "active"
    priority: int = 0


class ModelUpdateRequest(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    model_name: Optional[str] = None
    api_base: Optional[str] = None
    api_key: Optional[str] = None
    task_types: Optional[List[str]] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    status: Optional[str] = None
    priority: Optional[int] = None


@router.get("")
async def api_list_models(request: Request, task_type: Optional[str] = Query(None)):
    session_token = request.cookies.get("aidp_session")
    user = await AuthService.validate_session(session_token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if task_type:
        items = await ModelService.get_by_task(task_type)
    else:
        items = await ModelService.list_models()
    return {"items": items}


@router.post("")
async def api_create_model(request: Request, data: ModelCreateRequest):
    session_token = request.cookies.get("aidp_session")
    user = await AuthService.validate_session(session_token)
    if not user or not PermissionService.is_admin(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    model = await ModelService.create_model(data.model_dump())
    return {"success": True, "model": model}


@router.put("/{model_id}")
async def api_update_model(request: Request, model_id: int, data: ModelUpdateRequest):
    session_token = request.cookies.get("aidp_session")
    user = await AuthService.validate_session(session_token)
    if not user or not PermissionService.is_admin(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    model = await ModelService.update_model(model_id, data.model_dump(exclude_none=True))
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"success": True, "model": model}


@router.delete("/{model_id}")
async def api_delete_model(request: Request, model_id: int):
    session_token = request.cookies.get("aidp_session")
    user = await AuthService.validate_session(session_token)
    if not user or not PermissionService.is_admin(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    deleted = await ModelService.delete_model(model_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"success": True, "message": "Model deleted"}


@router.get("/for-task/{task_type}")
async def api_get_model_for_task(task_type: str):
    """供工具调用的接口 — 按任务类型获取最佳模型，无需认证"""
    model = await ModelService.get_best_for_task(task_type)
    if not model:
        raise HTTPException(status_code=404, detail=f"No model found for task: {task_type}")
    return {"model": model}