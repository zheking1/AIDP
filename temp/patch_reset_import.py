from pathlib import Path
p = Path('/home/docker/AI-Code/controller/app/api/auth.py')
s = p.read_text()

# Fix import - use AuthService.hash_password instead of get_password_hash
old = '''        from app.services.auth_service import get_password_hash

    async with async_session_factory() as session:
        result = await session.execute(select(UserModel).where(UserModel.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        hashed = get_password_hash(data.new_password)'''

new = '''    async with async_session_factory() as session:
        result = await session.execute(select(UserModel).where(UserModel.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        hashed = AuthService.hash_password(data.new_password)'''

s = s.replace(old, new)

p.write_text(s)
print('OK')
