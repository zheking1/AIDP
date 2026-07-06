from pathlib import Path
p = Path('/home/docker/AI-Code/controller/app/api/auth.py')
s = p.read_text()

# Add ResetPasswordRequest after UpdateRemarkRequest
old = '''class UpdateRemarkRequest(BaseModel):
    remark: Optional[str] = None


class RegisterRequest(BaseModel):'''

new = '''class UpdateRemarkRequest(BaseModel):
    remark: Optional[str] = None


class ResetPasswordRequest(BaseModel):
    user_id: str
    new_password: str


class RegisterRequest(BaseModel):'''

s = s.replace(old, new)

# Add admin reset password endpoint after update user endpoint
reset_endpoint = '''

@router.post("/users/{user_id}/reset-password")
async def api_admin_reset_password(request: Request, user_id: str, data: ResetPasswordRequest):
    \"\"\"Admin reset user password\"\"\"
    session_token = request.cookies.get("aidp_session")
    current_user = await AuthService.validate_session(session_token)

    if not current_user or not PermissionService.is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    from sqlalchemy import select, update
    from app.db.database import async_session_factory
    from app.db.auth_models import User as UserModel
    from app.services.auth_service import get_password_hash

    async with async_session_factory() as session:
        result = await session.execute(select(UserModel).where(UserModel.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        hashed = get_password_hash(data.new_password)
        await session.execute(
            update(UserModel).where(UserModel.id == user_id).values(password_hash=hashed)
        )
        await session.commit()
    return {"success": True, "message": "Password reset successfully"}

'''

s = s.replace(
    '\n@router.get("/settings")',
    reset_endpoint + '\n@router.get("/settings")'
)

p.write_text(s)
print('OK')
