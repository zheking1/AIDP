import uuid

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import text

from app.i18n import get_translator
from app.web.i18n_utils import render_template

router = APIRouter()

import os

ADMIN_USER = "admin"
ADMIN_PASS = os.environ.get("ADMIN_PASSWORD", "admin123")


@router.get("/login")
async def login_page(request: Request, error: str = ""):
    if request.session.get("user"):
        return RedirectResponse(url="/skills", status_code=302)
    return render_template("login.html", request, error=error)


@router.post("/login")
async def login(request: Request):
    form = await request.form()
    username = form.get("username", "")
    password = form.get("password", "")

    from app.db.init_db import get_session
    async with get_session() as db:
        result = await db.execute(
            text("SELECT id, password, role, is_active FROM users WHERE username = :u"),
            {"u": username},
        )
        row = result.first()

    if row:
        import bcrypt
        stored_hash = row[1]
        is_active = row[3]
        if is_active is not True and username != ADMIN_USER:
            t = get_translator(request.session.get("lang", "zh"))
            return render_template("login.html", request, error=t("Account is disabled"))
        if stored_hash and bcrypt.checkpw(password.encode(), stored_hash.encode()):
            request.session["user"] = {
                "id": str(row[0]),
                "username": username,
                "role": str(row[2]) if row[2] else "user",
            }
            return RedirectResponse(url="/skills", status_code=302)

    # fallback: hardcoded admin
    if username == ADMIN_USER and password == ADMIN_PASS:
        async with get_session() as db:
            result = await db.execute(text("SELECT id, role FROM users WHERE username = :u"), {"u": ADMIN_USER})
            row = result.first()
            uid = str(row[0]) if row else str(uuid.UUID(int=1))
            role = str(row[1]) if row else "admin"
        request.session["user"] = {"id": uid, "username": ADMIN_USER, "role": role}
        return RedirectResponse(url="/skills", status_code=302)

    t = get_translator(request.session.get("lang", "zh"))
    return render_template("login.html", request, error=t("Invalid credentials"))


@router.get("/register")
async def register_page(request: Request, error: str = ""):
    if request.session.get("user"):
        return RedirectResponse(url="/skills", status_code=302)
    return render_template("register.html", request, error=error)


@router.post("/register")
async def register(request: Request):
    if request.session.get("user"):
        return RedirectResponse(url="/skills", status_code=302)
    form = await request.form()
    username = form.get("username", "").strip()
    password = form.get("password", "")
    t = get_translator(request.session.get("lang", "zh"))
    if not username or not password:
        return render_template("register.html", request, error=t("Username and password required"))
    if len(password) < 6:
        return render_template("register.html", request, error=t("Password must be at least 6 characters"))
    import bcrypt
    from app.db.init_db import get_session
    from app.db.models import User
    from sqlalchemy import select
    async with get_session() as db:
        existing = await db.execute(select(User).where(User.username == username))
        if existing.scalar_one_or_none():
            return render_template("register.html", request, error=t("Username already exists"))
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        new_user = User(username=username, password=hashed, role="user")
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        request.session["user"] = {"id": str(new_user.id), "username": username, "role": "user"}
    return RedirectResponse(url="/skills", status_code=302)


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)


@router.get("/lang/{code}")
async def set_lang(request: Request, code: str):
    if code in ("en", "zh"):
        request.session["lang"] = code
    referer = request.headers.get("referer", "/skills")
    return RedirectResponse(url=referer, status_code=302)
