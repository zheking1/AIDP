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


@router.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    return render("history.html", {"request": request})
