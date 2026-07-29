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


@router.get("/documents", response_class=HTMLResponse)
async def documents_list(request: Request):
    return render("documents.html", {"request": request})


@router.get("/documents/new", response_class=HTMLResponse)
async def document_new(request: Request):
    return render("upload.html", {"request": request})


@router.get("/documents/{document_id}", response_class=HTMLResponse)
async def document_detail(request: Request, document_id: str):
    return render("document_detail.html", {"request": request, "document_id": document_id})


@router.get("/search", response_class=HTMLResponse)
async def search_page(request: Request):
    return render("search.html", {"request": request})


@router.get("/knowledge-bases", response_class=HTMLResponse)
async def knowledge_bases_page(request: Request):
    return render("knowledge-bases.html", {"request": request})


@router.get("/knowledge-bases/{kb_id}", response_class=HTMLResponse)
async def knowledge_base_detail(request: Request, kb_id: str):
    return render("knowledge-base-detail.html", {"request": request, "kb_id": kb_id})


@router.get("/project-bindings", response_class=HTMLResponse)
async def project_bindings_page(request: Request):
    return render("project-bindings.html", {"request": request})