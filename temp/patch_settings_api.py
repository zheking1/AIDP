from pathlib import Path
p = Path('/home/docker/AI-Code/controller/app/api/auth.py')
s = p.read_text()

# Add SystemSetting import
s = s.replace(
    'from app.db.auth_models import User, UserRole',
    'from app.db.auth_models import User, UserRole, SystemSetting'
)

# Add UpdateSettingsRequest after UpdateRemarkRequest
old = '''class UpdateRemarkRequest(BaseModel):
    remark: Optional[str] = None'''

new = '''class UpdateRemarkRequest(BaseModel):
    remark: Optional[str] = None


class UpdateSettingsRequest(BaseModel):
    settings: dict'''

s = s.replace(old, new)

# Add settings endpoints before require_admin
settings_endpoints = '''

@router.get("/settings")
async def api_get_settings(request: Request):
    """Get all system settings (admin only)"""
    session_token = request.cookies.get("aidp_session")
    current_user = await AuthService.validate_session(session_token)

    if not current_user or not PermissionService.is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    from sqlalchemy import select
    from app.db.database import async_session_factory

    async with async_session_factory() as session:
        result = await session.execute(select(SystemSetting))
        settings = result.scalars().all()
    return {"items": [s.to_dict() for s in settings]}


@router.put("/settings")
async def api_update_settings(request: Request, data: UpdateSettingsRequest):
    """Update system settings (admin only)"""
    session_token = request.cookies.get("aidp_session")
    current_user = await AuthService.validate_session(session_token)

    if not current_user or not PermissionService.is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    from sqlalchemy import select, update
    from app.db.database import async_session_factory

    async with async_session_factory() as session:
        for key, value in data.settings.items():
            await session.execute(
                update(SystemSetting).where(SystemSetting.key == key).values(
                    value=value, updated_by=current_user.id
                )
            )
        await session.commit()
    return {"success": True}

'''

s = s.replace(
    '\nasync def require_admin(request: Request) -> User:',
    settings_endpoints + '\nasync def require_admin(request: Request) -> User:'
)

p.write_text(s)
print('OK')
