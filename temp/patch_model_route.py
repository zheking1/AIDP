from pathlib import Path
p = Path('/home/docker/AI-Code/controller/app/web/routes.py')
s = p.read_text()

# Add model management page route after audit logs route
model_route = '''

@router.get("/admin/models", response_class=HTMLResponse)
async def admin_models_page(request: Request):
    """AI Model management page (admin only)"""
    user = await get_current_user_from_request(request)
    if not user or not PermissionService.is_admin(user):
        return RedirectResponse(url="/login", status_code=302)
    
    return render_template(request, "admin/models.html", {
        "current_user": user.to_dict(),
        "active_page": "models",
        "title": "Model Management - AIDP"
    })

'''

s = s.replace(
    '\n# ============================================================================\n# Tools Management',
    model_route + '\n# ============================================================================\n# Tools Management'
)

p.write_text(s)
print('OK')
