with open('/app/app/services/auth_service.py', encoding='utf-8') as f:
    c = f.read()

# Disable last_login update
c = c.replace('user.last_login_at = datetime.utcnow()', '# last_login disabled')

# Fix UUID comparison: use raw SQL with CAST
old = "user = await session.get(User, user_session.user_id)"
new = '''from sqlalchemy import text as _txt
                _row = (await session.execute(_txt("SELECT * FROM users WHERE CAST(id AS TEXT) = :uid"), {"uid": str(user_session.user_id)})).fetchone()
                if _row:
                    user = User(**dict(_row._mapping))
                    if isinstance(user.created_at, str):
                        from datetime import datetime
                        user.created_at = datetime.fromisoformat(user.created_at)
                    if isinstance(user.updated_at, str):
                        user.updated_at = datetime.fromisoformat(user.updated_at)
                else:
                    user = None'''
c = c.replace(old, new)

with open('/app/app/services/auth_service.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('OK')