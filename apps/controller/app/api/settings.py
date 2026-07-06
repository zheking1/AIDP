"""
AIDP - System Settings API
"""

from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from app.db.database import async_session_factory
from app.services.auth_service import AuthService, PermissionService

router = APIRouter(prefix="/api/settings", tags=["settings"])


# In-memory storage for settings
_settings = {
    "siteName": "AIDP",
    "siteDescription": "AI DevOps Platform",
    "allowRegistration": False,
    "requireApproval": True
}


class SettingsUpdateRequest(BaseModel):
    siteName: Optional[str] = None
    siteDescription: Optional[str] = None
    allowRegistration: Optional[bool] = None
    requireApproval: Optional[bool] = None


@router.get("")
async def api_get_settings(request: Request):
    """Get system settings"""
    session_token = request.cookies.get("aidp_session")
    user = await AuthService.validate_session(session_token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return _settings


@router.put("")
async def api_update_settings(request: Request, data: SettingsUpdateRequest):
    """Update system settings (admin only)"""
    session_token = request.cookies.get("aidp_session")
    user = await AuthService.validate_session(session_token)
    
    if not user or not PermissionService.is_admin(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    global _settings
    
    if data.siteName is not None:
        _settings["siteName"] = data.siteName
    if data.siteDescription is not None:
        _settings["siteDescription"] = data.siteDescription
    if data.allowRegistration is not None:
        _settings["allowRegistration"] = data.allowRegistration
    if data.requireApproval is not None:
        _settings["requireApproval"] = data.requireApproval
    
    return {"success": True, "settings": _settings}
