from pathlib import Path
p = Path('/home/docker/AI-Code/controller/app/api/auth.py')
s = p.read_text()

# Add LoginLog, AuditLog import
s = s.replace(
    'from app.db.auth_models import User, UserRole, SystemSetting',
    'from app.db.auth_models import User, UserRole, SystemSetting, LoginLog, AuditLog'
)

# Add audit log endpoints before the settings endpoints
audit_endpoints = '''

@router.get("/login-logs")
async def api_get_login_logs(request: Request, page: int = 1, size: int = 20):
    """Get login logs (admin only)"""
    session_token = request.cookies.get("aidp_session")
    current_user = await AuthService.validate_session(session_token)

    if not current_user or not PermissionService.is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    from sqlalchemy import select, func
    from app.db.database import async_session_factory

    async with async_session_factory() as session:
        query = select(LoginLog)
        count_result = await session.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar()

        query = query.order_by(LoginLog.created_at.desc()).offset((page - 1) * size).limit(size)
        result = await session.execute(query)
        logs = result.scalars().all()

    return {
        "items": [l.to_dict() for l in logs],
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size
    }


@router.get("/audit-logs")
async def api_get_audit_logs(request: Request, page: int = 1, size: int = 20):
    """Get audit logs (admin only)"""
    session_token = request.cookies.get("aidp_session")
    current_user = await AuthService.validate_session(session_token)

    if not current_user or not PermissionService.is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    from sqlalchemy import select, func
    from app.db.database import async_session_factory

    async with async_session_factory() as session:
        query = select(AuditLog)
        count_result = await session.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar()

        query = query.order_by(AuditLog.created_at.desc()).offset((page - 1) * size).limit(size)
        result = await session.execute(query)
        logs = result.scalars().all()

    return {
        "items": [l.to_dict() for l in logs],
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size
    }

'''

s = s.replace(
    '\n@router.get("/settings")',
    audit_endpoints + '\n@router.get("/settings")'
)

p.write_text(s)
print('OK')
