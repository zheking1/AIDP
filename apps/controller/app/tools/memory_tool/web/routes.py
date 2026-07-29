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


@router.get("/memories", response_class=HTMLResponse)
async def memories_list(request: Request):
    return render("memories.html", {"request": request})


@router.get("/memories/new", response_class=HTMLResponse)
async def memory_new(request: Request):
    return render("form.html", {"request": request, "mode": "new"})


@router.get("/memories/graph", response_class=HTMLResponse)
async def memory_graph(request: Request):
    return render("graph.html", {"request": request})


@router.get("/memories/{memory_id}", response_class=HTMLResponse)
async def memory_detail(request: Request, memory_id: int):
    return render("detail.html", {"request": request, "memory_id": memory_id})


@router.get("/memories/{memory_id}/edit", response_class=HTMLResponse)
async def memory_edit(request: Request, memory_id: int):
    return render("form.html", {"request": request, "mode": "edit", "memory_id": memory_id})


@router.get("/context", response_class=HTMLResponse)
async def context_page(request: Request):
    return render("context.html", {"request": request})


@router.get("/review", response_class=HTMLResponse)
async def review_page(request: Request):
    return render("review.html", {"request": request})


@router.get("/search", response_class=HTMLResponse)
async def search_page(request: Request):
    return render("search.html", {"request": request})
