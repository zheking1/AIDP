from pathlib import Path
p = Path('/home/docker/AI-Code/controller/app/api/auth.py')
s = p.read_text()

# Add RegisterRequest after CreateUserRequest
old = '''class UpdateUserRequest(BaseModel):
    email: Optional[str] = None
    nickname: Optional[str] = None
    role: Optional[str] = None'''

new = '''class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    nickname: Optional[str] = None


class UpdateUserRequest(BaseModel):
    email: Optional[str] = None
    nickname: Optional[str] = None
    role: Optional[str] = None'''

s = s.replace(old, new)

# Add registration endpoint after login endpoint
register_endpoint = '''

@router.post("/register")
async def api_register(request: Request, data: RegisterRequest):
    """Register a new user (if registration is enabled)"""
    # Check if registration is enabled
    from sqlalchemy import select
    from app.db.database import async_session_factory
    from app.db.auth_models import SystemSetting

    async with async_session_factory() as session:
        result = await session.execute(
            select(SystemSetting).where(SystemSetting.key == "auth.allow_registration")
        )
        setting = result.scalar_one_or_none()

    if not setting or setting.value != "true":
        raise HTTPException(status_code=403, detail="Registration is disabled")

    try:
        user = await AuthService.create_user(
            username=data.username,
            password=data.password,
            email=data.email,
            nickname=data.nickname,
            role=UserRole.USER
        )
        return {"success": True, "message": "Registration successful. Please login."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

'''

s = s.replace(
    '\n# User Management API (Admin only)',
    register_endpoint + '\n# User Management API (Admin only)'
)

p.write_text(s)
print('OK')
