from pathlib import Path
p = Path('/home/docker/AI-Code/controller/app/web/routes.py')
s = p.read_text()

# Add edit user page route after create user route
edit_route = '''

@router.get("/admin/users/{user_id}/edit", response_class=HTMLResponse)
async def admin_user_edit_page(request: Request, user_id: str):
    """Edit user page (admin only)"""
    user = await get_current_user_from_request(request)
    if not user or not PermissionService.is_admin(user):
        return RedirectResponse(url="/login", status_code=302)
    
    from sqlalchemy import select
    from app.db.database import async_session_factory
    from app.db.auth_models import User as UserModel
    
    async with async_session_factory() as session:
        result = await session.execute(select(UserModel).where(UserModel.id == user_id))
        target_user = result.scalar_one_or_none()
    
    if not target_user:
        return RedirectResponse(url="/admin/users", status_code=302)
    
    return render_template(request, "admin/user_form.html", {
        "current_user": user.to_dict(),
        "active_page": "users",
        "title": "Edit User - AIDP",
        "roles": [r.value for r in UserRole],
        "edit_mode": True,
        "target_user": target_user.to_dict(caller_role=user.role)
    })

'''

s = s.replace(
    '\n# ============================================================================\n# Tools Management',
    edit_route + '\n# ============================================================================\n# Tools Management'
)

p.write_text(s)
print('OK')
