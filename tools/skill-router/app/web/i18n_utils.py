from fastapi import Request
from jinja2 import Environment, FileSystemLoader

from app.i18n import get_translator

_loader = Environment(loader=FileSystemLoader("app/web/templates"))


def get_env():
    return _loader


def get_translator_for_request(request: Request):
    lang = request.session.get("lang", "zh")
    return get_translator(lang), lang


def render_template(name: str, request: Request, **context):
    t = _loader.get_template(name)
    _, lang = get_translator_for_request(request)
    trans = get_translator(lang)
    ctx = {"_": trans, "lang": lang, "request": request, **context}
    from fastapi.responses import HTMLResponse
    return HTMLResponse(t.render(**ctx))
