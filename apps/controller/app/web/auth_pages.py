"""
AIDP Unified Web UI - Authentication Pages
Phase 1: Infrastructure
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

from app.services.auth_service import AuthService, PermissionService
from app.db.auth_models import UserRole

router = APIRouter()

# Setup Jinja2 for auth templates
templates_dir = Path(__file__).parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(templates_dir)))


def get_template(template_name: str):
    """Get Jinja2 template"""
    return jinja_env.get_template(template_name)


def render_template(request: Request, template_name: str, context: dict = None):
    """Render template with common context"""
    if context is None:
        context = {}
    context["request"] = request
    template = get_template(template_name)
    html = template.render(context)
    return HTMLResponse(content=html)


# ============================================================================
# Public Pages
# ============================================================================

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = None, next: str = "/"):
    """Login page"""
    # If already logged in, redirect to home
    session_token = request.cookies.get("aidp_session")
    if session_token:
        user = await AuthService.validate_session(session_token)
        if user:
            return RedirectResponse(url=next, status_code=302)
    
    return render_template(request, "auth/login.html", {
        "error": error,
        "next": next,
        "title": "Login - AIDP"
    })


@router.get("/logout")
async def logout_page(request: Request):
    """Logout and redirect to login"""
    session_token = request.cookies.get("aidp_session")
    if session_token:
        await AuthService.logout(session_token)
    
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(key="aidp_session")
    return response


# ============================================================================
# Protected Pages - User Profile
# ============================================================================

@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    """User profile page"""
    session_token = request.cookies.get("aidp_session")
    user = await AuthService.validate_session(session_token)
    
    if not user:
        return RedirectResponse(url="/login?next=/profile", status_code=302)
    
    return render_template(request, "auth/profile.html", {
        "user": user.to_dict(),
        "title": "Profile - AIDP"
    })


# ============================================================================
# Admin Pages - User Management
# ============================================================================

@router.get("/admin/users", response_class=HTMLResponse)
async def admin_users_page(request: Request):
    """User management page (admin only)"""
    session_token = request.cookies.get("aidp_session")
    user = await AuthService.validate_session(session_token)
    
    if not user or not PermissionService.is_admin(user):
        return RedirectResponse(url="/login", status_code=302)
    
    return render_template(request, "admin/users.html", {
        "user": user.to_dict(),
        "title": "User Management - AIDP",
        "roles": [r.value for r in UserRole]
    })


@router.get("/admin/users/create", response_class=HTMLResponse)
async def admin_user_create_page(request: Request):
    """Create user page (admin only)"""
    session_token = request.cookies.get("aidp_session")
    user = await AuthService.validate_session(session_token)
    
    if not user or not PermissionService.is_admin(user):
        return RedirectResponse(url="/login", status_code=302)
    
    return render_template(request, "admin/user_form.html", {
        "user": user.to_dict(),
        "title": "Create User - AIDP",
        "roles": [r.value for r in UserRole],
        "edit_mode": False
    })


# ============================================================================
# API Keys Page
# ============================================================================

@router.get("/api-keys", response_class=HTMLResponse)
async def api_keys_page(request: Request, new_key: str = None):
    """API keys management page"""
    session_token = request.cookies.get("aidp_session")
    user = await AuthService.validate_session(session_token)
    
    if not user:
        return RedirectResponse(url="/login?next=/api-keys", status_code=302)
    
    return render_template(request, "auth/api_keys.html", {
        "user": user.to_dict(),
        "title": "API Keys - AIDP",
        "new_key": new_key
    })
