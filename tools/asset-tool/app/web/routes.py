from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from pathlib import Path
import jinja2

env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(Path(__file__).parent / "templates")),
    autoescape=True
)

router = APIRouter()


def render(template_name: str, context: dict = None) -> str:
    template = env.get_template(template_name)
    return template.render(context or {})


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return render("index.html", {"request": request})


@router.get("/assets", response_class=HTMLResponse)
async def assets_list(request: Request):
    return render("assets.html", {"request": request})


@router.get("/assets/new", response_class=HTMLResponse)
async def asset_new(request: Request):
    return render("form.html", {"request": request, "mode": "new"})


@router.get("/assets/{asset_id}", response_class=HTMLResponse)
async def asset_detail(request: Request, asset_id: str):
    return render("detail.html", {"request": request, "asset_id": asset_id})


@router.get("/assets/{asset_id}/edit", response_class=HTMLResponse)
async def asset_edit(request: Request, asset_id: str):
    return render("form.html", {"request": request, "mode": "edit", "asset_id": asset_id})


@router.get("/search", response_class=HTMLResponse)
async def search_page(request: Request):
    return render("search.html", {"request": request})


@router.get("/render", response_class=HTMLResponse)
async def render_page(request: Request):
    return render("render.html", {"request": request})
