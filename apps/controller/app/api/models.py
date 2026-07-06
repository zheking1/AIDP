"""
AIDP - LLM Models Management API
"""

from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from app.db.database import async_session_factory
from app.services.auth_service import AuthService, PermissionService

router = APIRouter(prefix="/api/models", tags=["models"])


# In-memory storage for models (until database table is created)
_models = [
    {"id": 1, "name": "DeepSeek-V3", "provider": "DeepSeek", "model_name": "deepseek-chat", "role": "completion", "status": "active", "created_at": datetime.utcnow().isoformat()},
    {"id": 2, "name": "GPT-4", "provider": "OpenAI", "model_name": "gpt-4", "role": "completion", "status": "active", "created_at": datetime.utcnow().isoformat()},
]
_next_id = 3


class ModelCreateRequest(BaseModel):
    name: str
    provider: str
    model_name: str
    role: str = "completion"
    status: str = "active"


class ModelUpdateRequest(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    model_name: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None


@router.get("")
async def api_list_models(request: Request):
    """List all LLM models"""
    session_token = request.cookies.get("aidp_session")
    user = await AuthService.validate_session(session_token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return {"items": _models}


@router.post("")
async def api_create_model(request: Request, data: ModelCreateRequest):
    """Create a new model configuration (admin only)"""
    session_token = request.cookies.get("aidp_session")
    user = await AuthService.validate_session(session_token)
    
    if not user or not PermissionService.is_admin(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    global _next_id
    model = {
        "id": _next_id,
        "name": data.name,
        "provider": data.provider,
        "model_name": data.model_name,
        "role": data.role,
        "status": data.status,
        "created_at": datetime.utcnow().isoformat()
    }
    _models.append(model)
    _next_id += 1
    
    return {"success": True, "model": model}


@router.put("/{model_id}")
async def api_update_model(request: Request, model_id: int, data: ModelUpdateRequest):
    """Update a model configuration (admin only)"""
    session_token = request.cookies.get("aidp_session")
    user = await AuthService.validate_session(session_token)
    
    if not user or not PermissionService.is_admin(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    model = None
    for m in _models:
        if m["id"] == model_id:
            model = m
            break
    
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    if data.name is not None:
        model["name"] = data.name
    if data.provider is not None:
        model["provider"] = data.provider
    if data.model_name is not None:
        model["model_name"] = data.model_name
    if data.role is not None:
        model["role"] = data.role
    if data.status is not None:
        model["status"] = data.status
    
    model["updated_at"] = datetime.utcnow().isoformat()
    
    return {"success": True, "model": model}


@router.delete("/{model_id}")
async def api_delete_model(request: Request, model_id: int):
    """Delete a model configuration (admin only)"""
    session_token = request.cookies.get("aidp_session")
    user = await AuthService.validate_session(session_token)
    
    if not user or not PermissionService.is_admin(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    global _models
    model = None
    for m in _models:
        if m["id"] == model_id:
            model = m
            break
    
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    _models = [m for m in _models if m["id"] != model_id]
    
    return {"success": True, "message": "Model deleted successfully"}
