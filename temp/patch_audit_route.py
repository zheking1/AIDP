from pathlib import Path
p = Path('/home/docker/AI-Code/controller/app/web/routes.py')
s = p.read_text()

# Add audit log page route after settings route
audit_route = '''

@router.get("/admin/audit-logs", response_class=HTMLResponse)
async def admin_audit_logs_page(request: Request):
    """Audit logs page (admin only)"""
    user = await get_current_user_from_request(request)
    if not user or not PermissionService.is_admin(user):
        return RedirectResponse(url="/login", status_code=302)
    
    return render_template(request, "admin/audit_logs.html", {
        "current_user": user.to_dict(),
        "active_page": "audit-logs",
        "title": "Audit Logs - AIDP"
    })

'''

s = s.replace(
    '\n# ============================================================================\n# Tools Management',
    audit_route + '\n# ============================================================================\n# Tools Management'
)

p.write_text(s)
print('OK')
