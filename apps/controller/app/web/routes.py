from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response, JSONResponse
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
import httpx

from app.services.tool_registry import get_tool
from app.services.auth_service import AuthService, PermissionService
from app.db.auth_models import UserRole

# Setup templates
templates_dir = Path(__file__).parent / "templates"
jinja_env = Environment(
    loader=FileSystemLoader(str(templates_dir)),
    auto_reload=True,
    cache_size=0  # Disable cache for development
)

router = APIRouter()


def get_template(template_name: str):
    """Get Jinja2 template"""
    return jinja_env.get_template(template_name)


def render_template(request: Request, template_name: str, context: dict = None):
    """Render template with common context"""
    if context is None:
        context = {}
    context["request"] = request
    context["embed"] = request.query_params.get("embed", False)
    context["partial"] = request.query_params.get("partial", False)
    
    # partial 模式：自动切换到 _content 模板
    if context["partial"]:
        content_tpl = template_name.rsplit(".", 1)[0] + "_content.html"
        try:
            template = get_template(content_tpl)
            html = template.render(context)
            return HTMLResponse(content=html)
        except Exception:
            pass  # 没有 _content 模板时回退到原模板
    
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
async def workspace(request: Request):
    """Workspace with tabbed interface"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return render_template(request, "layouts/workspace.html", {
        "current_user": user.to_dict(),
        "title": "AIDP Workspace"
    })


@router.get("/home", response_class=HTMLResponse)
async def home_page(request: Request):
    """Home - redirect to workspace, or render dashboard for partial"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    # Partial mode: render dashboard content fragment directly
    if request.query_params.get("partial"):
        return render_template(request, "pages/home_content.html", {
            "current_user": user.to_dict(), "active_page": "home", "title": "首页"
        })
    return RedirectResponse(url="/?tab=home", status_code=302)


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Dashboard page"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/dashboard", status_code=302)
    return render_template(request, "pages/dashboard.html", {
        "current_user": user.to_dict(), "active_page": "dashboard", "title": "仪表盘 - AIDP"
    })


@router.get("/dashboard-frame", response_class=HTMLResponse)
async def dashboard_frame(request: Request):
    """Dashboard frame content (deprecated, use ?partial=1)"""
    return RedirectResponse(url="/dashboard?partial=1", status_code=302)


# Frame pages (content only, loaded in iframe)
@router.get("/admin/users-frame", response_class=HTMLResponse)
async def users_frame(request: Request):
    """User management frame content"""
    user = await get_current_user_from_request(request)
    # Allow anonymous access for testing
    if not user:
        mock_user = {"id": "test", "username": "admin", "nickname": "Admin", "role": "super_admin"}
        return render_template(request, "admin/users-frame.html", {
            "current_user": mock_user
        })
    if not PermissionService.is_admin(user):
        return RedirectResponse(url="/login", status_code=302)
    return render_template(request, "admin/users-frame.html", {
        "current_user": user.to_dict()
    })


@router.get("/admin/roles-frame", response_class=HTMLResponse)
async def roles_frame(request: Request):
    """Roles management frame content"""
    user = await get_current_user_from_request(request)
    if not user or not PermissionService.is_admin(user):
        return RedirectResponse(url="/login", status_code=302)
    return render_template(request, "admin/roles-frame.html", {
        "current_user": user.to_dict(),
        "roles": [r.value for r in UserRole]
    })


@router.get("/admin/models-frame", response_class=HTMLResponse)
async def models_frame(request: Request):
    """Models management frame content"""
    user = await get_current_user_from_request(request)
    if not user or not PermissionService.is_admin(user):
        return RedirectResponse(url="/login", status_code=302)
    return render_template(request, "admin/models-frame.html", {
        "current_user": user.to_dict()
    })


@router.get("/admin/settings-frame", response_class=HTMLResponse)
async def settings_frame(request: Request):
    """Settings frame content"""
    user = await get_current_user_from_request(request)
    if not user or not PermissionService.is_admin(user):
        return RedirectResponse(url="/login", status_code=302)
    return render_template(request, "admin/settings-frame.html", {
        "current_user": user.to_dict()
    })


@router.get("/profile-frame", response_class=HTMLResponse)
async def profile_frame(request: Request):
    """Profile frame content"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return render_template(request, "auth/profile-frame.html", {
        "current_user": user.to_dict()
    })


@router.get("/api-keys-frame", response_class=HTMLResponse)
async def api_keys_frame(request: Request):
    """API Keys frame content"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return render_template(request, "auth/api-keys-frame.html", {
        "current_user": user.to_dict()
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
    
    return render_template(request, "auth/api_keys_content.html", {
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


@router.get("/tools-frame", response_class=HTMLResponse)
async def tools_frame(request: Request):
    """Tools list frame content (for workspace iframe)"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    return render_template(request, "pages/tools-frame.html", {
        "current_user": user.to_dict()
    })


# ============================================================================
# Project Management (AIDP Unified Platform - New)
# ============================================================================

@router.get("/projects", response_class=HTMLResponse)
async def projects_list_page(request: Request):
    """Projects list page (new unified platform)"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/projects", status_code=302)
    
    return render_template(request, "pages/projects_new.html", {
        "current_user": user.to_dict(),
        "active_page": "projects",
        "title": "项目列表 - AIDP"
    })


# ============================================================================
# Knowledge Tool Frame Routes (redirect to built-in knowledge hub)
# ============================================================================

@router.get("/knowledge-frame", response_class=HTMLResponse)
async def knowledge_frame(request: Request):
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return RedirectResponse(url="/hub/knowledge", status_code=302)


@router.get("/knowledge-frame/bindings", response_class=HTMLResponse)
async def knowledge_bindings_frame(request: Request):
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return RedirectResponse(url="/knowledge/bases", status_code=302)


@router.get("/knowledge-frame/search", response_class=HTMLResponse)
async def knowledge_search_frame(request: Request):
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return RedirectResponse(url="/knowledge/search", status_code=302)


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


# ============================================================================
# New API Routes (AIDP Unified Platform)
# ============================================================================

from fastapi.responses import JSONResponse, PlainTextResponse
from app.core.menu import get_menu_for_user
from app.core.config_loader import get_menu_config, reload_configs

@router.get("/api/menu", response_class=JSONResponse)
async def get_menu_api(request: Request):
    """
    获取动态菜单 API（新架构）
    
    返回当前用户的完整菜单配置
    """
    user = await get_current_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # 从 query param 获取 project_id
    project_id = request.query_params.get('project_id')
    
    menu = get_menu_for_user(user, project_id)
    return menu


@router.get("/api/config/menu.yaml", response_class=PlainTextResponse)
async def get_menu_config_raw(request: Request):
    """
    获取原始菜单配置（管理员用）
    
    返回菜单配置文件的原始 YAML 内容
    """
    user = await get_current_user_from_request(request)
    if not user or not PermissionService.is_admin(user):
        raise HTTPException(status_code=403, detail="Admin required")
    
    import yaml
    config = get_menu_config(use_cache=False)
    return yaml.dump(config, allow_unicode=True, sort_keys=False)


@router.post("/api/config/reload")
async def reload_config_api(request: Request):
    """
    重新加载配置（管理员用）
    
    用于热重载配置文件而不重启服务
    """
    user = await get_current_user_from_request(request)
    if not user or not PermissionService.is_admin(user):
        raise HTTPException(status_code=403, detail="Admin required")
    
    try:
        reload_configs()
        return {"success": True, "message": "Configuration reloaded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reload: {str(e)}")


# ============================================================================
# Knowledge Module Frontend Routes (AIDP Unified Platform)
# ============================================================================

@router.get("/knowledge/bases", response_class=HTMLResponse)
async def knowledge_bases_page(request: Request):
    """知识库列表页"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/knowledge/bases", status_code=302)
    
    return render_template(request, "modules/knowledge/bases.html", {
        "current_user": user.to_dict(),
        "active_page": "knowledge",
        "title": "知识库 - AIDP"
    })


@router.get("/knowledge/documents", response_class=HTMLResponse)
async def knowledge_documents_page(request: Request):
    """文档管理页"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/knowledge/documents", status_code=302)
    
    return render_template(request, "modules/knowledge/documents.html", {
        "current_user": user.to_dict(),
        "active_page": "knowledge",
        "title": "文档管理 - AIDP"
    })


@router.get("/knowledge/search", response_class=HTMLResponse)
async def knowledge_search_page(request: Request):
    """知识搜索页"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/knowledge/search", status_code=302)
    
    return render_template(request, "modules/knowledge/search.html", {
        "current_user": user.to_dict(),
        "active_page": "knowledge",
        "title": "知识搜索 - AIDP"
    })


@router.get("/hub/knowledge", response_class=HTMLResponse)
async def knowledge_hub_page(request: Request):
    """知识中心 Hub 页"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/hub/knowledge", status_code=302)
    return render_template(request, "pages/knowledge_hub.html", {
        "current_user": user.to_dict(), "active_page": "knowledge-hub", "title": "知识中心 - AIDP"
    })


@router.get("/hub/skills", response_class=HTMLResponse)
async def skills_hub_page(request: Request):
    """技能库 Hub 页"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/hub/skills", status_code=302)
    return render_template(request, "pages/skills_hub.html", {
        "current_user": user.to_dict(), "active_page": "skills-hub", "title": "技能库 - AIDP"
    })


@router.get("/hub/memory", response_class=HTMLResponse)
async def memory_hub_page(request: Request):
    """记忆中心 Hub 页"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/hub/memory", status_code=302)
    return render_template(request, "pages/memory_hub.html", {
        "current_user": user.to_dict(), "active_page": "memory-hub", "title": "记忆中心 - AIDP"
    })


@router.get("/knowledge/templates", response_class=HTMLResponse)
async def knowledge_templates_page(request: Request):
    """文档模板页"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/knowledge/templates", status_code=302)
    return render_template(request, "modules/knowledge/templates.html", {
        "current_user": user.to_dict(), "active_page": "knowledge", "title": "文档模板 - AIDP"
    })


@router.get("/knowledge/graph", response_class=HTMLResponse)
async def knowledge_graph_page(request: Request):
    """知识图谱页"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/knowledge/graph", status_code=302)
    return render_template(request, "modules/knowledge/graph.html", {
        "current_user": user.to_dict(), "active_page": "knowledge", "title": "知识图谱 - AIDP"
    })


# ============================================================================
# Memory Module Frontend Routes (AIDP Unified Platform)
# ============================================================================

@router.get("/memory/memories", response_class=HTMLResponse)
async def memory_memories_page(request: Request):
    """记忆管理页"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/memory/memories", status_code=302)
    
    return render_template(request, "modules/memory/memories.html", {
        "current_user": user.to_dict(),
        "active_page": "memory",
        "title": "记忆管理 - AIDP"
    })


@router.get("/memory/graph", response_class=HTMLResponse)
async def memory_graph_page(request: Request):
    """记忆图谱页"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/memory/graph", status_code=302)
    
    return render_template(request, "modules/memory/graph.html", {
        "current_user": user.to_dict(),
        "active_page": "memory",
        "title": "记忆图谱 - AIDP"
    })


@router.get("/memory/search", response_class=HTMLResponse)
async def memory_search_page(request: Request):
    """记忆检索页"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/memory/search", status_code=302)
    return render_template(request, "modules/memory/memories.html", {
        "current_user": user.to_dict(), "active_page": "memory", "title": "记忆检索 - AIDP",
        "mode": "search"
    })


# ============================================================================
# Skills Module Frontend Routes (AIDP Unified Platform)
# ============================================================================

@router.get("/skills/global", response_class=HTMLResponse)
async def skills_global_page(request: Request):
    """全局技能页"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/skills/global", status_code=302)
    return render_template(request, "modules/skills/global.html", {
        "current_user": user.to_dict(), "active_page": "skills", "title": "全局技能 - AIDP",
        "is_admin": user.role in ["admin", "super_admin"]
    })


@router.get("/skills/personal", response_class=HTMLResponse)
async def skills_personal_page(request: Request):
    """个人技能页"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/skills/personal", status_code=302)
    return render_template(request, "modules/skills/personal.html", {
        "current_user": user.to_dict(), "active_page": "skills", "title": "我的技能 - AIDP"
    })


@router.get("/skills/project/{project_id}", response_class=HTMLResponse)
async def skills_project_page(request: Request, project_id: int):
    """项目技能页"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/skills/project/" + str(project_id), status_code=302)
    return render_template(request, "modules/skills/personal.html", {
        "current_user": user.to_dict(), "active_page": "skills", "title": "项目技能 - AIDP",
        "scope": "project", "project_id": project_id
    })


# ============================================================================
# Assets Module Frontend Routes (AIDP Unified Platform)
# ============================================================================

@router.get("/assets", response_class=HTMLResponse)
async def assets_list_page(request: Request):
    """资产列表页"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/assets", status_code=302)
    return render_template(request, "modules/assets/list.html", {
        "current_user": user.to_dict(), "active_page": "assets", "title": "代码资产 - AIDP"
    })


@router.get("/assets/search", response_class=HTMLResponse)
async def assets_search_page(request: Request):
    """资产搜索页"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/assets/search", status_code=302)
    return render_template(request, "modules/assets/list.html", {
        "current_user": user.to_dict(), "active_page": "assets", "title": "资产搜索 - AIDP"
    })


# ============================================================================
# Sandbox Module Frontend Routes (AIDP Unified Platform)
# ============================================================================

@router.get("/sandbox", response_class=HTMLResponse)
async def sandbox_page(request: Request):
    """代码沙箱页"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/sandbox", status_code=302)
    return render_template(request, "modules/sandbox/index.html", {
        "current_user": user.to_dict(), "active_page": "devtools", "title": "代码沙箱 - AIDP"
    })


# ============================================================================
# Quality Module Frontend Routes (AIDP Unified Platform)
# ============================================================================

@router.get("/quality", response_class=HTMLResponse)
async def quality_page(request: Request):
    """质量检查页"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/quality", status_code=302)
    return render_template(request, "modules/quality/index.html", {
        "current_user": user.to_dict(), "active_page": "devtools", "title": "质量检查 - AIDP"
    })


# ============================================================================
# Rules Module Frontend Routes (AIDP Unified Platform)
# ============================================================================

@router.get("/rules/global", response_class=HTMLResponse)
async def rules_global_page(request: Request):
    """全局规则页"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/rules/global", status_code=302)
    return render_template(request, "modules/rules/global.html", {
        "current_user": user.to_dict(), "active_page": "rules", "title": "全局规则 - AIDP",
        "is_admin": user.role in ["admin", "super_admin"]
    })


@router.get("/rules/personal", response_class=HTMLResponse)
async def rules_personal_page(request: Request):
    """个人规则页"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/rules/personal", status_code=302)
    return render_template(request, "modules/rules/personal.html", {
        "current_user": user.to_dict(), "active_page": "rules", "title": "我的规则 - AIDP"
    })


@router.get("/rules/project/{project_id}", response_class=HTMLResponse)
async def rules_project_page(request: Request, project_id: int):
    """项目规则页"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/rules/project/" + str(project_id), status_code=302)
    return render_template(request, "modules/rules/personal.html", {
        "current_user": user.to_dict(), "active_page": "rules", "title": "项目规则 - AIDP"
    })


# ============================================================================
# Agents Module Frontend Routes (AIDP Unified Platform)
# ============================================================================

@router.get("/agents", response_class=HTMLResponse)
async def agents_list_page(request: Request):
    """Agent 管理页"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/agents", status_code=302)
    return render_template(request, "modules/agents/list.html", {
        "current_user": user.to_dict(), "active_page": "agents", "title": "Agent 管理 - AIDP"
    })


@router.get("/project/{project_id}/agents", response_class=HTMLResponse)
async def project_agents_page(request: Request, project_id: int):
    """项目 Agent 页"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/project/" + str(project_id) + "/agents", status_code=302)
    return render_template(request, "modules/agents/list.html", {
        "current_user": user.to_dict(), "active_page": "agents", "title": "项目 Agent - AIDP"
    })


# ============================================================================
# Workflows Module Frontend Routes (AIDP Unified Platform)
# ============================================================================

@router.get("/workflows", response_class=HTMLResponse)
async def workflows_list_page(request: Request):
    """流程管理列表页"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/workflows", status_code=302)
    return render_template(request, "modules/workflows/list.html", {
        "current_user": user.to_dict(), "active_page": "workflows", "title": "流程管理 - AIDP"
    })


@router.get("/project/{project_id}/workflows", response_class=HTMLResponse)
async def project_workflows_page(request: Request, project_id: int):
    """项目流程页"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/project/" + str(project_id) + "/workflows", status_code=302)
    return render_template(request, "modules/workflows/list.html", {
        "current_user": user.to_dict(), "active_page": "workflows", "title": "项目流程 - AIDP"
    })


# ============================================================================
# Admin Pages (AIDP Unified Platform)
# ============================================================================

@router.get("/admin/projects", response_class=HTMLResponse)
async def admin_projects_page(request: Request):
    """管理员项目管理页"""
    user = await get_current_user_from_request(request)
    if not user or user.role not in ('admin', 'super_admin'):
        return RedirectResponse(url="/login?next=/admin/projects", status_code=302)
    return render_template(request, "admin/projects.html", {
        "current_user": user.to_dict(), "active_page": "admin", "title": "项目管理 - AIDP"
    })


@router.get("/admin/skills", response_class=HTMLResponse)
async def admin_skills_page(request: Request):
    """管理员技能管理页"""
    user = await get_current_user_from_request(request)
    if not user or user.role not in ('admin', 'super_admin'):
        return RedirectResponse(url="/login?next=/admin/skills", status_code=302)
    return render_template(request, "admin/skills.html", {
        "current_user": user.to_dict(), "active_page": "admin", "title": "技能管理 - AIDP"
    })


@router.get("/admin/audit-logs", response_class=HTMLResponse)
async def admin_audit_logs_page(request: Request):
    """管理员审计日志页"""
    user = await get_current_user_from_request(request)
    if not user or user.role not in ('admin', 'super_admin'):
        return RedirectResponse(url="/login?next=/admin/audit-logs", status_code=302)
    return render_template(request, "admin/audit_logs.html", {
        "current_user": user.to_dict(), "active_page": "admin", "title": "审计日志 - AIDP"
    })


@router.get("/admin/rules", response_class=HTMLResponse)
async def admin_rules_page(request: Request):
    """管理员全局规则页"""
    user = await get_current_user_from_request(request)
    if not user or user.role not in ('admin', 'super_admin'):
        return RedirectResponse(url="/login?next=/admin/rules", status_code=302)
    return render_template(request, "modules/rules/global.html", {
        "current_user": user.to_dict(), "active_page": "admin", "title": "全局规则 - AIDP"
    })


# ============================================================================
# Project Dashboard & Settings Pages (AIDP Unified Platform)
# ============================================================================

@router.get("/project/{project_id}/dashboard", response_class=HTMLResponse)
async def project_dashboard_page(request: Request, project_id: int):
    """项目仪表盘页"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/project/" + str(project_id) + "/dashboard", status_code=302)
    return render_template(request, "pages/project_dashboard.html", {
        "current_user": user.to_dict(), "active_page": "dashboard", "project_id": project_id, "title": "项目仪表盘 - AIDP"
    })


@router.get("/project/{project_id}/settings/general", response_class=HTMLResponse)
async def project_settings_general(request: Request, project_id: int):
    """项目设置 - 基本信息"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/project/" + str(project_id) + "/settings/general", status_code=302)
    return render_template(request, "pages/project_settings/general.html", {
        "current_user": user.to_dict(), "active_page": "project-settings", "project_id": project_id, "active_tab": "general", "title": "项目设置 - AIDP"
    })


@router.get("/project/{project_id}/settings/instructions", response_class=HTMLResponse)
async def project_settings_instructions(request: Request, project_id: int):
    """项目设置 - AI配置"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/project/" + str(project_id) + "/settings/instructions", status_code=302)
    return render_template(request, "pages/project_settings/instructions.html", {
        "current_user": user.to_dict(), "active_page": "project-settings", "project_id": project_id, "active_tab": "instructions", "title": "AI配置 - AIDP"
    })


@router.get("/project/{project_id}/settings/knowledge/general", response_class=HTMLResponse)
async def project_settings_knowledge(request: Request, project_id: int):
    """项目设置 - 知识库配置"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/project/" + str(project_id) + "/settings/knowledge/general", status_code=302)
    return render_template(request, "pages/project_settings/knowledge.html", {
        "current_user": user.to_dict(), "active_page": "project-settings", "project_id": project_id, "active_tab": "knowledge", "title": "知识库配置 - AIDP"
    })


@router.get("/project/{project_id}/settings/members", response_class=HTMLResponse)
async def project_settings_members(request: Request, project_id: int):
    """项目设置 - 成员管理"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/project/" + str(project_id) + "/settings/members", status_code=302)
    return render_template(request, "pages/project_settings/members.html", {
        "current_user": user.to_dict(), "active_page": "project-settings", "project_id": project_id, "active_tab": "members", "title": "成员管理 - AIDP"
    })


@router.get("/project/{project_id}/settings/integrations/git", response_class=HTMLResponse)
async def project_settings_integrations(request: Request, project_id: int):
    """项目设置 - 集成"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/project/" + str(project_id) + "/settings/integrations/git", status_code=302)
    return render_template(request, "pages/project_settings/integrations.html", {
        "current_user": user.to_dict(), "active_page": "project-settings", "project_id": project_id, "active_tab": "integrations", "title": "集成配置 - AIDP"
    })


# ============================================================================
# Project-scoped module redirects (menu uses /project/{id}/... paths)
# ============================================================================

@router.get("/project/{project_id}/knowledge/documents", response_class=HTMLResponse)
async def project_knowledge_docs(request: Request, project_id: int):
    """项目知识文档（直接渲染，支持 partial）"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/project/" + str(project_id) + "/knowledge/documents", status_code=302)
    return render_template(request, "modules/knowledge/documents.html", {
        "current_user": user.to_dict(), "project_id": project_id
    })


@router.get("/project/{project_id}/knowledge/search", response_class=HTMLResponse)
async def project_knowledge_search(request: Request, project_id: int):
    """项目知识搜索（直接渲染，支持 partial）"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/project/" + str(project_id) + "/knowledge/search", status_code=302)
    return render_template(request, "modules/knowledge/search.html", {
        "current_user": user.to_dict(), "project_id": project_id
    })


@router.get("/project/{project_id}/knowledge/import", response_class=HTMLResponse)
async def project_knowledge_import(request: Request, project_id: int):
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/project/" + str(project_id) + "/knowledge/documents", status_code=302)
    return RedirectResponse(url=f"/project/{project_id}/knowledge/documents", status_code=302)


@router.get("/project/{project_id}/memory/memories", response_class=HTMLResponse)
async def project_memory_list(request: Request, project_id: int):
    """项目记忆列表（直接渲染，支持 partial）"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/project/" + str(project_id) + "/memory/memories", status_code=302)
    return render_template(request, "modules/memory/memories.html", {
        "current_user": user.to_dict(), "project_id": project_id
    })


@router.get("/project/{project_id}/memory/graph", response_class=HTMLResponse)
async def project_memory_graph(request: Request, project_id: int):
    """项目记忆图谱（直接渲染，支持 partial）"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/project/" + str(project_id) + "/memory/graph", status_code=302)
    return render_template(request, "modules/memory/graph.html", {
        "current_user": user.to_dict(), "project_id": project_id
    })


@router.get("/project/{project_id}/memory/search", response_class=HTMLResponse)
async def project_memory_search(request: Request, project_id: int):
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/project/" + str(project_id) + "/memory/search", status_code=302)
    return render_template(request, "modules/memory/memories.html", {
        "current_user": user.to_dict(), "project_id": project_id
    })


@router.get("/project/{project_id}/assets", response_class=HTMLResponse)
async def project_assets_list(request: Request, project_id: int):
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/project/" + str(project_id) + "/assets", status_code=302)
    return render_template(request, "modules/assets/list.html", {
        "current_user": user.to_dict(), "project_id": project_id
    })


@router.get("/project/{project_id}/assets/search", response_class=HTMLResponse)
async def project_assets_search(request: Request, project_id: int):
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/project/" + str(project_id) + "/assets/search", status_code=302)
    return render_template(request, "modules/assets/list.html", {
        "current_user": user.to_dict(), "project_id": project_id
    })


@router.get("/project/{project_id}/sandbox", response_class=HTMLResponse)
async def project_sandbox(request: Request, project_id: int):
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/project/" + str(project_id) + "/sandbox", status_code=302)
    return render_template(request, "modules/sandbox/index.html", {
        "current_user": user.to_dict(), "project_id": project_id
    })


@router.get("/project/{project_id}/quality", response_class=HTMLResponse)
async def project_quality(request: Request, project_id: int):
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/project/" + str(project_id) + "/quality", status_code=302)
    return render_template(request, "modules/quality/index.html", {
        "current_user": user.to_dict(), "project_id": project_id
    })


@router.get("/admin/instructions", response_class=HTMLResponse)
async def admin_instructions_page(request: Request):
    """管理员指令管理页"""
    user = await get_current_user_from_request(request)
    if not user or user.role not in ('admin', 'super_admin'):
        return RedirectResponse(url="/login?next=/admin/instructions", status_code=302)
    return render_template(request, "admin/instructions_content.html", {
        "current_user": user.to_dict(), "active_page": "admin", "title": "指令管理 - AIDP"
    })


@router.get("/admin/models", response_class=HTMLResponse)
async def admin_models_page(request: Request):
    """管理员模型管理页"""
    user = await get_current_user_from_request(request)
    if not user or user.role not in ('admin', 'super_admin'):
        return RedirectResponse(url="/login?next=/admin/models", status_code=302)
    return render_template(request, "admin/models_content.html", {
        "current_user": user.to_dict(), "active_page": "admin", "title": "模型管理 - AIDP"
    })


@router.get("/admin/tools", response_class=HTMLResponse)
async def admin_tools_page(request: Request):
    """管理员工具注册管理页"""
    user = await get_current_user_from_request(request)
    if not user or user.role not in ('admin', 'super_admin'):
        return RedirectResponse(url="/login?next=/admin/tools", status_code=302)
    return render_template(request, "admin/tools_content.html", {
        "current_user": user.to_dict(), "active_page": "admin", "title": "工具管理 - AIDP"
    })


@router.get("/admin/nas", response_class=HTMLResponse)
async def admin_nas_page(request: Request):
    """管理员 NAS 文件管理页"""
    user = await get_current_user_from_request(request)
    if not user or user.role not in ('admin', 'super_admin'):
        return RedirectResponse(url="/login?next=/admin/nas", status_code=302)
    return render_template(request, "admin/nas_content.html", {
        "current_user": user.to_dict(), "active_page": "admin", "title": "NAS 文件管理 - AIDP"
    })


@router.get("/admin/configs", response_class=HTMLResponse)
async def admin_configs_page(request: Request):
    """管理员环境配置管理页"""
    user = await get_current_user_from_request(request)
    if not user or user.role not in ('admin', 'super_admin'):
        return RedirectResponse(url="/login?next=/admin/configs", status_code=302)
    return render_template(request, "admin/configs_content.html", {
        "current_user": user.to_dict(), "active_page": "admin", "title": "环境配置 - AIDP"
    })


@router.get("/admin/evolution", response_class=HTMLResponse)
async def admin_evolution_page(request: Request):
    """管理员进化管理页"""
    user = await get_current_user_from_request(request)
    if not user or user.role not in ('admin', 'super_admin'):
        return RedirectResponse(url="/login?next=/admin/evolution", status_code=302)
    return render_template(request, "admin/evolution_content.html", {
        "current_user": user.to_dict(), "active_page": "admin", "title": "进化管理 - AIDP"
    })


@router.get("/evolution", response_class=HTMLResponse)
async def evolution_list_page(request: Request):
    """项目进化列表页"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/evolution", status_code=302)
    return render_template(request, "modules/evolution/list.html", {
        "current_user": user.to_dict(), "active_page": "evolution", "title": "进化提案 - AIDP"
    })


@router.get("/api/modules", response_class=JSONResponse)
async def get_modules_api(request: Request):
    """
    获取所有模块信息
    
    返回已注册的模块列表和状态
    """
    user = await get_current_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    from app.modules import get_module_info
    return {"modules": get_module_info()}
