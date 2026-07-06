from pathlib import Path
p = Path('/home/docker/AI-Code/controller/app/web/routes.py')
s = p.read_text()

# Add tools management page route after models route
tools_route = '''

@router.get("/admin/tools", response_class=HTMLResponse)
async def admin_tools_page(request: Request):
    """Tool management page (admin only)"""
    user = await get_current_user_from_request(request)
    if not user or not PermissionService.is_admin(user):
        return RedirectResponse(url="/login", status_code=302)
    
    return render_template(request, "admin/tools.html", {
        "current_user": user.to_dict(),
        "active_page": "tools-admin",
        "title": "Tool Management - AIDP"
    })

'''

s = s.replace(
    '\n# ============================================================================\n# Tools Management',
    tools_route + '\n# ============================================================================\n# Tools Management'
)

p.write_text(s)
print('OK')
