from pathlib import Path
p = Path('/home/docker/AI-Code/controller/app/web/routes.py')
s = p.read_text()

# Add user detail page route after edit user route
detail_route = '''

@router.get("/admin/users/{user_id}", response_class=HTMLResponse)
async def admin_user_detail_page(request: Request, user_id: str):
    """User detail page (admin only)"""
    user = await get_current_user_from_request(request)
    if not user or not PermissionService.is_admin(user):
        return RedirectResponse(url="/login", status_code=302)
    
    return render_template(request, "admin/user_detail.html", {
        "current_user": user.to_dict(),
        "active_page": "users",
        "title": "User Detail - AIDP",
        "target_user_id": user_id
    })

'''

# Insert before the edit user route to avoid route conflict
s = s.replace(
    '\n@router.get("/admin/users/{user_id}/edit"',
    detail_route + '\n@router.get("/admin/users/{user_id}/edit"'
)

p.write_text(s)
print('OK')
