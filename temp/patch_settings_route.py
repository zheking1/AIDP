from pathlib import Path
p = Path('/home/docker/AI-Code/controller/app/web/routes.py')
s = p.read_text()

# Add settings page route after admin_user_create_page
settings_route = '''

@router.get("/admin/settings", response_class=HTMLResponse)
async def admin_settings_page(request: Request):
    """System settings page (admin only)"""
    user = await get_current_user_from_request(request)
    if not user or not PermissionService.is_admin(user):
        return RedirectResponse(url="/login", status_code=302)
    
    return render_template(request, "admin/settings.html", {
        "current_user": user.to_dict(),
        "active_page": "settings",
        "title": "System Settings - AIDP"
    })

'''

s = s.replace(
    '\n# ============================================================================\n# Tools Management',
    settings_route + '\n# ============================================================================\n# Tools Management'
)

p.write_text(s)
print('OK')
