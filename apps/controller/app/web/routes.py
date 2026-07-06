from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
import httpx

from app.services.tool_registry import get_tool
from app.services.auth_service import AuthService, PermissionService
from app.db.auth_models import UserRole

# Setup templates
templates_dir = Path(__file__).parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(templates_dir)))

router = APIRouter()


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


async def get_current_user_from_request(request: Request):
    """Get current user from session cookie"""
    session_token = request.cookies.get("aidp_session")
    if not session_token:
        return None
    return await AuthService.validate_session(session_token)


# ============================================================================
# Authentication Pages
# ============================================================================

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = None, next: str = "/"):
    """Login page - Unified Authentication"""
    # Check if already logged in
    user = await get_current_user_from_request(request)
    if user:
        return RedirectResponse(url=next, status_code=302)
    
    return render_template(request, "auth/login.html", {
        "error": error,
        "next": next,
        "title": "Login - AIDP"
    })


@router.get("/logout")
async def logout_page(request: Request):
    """Logout page"""
    session_token = request.cookies.get("aidp_session")
    if session_token:
        await AuthService.logout(session_token)
    
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(key="aidp_session")
    return response


# ============================================================================
# Dashboard (Unified UI Entry Point)
# ============================================================================

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard - Main entry point"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    return render_template(request, "pages/dashboard.html", {
        "current_user": user.to_dict(),
        "active_page": "dashboard",
        "title": "Dashboard - AIDP"
    })


# ============================================================================
# User Profile
# ============================================================================

@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    """User profile page"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/profile", status_code=302)
    
    return render_template(request, "auth/profile.html", {
        "current_user": user.to_dict(),
        "active_page": "profile",
        "title": "Profile - AIDP"
    })


@router.get("/api-keys", response_class=HTMLResponse)
async def api_keys_page(request: Request, new_key: str = None):
    """API keys management page"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/api-keys", status_code=302)
    
    return render_template(request, "auth/api_keys.html", {
        "current_user": user.to_dict(),
        "active_page": "api-keys",
        "title": "API Keys - AIDP",
        "new_key": new_key
    })


# ============================================================================
# Admin Pages - User Management
# Admin Pages - Independent pages with unique active_page
@router.get("/admin", response_class=HTMLResponse)
async def admin_index(request: Request):
    """Admin index - redirect to users"""
    return RedirectResponse(url="/admin/users", status_code=302)


@router.get("/admin/users", response_class=HTMLResponse)
async def admin_users_page(request: Request):
    """User management page"""
    user = await get_current_user_from_request(request)
    if not user or not PermissionService.is_admin(user):
        return RedirectResponse(url="/login", status_code=302)
    return render_template(request, "admin/users.html", {
        "current_user": user.to_dict(),
        "active_page": "users",
        "title": "用户管理 - AIDP",
        "roles": [r.value for r in UserRole]
    })


@router.get("/admin/users/create", response_class=HTMLResponse)
async def admin_user_create_page(request: Request):
    """Create user page (admin only)"""
    user = await get_current_user_from_request(request)
    if not user or not PermissionService.is_admin(user):
        return RedirectResponse(url="/login", status_code=302)
    return render_template(request, "admin/user_form.html", {
        "current_user": user.to_dict(),
        "active_page": "users",
        "title": "创建用户 - AIDP",
        "roles": [r.value for r in UserRole],
        "edit_mode": False
    })


@router.get("/admin/roles", response_class=HTMLResponse)
async def admin_roles_page(request: Request):
    """Roles management page"""
    user = await get_current_user_from_request(request)
    if not user or not PermissionService.is_admin(user):
        return RedirectResponse(url="/login", status_code=302)
    return render_template(request, "admin/roles.html", {
        "current_user": user.to_dict(),
        "active_page": "roles",
        "title": "角色权限 - AIDP",
        "roles": [r.value for r in UserRole]
    })


@router.get("/admin/models", response_class=HTMLResponse)
async def admin_models_page(request: Request):
    """Models management page"""
    user = await get_current_user_from_request(request)
    if not user or not PermissionService.is_admin(user):
        return RedirectResponse(url="/login", status_code=302)
    return render_template(request, "admin/models.html", {
        "current_user": user.to_dict(),
        "active_page": "models",
        "title": "模型管理 - AIDP"
    })


@router.get("/admin/settings", response_class=HTMLResponse)
async def admin_settings_page(request: Request):
    """System settings page"""
    user = await get_current_user_from_request(request)
    if not user or not PermissionService.is_admin(user):
        return RedirectResponse(url="/login", status_code=302)
    return render_template(request, "admin/settings.html", {
        "current_user": user.to_dict(),
        "active_page": "settings",
        "title": "系统设置 - AIDP"
    })


# ============================================================================
# Tools Management
# ============================================================================

@router.get("/tools", response_class=HTMLResponse)
async def tools_list(request: Request):
    """Tools list page"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    return render_template(request, "pages/tools.html", {
        "current_user": user.to_dict(),
        "active_page": "tools",
        "title": "Tools - AIDP"
    })


@router.get("/tools/{tool_name}", response_class=HTMLResponse)
async def tool_detail(request: Request, tool_name: str):
    """Tool detail page"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    tool = await get_tool(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")
    
    return render_template(request, "pages/tool_detail.html", {
        "current_user": user.to_dict(),
        "active_page": "tools",
        "tool_name": tool_name,
        "tool": tool,
        "title": f"{tool.get('displayName', tool_name)} - AIDP"
    })


# ============================================================================
# Proxy Routes
# ============================================================================

@router.api_route("/api/proxy/{tool_name}/{path:path}", 
                  methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def proxy_to_tool(request: Request, tool_name: str, path: str):
    """Proxy requests to tools"""
    user = await get_current_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    tool = await get_tool(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")
    
    base_url = tool.get("endpoint", "").rstrip("/")
    if not base_url:
        raise HTTPException(status_code=400, detail=f"Tool {tool_name} has no endpoint")
    
    target_url = f"{base_url}/{path}"
    query_string = str(request.query_params)
    if query_string:
        target_url += f"?{query_string}"
    
    headers = {}
    for header in ["accept", "content-type", "authorization"]:
        if header in request.headers:
            headers[header] = request.headers[header]
    
    headers["X-Forwarded-By"] = "AIDP-Controller"
    headers["X-Forwarded-For"] = request.client.host if request.client else "unknown"
    headers["X-User-ID"] = str(user.id)
    headers["X-User-Role"] = user.role
    
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            body = None
            if request.method in ["POST", "PUT", "PATCH"]:
                body = await request.body()
            
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body
            )
            
            response_headers = dict(response.headers)
            for h in ["content-encoding", "transfer-encoding", "content-length"]:
                response_headers.pop(h, None)
            
            content = response.content
            content_type = response_headers.get("content-type", "")
            
            if "text/html" in content_type:
                html = content.decode("utf-8", errors="replace")
                html = rewrite_tool_html(html, tool_name, base_url)
                content = html.encode("utf-8")
                response_headers["content-length"] = str(len(content))
            
            return Response(
                content=content,
                status_code=response.status_code,
                headers=response_headers
            )
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Proxy error: {str(e)}")


def rewrite_tool_html(html: str, tool_name: str, base_url: str) -> str:
    """Rewrite tool HTML for unified UI integration"""
    import re
    
    html = html.replace("<body", '<body class="aidp-embedded"')
    
    def rewrite_link(match):
        href = match.group(1)
        if href.startswith("http") or href.startswith("#") or href.startswith("javascript:"):
            return match.group(0)
        if href.startswith("/"):
            return f'href="/tools/{tool_name}/web{href}"'
        return f'href="/tools/{tool_name}/web/{href}"'
    
    html = re.sub(r'href="([^"]*)"', rewrite_link, html)
    
    def rewrite_src(match):
        src = match.group(1)
        if src.startswith("http") or src.startswith("data:") or src.startswith("//"):
            return match.group(0)
        if src.startswith("/"):
            return f'src="/tools/{tool_name}/web{src}"'
        return f'src="/tools/{tool_name}/web/{src}"'
    
    html = re.sub(r'src="([^"]*)"', rewrite_src, html)
    
    return html


# ============================================================================
# Tool Web UI Proxy (for unified interface embedding)
# ============================================================================

@router.api_route("/tools/{tool_name}/web/{path:path}", 
                  methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def tool_web_proxy(request: Request, tool_name: str, path: str = ""):
    """Proxy tool Web UI through Controller for unified interface"""
    user = await get_current_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    tool = await get_tool(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")
    
    base_url = tool.get("endpoint", "").rstrip("/")
    if not base_url:
        raise HTTPException(status_code=400, detail=f"Tool {tool_name} has no endpoint")
    
    target_url = f"{base_url}/{path}"
    query_string = str(request.query_params)
    if query_string:
        target_url += f"?{query_string}"
    
    headers = {}
    for header in ["accept", "content-type", "authorization", "cookie"]:
        if header in request.headers:
            headers[header] = request.headers[header]
    
    headers["X-Forwarded-By"] = "AIDP-Controller"
    headers["X-Forwarded-For"] = request.client.host if request.client else "unknown"
    headers["X-User-ID"] = str(user.id)
    headers["X-User-Role"] = user.role
    
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            body = None
            if request.method in ["POST", "PUT", "PATCH"]:
                body = await request.body()
            
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                params=request.query_params
            )
            
            content_type = response.headers.get("content-type", "")
            
            if "text/html" in content_type:
                html = response.text
                html = rewrite_tool_html(html, tool_name, f"/tools/{tool_name}/web")
                return HTMLResponse(content=html, status_code=response.status_code)
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers={"content-type": content_type}
            )
    except httpx.RequestError as e:
        return HTMLResponse(
            content=f"<html><body style='background:#1f2937;color:#fff;padding:20px;'><h1>Tool Unavailable</h1><p>{tool_name} is not responding: {str(e)}</p></body></html>",
            status_code=502
        )


# ============================================================================
# Legacy Routes (for compatibility)
# ============================================================================

@router.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request):
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return render_template(request, "logs.html", {
        "current_user": user.to_dict() if user else None
    })


@router.get("/projects", response_class=HTMLResponse)
async def projects_page(request: Request):
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return render_template(request, "projects.html", {
        "current_user": user.to_dict() if user else None
    })


@router.get("/configs", response_class=HTMLResponse)
async def configs_page(request: Request):
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return render_template(request, "configs.html", {
        "current_user": user.to_dict() if user else None
    })


@router.get("/onboarding", response_class=HTMLResponse)
async def onboarding_page(request: Request):
    return render_template(request, "onboarding.html", {
        "current_user": None
    })
