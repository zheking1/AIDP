from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

templates_dir = Path(__file__).parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(templates_dir)))

router = APIRouter()


def get_template(template_name: str):
    """获取模板"""
    return jinja_env.get_template(template_name)


def render_template(request: Request, template_name: str, context: dict = None):
    """渲染模板"""
    if context is None:
        context = {}
    context["request"] = request
    template = get_template(template_name)
    html = template.render(context)
    return HTMLResponse(content=html)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return render_template(request, "login.html")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login")
    return render_template(request, "index.html", {
        "username": request.session.get("username"),
        "role": request.session.get("role")
    })


@router.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login")
    return render_template(request, "logs.html", {
        "username": request.session.get("username"),
        "role": request.session.get("role")
    })


@router.get("/projects", response_class=HTMLResponse)
async def projects_page(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login")
    return render_template(request, "projects.html", {
        "username": request.session.get("username"),
        "role": request.session.get("role")
    })


@router.get("/projects/{project_id}", response_class=HTMLResponse)
async def project_detail_page(request: Request, project_id: int):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login")
    return render_template(request, "project_detail.html", {
        "username": request.session.get("username"),
        "role": request.session.get("role"),
        "project_id": project_id
    })


@router.get("/configs", response_class=HTMLResponse)
async def configs_page(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login")
    return render_template(request, "configs.html", {
        "username": request.session.get("username"),
        "role": request.session.get("role")
    })


@router.get("/reviews", response_class=HTMLResponse)
async def reviews_page(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login")
    return render_template(request, "reviews.html", {
        "username": request.session.get("username"),
        "role": request.session.get("role")
    })


@router.get("/audit", response_class=HTMLResponse)
async def audit_page(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login")
    return render_template(request, "audit.html", {
        "username": request.session.get("username"),
        "role": request.session.get("role")
    })


@router.get("/onboarding", response_class=HTMLResponse)
async def onboarding_page(request: Request):
    return render_template(request, "onboarding.html")
