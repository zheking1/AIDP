with open('/app/app/services/auth_service.py', encoding='utf-8') as f:
    c = f.read()

old = '''result = await session.execute(
                    select(User).where(User.id == user_session.user_id)
                )
                user = result.scalar_one_or_none()'''

new = '''from sqlalchemy import text as _txt
                _row = (await session.execute(_txt("SELECT * FROM users WHERE CAST(id AS TEXT) = :uid"), {"uid": str(user_session.user_id)})).fetchone()
                if _row:
                    d = dict(_row._mapping)
                    for k in ["created_at","updated_at","last_login_at"]:
                        if isinstance(d.get(k), str):
                            d[k] = __import__("datetime").datetime.fromisoformat(d[k])
                    user = User(**d)
                else:
                    user = None'''

c = c.replace(old, new)

with open('/app/app/services/auth_service.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('OK')