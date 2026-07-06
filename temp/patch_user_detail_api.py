from pathlib import Path
p = Path('/home/docker/AI-Code/controller/app/api/auth.py')
s = p.read_text()

# Add user detail endpoint after update user endpoint
detail_endpoint = '''

@router.get("/users/{user_id}")
async def api_get_user(request: Request, user_id: str):
    \"\"\"Get user detail with login history (admin only)\"\"\"
    session_token = request.cookies.get("aidp_session")
    current_user = await AuthService.validate_session(session_token)

    if not current_user or not PermissionService.is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    from sqlalchemy import select
    from app.db.database import async_session_factory

    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get login logs for this user
        log_result = await session.execute(
            select(LoginLog).where(LoginLog.user_id == user_id).order_by(LoginLog.created_at.desc()).limit(20)
        )
        login_logs = log_result.scalars().all()

    return {
        "user": user.to_dict(caller_role=current_user.role),
        "login_logs": [l.to_dict() for l in login_logs]
    }

'''

s = s.replace(
    '\n@router.get("/settings")',
    detail_endpoint + '\n@router.get("/settings")'
)

p.write_text(s)
print('OK')
