from pathlib import Path
p = Path('/home/docker/AI-Code/controller/app/api/auth.py')
s = p.read_text()

# Update to_dict calls to pass caller_role
s = s.replace(
    '"items": [u.to_dict() for u in users],',
    '"items": [u.to_dict(caller_role=current_user.role) for u in users],'
)
s = s.replace(
    'return {"success": True, "user": user.to_dict()}',
    'return {"success": True, "user": user.to_dict(caller_role=current_user.role)}'
)

# Add UpdateRemarkRequest after CreateUserRequest
s = s.replace(
    'class CreateUserRequest(BaseModel):\n    username: str\n    password: str\n    email: Optional[str] = None\n    nickname: Optional[str] = None\n    role: str = "user"',
    'class CreateUserRequest(BaseModel):\n    username: str\n    password: str\n    email: Optional[str] = None\n    nickname: Optional[str] = None\n    role: str = "user"\n\n\nclass UpdateRemarkRequest(BaseModel):\n    remark: Optional[str] = None'
)

remark_endpoint = '''

@router.patch("/users/{user_id}/remark")
async def api_update_remark(request: Request, user_id: str, data: UpdateRemarkRequest):
    """Update user remark (admin only)"""
    session_token = request.cookies.get("aidp_session")
    current_user = await AuthService.validate_session(session_token)

    if not current_user or not PermissionService.is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    from sqlalchemy import update
    from app.db.database import async_session_factory

    async with async_session_factory() as session:
        await session.execute(
            update(User).where(User.id == user_id).values(remark=data.remark)
        )
        await session.commit()
    return {"success": True}

'''

s = s.replace(
    'async def require_admin(request: Request) -> User:',
    remark_endpoint + '\nasync def require_admin(request: Request) -> User:'
)

p.write_text(s)
print('OK')
