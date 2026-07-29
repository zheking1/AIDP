with open('/app/app/services/auth_service.py', encoding='utf-8') as f:
    c = f.read()

old = "                select(User).where(User.id == user_session.user_id.hex)\n                )\n                user = result.scalar_one_or_none()"
new = "                from sqlalchemy import text as _t\n                _row = (await session.execute(_t(\"SELECT * FROM users WHERE CAST(id AS TEXT) = :uid\"), {\"uid\": str(user_session.user_id)})).fetchone()\n                if _row:\n                    _d = dict(_row._mapping)\n                    for _k in [\"created_at\",\"updated_at\",\"last_login_at\"]:\n                        if isinstance(_d.get(_k), str):\n                            _d[_k] = __import__(\"datetime\").datetime.fromisoformat(_d[_k])\n                    user = User(**_d)\n                else:\n                    user = None"

c = c.replace(old, new)

with open('/app/app/services/auth_service.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('OK')