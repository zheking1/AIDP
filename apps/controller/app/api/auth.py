"""
AIDP Unified Web UI - Authentication API Routes
Phase 1: Infrastructure
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Request, Response, HTTPException, Depends, Form
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

from app.services.auth_service import AuthService, PermissionService
from app.db.auth_models import User, UserRole

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ============================================================================
# Pydantic Models
# ============================================================================

class LoginRequest(BaseModel):
    username: str
    password: str
    remember_me: bool = False


class LoginResponse(BaseModel):
    success: bool
    message: str
    user: Optional[dict] = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class CreateUserRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    nickname: Optional[str] = None
    role: str = "user"


# ============================================================================
# API Routes
# ============================================================================

@router.post("/login", response_model=LoginResponse)
async def api_login(request: Request, response: Response, data: LoginRequest):
    """API endpoint for user login"""
    # Get client info
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    # Authenticate
    user = await AuthService.authenticate_user(
        username=data.username,
        password=data.password,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    if not user:
        return LoginResponse(success=False, message="Invalid username or password")
    
    # Create session
    session = await AuthService.create_session(
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
        remember_me=data.remember_me
    )
    
    # Set session cookie
    max_age = 60 * 60 * 24 * 7 if data.remember_me else 60 * 60 * 24  # 7 days or 1 day
    response.set_cookie(
        key="aidp_session",
        value=session.session_token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=max_age
    )
    
    return LoginResponse(
        success=True,
        message="Login successful",
        user={
            "id": str(user.id),
            "username": user.username,
            "nickname": user.nickname,
            "email": user.email,
            "role": user.role,
            "avatar_url": user.avatar_url
        }
    )


@router.post("/login/form")
async def login_form(request: Request, response: Response):
    """Form-based login (for web UI)"""
    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    remember_me = form.get("remember_me") == "on"
    
    # Get client info
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    # Authenticate
    user = await AuthService.authenticate_user(
        username=username,
        password=password,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    if not user:
        # Return to login page with error
        return RedirectResponse(
            url=f"/login?error=Invalid+username+or+password",
            status_code=302
        )
    
    # Create session
    session = await AuthService.create_session(
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
        remember_me=remember_me
    )
    
    # Redirect to home page with session cookie
    redirect = RedirectResponse(url="/", status_code=302)
    max_age = 60 * 60 * 24 * 7 if remember_me else 60 * 60 * 24
    redirect.set_cookie(
        key="aidp_session",
        value=session.session_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=max_age
    )
    return redirect


@router.post("/logout")
async def api_logout(request: Request, response: Response):
    """Logout user"""
    session_token = request.cookies.get("aidp_session")
    
    if session_token:
        await AuthService.logout(session_token)
    
    # Clear cookie
    response.delete_cookie(key="aidp_session")
    
    return JSONResponse({"success": True, "message": "Logged out successfully"})


@router.post("/logout/form")
async def logout_form(request: Request, response: Response):
    """Form-based logout (for web UI)"""
    session_token = request.cookies.get("aidp_session")
    
    if session_token:
        await AuthService.logout(session_token)
    
    # Clear cookie
    response.delete_cookie(key="aidp_session")
    
    return RedirectResponse(url="/login", status_code=302)


@router.get("/me")
async def api_get_current_user(request: Request):
    """Get current logged-in user info"""
    session_token = request.cookies.get("aidp_session")
    user = await AuthService.validate_session(session_token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return {
        "id": str(user.id),
        "username": user.username,
        "nickname": user.nickname,
        "email": user.email,
        "role": user.role,
        "avatar_url": user.avatar_url,
        "status": user.status
    }


@router.post("/change-password")
async def api_change_password(request: Request, data: ChangePasswordRequest):
    """Change user password"""
    session_token = request.cookies.get("aidp_session")
    user = await AuthService.validate_session(session_token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    success = await AuthService.change_password(
        user_id=user.id,
        old_password=data.old_password,
        new_password=data.new_password
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Invalid old password")
    
    return {"success": True, "message": "Password changed successfully"}


# ============================================================================
# User Management API (Admin only)
# ============================================================================

@router.get("/users")
async def api_list_users(request: Request, page: int = 1, size: int = 20, search: str = None):
    """List all users (admin only)"""
    session_token = request.cookies.get("aidp_session")
    current_user = await AuthService.validate_session(session_token)
    
    if not current_user or not PermissionService.is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from sqlalchemy import select, func
    from app.db.database import async_session_factory
    
    async with async_session_factory() as session:
        query = select(User)
        
        if search:
            from sqlalchemy import or_
            query = query.where(
                or_(
                    User.username.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%"),
                    User.nickname.ilike(f"%{search}%")
                )
            )
        
        # Get total count
        count_result = await session.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar()
        
        # Get paginated results
        query = query.order_by(User.created_at.desc()).offset((page - 1) * size).limit(size)
        result = await session.execute(query)
        users = result.scalars().all()
        
        return {
            "items": [u.to_dict() for u in users],
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size
        }


@router.post("/users")
async def api_create_user(request: Request, data: CreateUserRequest):
    """Create a new user (admin only)"""
    session_token = request.cookies.get("aidp_session")
    current_user = await AuthService.validate_session(session_token)
    
    if not current_user or not PermissionService.is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        role = UserRole(data.role) if data.role else UserRole.USER
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {data.role}")
    
    try:
        user = await AuthService.create_user(
            username=data.username,
            password=data.password,
            email=data.email,
            nickname=data.nickname,
            role=role,
            created_by=current_user.id
        )
        return {"success": True, "user": user.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/users/{user_id}/toggle")
async def api_toggle_user(request: Request, user_id: str):
    """Enable/disable a user (admin only)"""
    session_token = request.cookies.get("aidp_session")
    current_user = await AuthService.validate_session(session_token)
    
    if not current_user or not PermissionService.is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        target_user_id = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    # Can't disable yourself
    if target_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot disable yourself")
    
    async with async_session_factory() as session:
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.id == target_user_id))
        target_user = result.scalar_one_or_none()
        
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Toggle status
        new_status = target_user.status != "active"
        success = await AuthService.toggle_user_status(target_user_id, new_status)
        
        if success:
            return {"success": True, "message": f"User {'enabled' if new_status else 'disabled'}"}
        else:
            raise HTTPException(status_code=400, detail="Failed to toggle user status")


@router.delete("/users/{user_id}")
async def api_delete_user(request: Request, user_id: str):
    """Delete a user (super admin only)"""
    session_token = request.cookies.get("aidp_session")
    current_user = await AuthService.validate_session(session_token)
    
    if not current_user or not PermissionService.is_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super admin access required")
    
    try:
        target_user_id = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    # Can't delete yourself
    if target_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    async with async_session_factory() as session:
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.id == target_user_id))
        target_user = result.scalar_one_or_none()
        
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        await session.delete(target_user)
        await session.commit()
        
        return {"success": True, "message": "User deleted successfully"}


# ============================================================================
# API Key Management
# ============================================================================

@router.get("/api-keys")
async def api_list_api_keys(request: Request):
    """List user's API keys"""
    session_token = request.cookies.get("aidp_session")
    user = await AuthService.validate_session(session_token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    from sqlalchemy import select
    from app.db.database import async_session_factory
    
    async with async_session_factory() as session:
        result = await session.execute(
            select(ApiKey).where(ApiKey.user_id == user.id, ApiKey.is_active == True)
        )
        keys = result.scalars().all()
        
        return {"items": [k.to_dict() for k in keys]}


@router.post("/api-keys")
async def api_create_api_key(request: Request, label: str = "Default", expires_days: int = None):
    """Create a new API key"""
    session_token = request.cookies.get("aidp_session")
    user = await AuthService.validate_session(session_token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    api_key, raw_key = await AuthService.create_api_key(
        user_id=user.id,
        label=label,
        expires_days=expires_days
    )
    
    return {
        "success": True,
        "key": raw_key,
        "key_id": str(api_key.id),
        "message": "Please copy this key now. It will not be shown again."
    }


@router.delete("/api-keys/{key_id}")
async def api_revoke_api_key(request: Request, key_id: str):
    """Revoke an API key"""
    session_token = request.cookies.get("aidp_session")
    user = await AuthService.validate_session(session_token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        key_uuid = uuid.UUID(key_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid key ID")
    
    success = await AuthService.revoke_api_key(key_uuid, user.id)
    
    if success:
        return {"success": True, "message": "API key revoked"}
    else:
        raise HTTPException(status_code=404, detail="API key not found")


# ============================================================================
# Dependency for protecting routes
# ============================================================================

async def get_current_user(request: Request) -> Optional[User]:
    """Dependency to get current user from session"""
    session_token = request.cookies.get("aidp_session")
    if not session_token:
        return None
    return await AuthService.validate_session(session_token)


async def require_auth(request: Request) -> User:
    """Dependency that requires authentication"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


async def require_admin(request: Request) -> User:
    """Dependency that requires admin role"""
    user = await require_auth(request)
    if not PermissionService.is_admin(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
