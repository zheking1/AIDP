from pathlib import Path
p = Path('/home/docker/AI-Code/controller/app/api/auth.py')
s = p.read_text()

# Add UpdateUserRequest after UpdateRemarkRequest
old = '''class UpdateRemarkRequest(BaseModel):
    remark: Optional[str] = None


class UpdateSettingsRequest(BaseModel):
    settings: dict'''

new = '''class UpdateRemarkRequest(BaseModel):
    remark: Optional[str] = None


class UpdateUserRequest(BaseModel):
    email: Optional[str] = None
    nickname: Optional[str] = None
    role: Optional[str] = None


class UpdateSettingsRequest(BaseModel):
    settings: dict'''

s = s.replace(old, new)

# Add update user endpoint after remark endpoint
update_user_endpoint = '''

@router.patch("/users/{user_id}")
async def api_update_user(request: Request, user_id: str, data: UpdateUserRequest):
    \"\"\"Update user info (admin only)\"\"\"
    session_token = request.cookies.get("aidp_session")
    current_user = await AuthService.validate_session(session_token)

    if not current_user or not PermissionService.is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    from sqlalchemy import update
    from app.db.database import async_session_factory

    values = {}
    if data.email is not None:
        values["email"] = data.email
    if data.nickname is not None:
        values["nickname"] = data.nickname
    if data.role is not None:
        try:
            UserRole(data.role)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid role: {data.role}")
        values["role"] = data.role

    if not values:
        raise HTTPException(status_code=400, detail="No fields to update")

    async with async_session_factory() as session:
        await session.execute(
            update(User).where(User.id == user_id).values(**values)
        )
        await session.commit()
    return {"success": True}

'''

s = s.replace(
    '\n@router.get("/settings")',
    update_user_endpoint + '\n@router.get("/settings")'
)

p.write_text(s)
print('OK')
