from pathlib import Path
p = Path('/home/docker/AI-Code/controller/app/web/routes.py')
s = p.read_text()

# Add register page route after login page route
register_route = '''

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, error: str = None):
    """Registration page"""
    # Check if registration is enabled
    from sqlalchemy import select
    from app.db.database import async_session_factory
    from app.db.auth_models import SystemSetting

    async with async_session_factory() as session:
        result = await session.execute(
            select(SystemSetting).where(SystemSetting.key == "auth.allow_registration")
        )
        setting = result.scalar_one_or_none()

    if not setting or setting.value != "true":
        return RedirectResponse(url="/login", status_code=302)

    return render_template(request, "auth/register.html", {
        "error": error,
        "title": "Register - AIDP"
    })

'''

s = s.replace(
    '\n# ============================================================================\n# Dashboard',
    register_route + '\n# ============================================================================\n# Dashboard'
)

p.write_text(s)
print('OK')
