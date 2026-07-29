with open('/app/app/services/auth_service.py', encoding='utf-8') as f:
    c = f.read()

c = c.replace(
    'SELECT * FROM users WHERE id = :uid',
    'SELECT * FROM users WHERE CAST(id AS TEXT) = :uid'
)
c = c.replace(
    'user = User(**dict(_row._mapping))',
    '''d = dict(_row._mapping)
                    for k in ["created_at","updated_at","last_login_at"]:
                        if isinstance(d.get(k), str):
                            from datetime import datetime as _dt
                            d[k] = _dt.fromisoformat(d[k])
                    user = User(**d)'''
)

with open('/app/app/services/auth_service.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('OK')