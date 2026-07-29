with open('/app/app/services/auth_service.py', encoding='utf-8') as f:
    c = f.read()

c = c.replace(
    'user = User(**_row._mapping)',
    'd = dict(_row._mapping)\n'
    '                    for k in ["created_at","updated_at","last_login_at"]:\n'
    '                        if isinstance(d.get(k), str):\n'
    '                            from datetime import datetime\n'
    '                            d[k] = datetime.fromisoformat(d[k])\n'
    '                    user = User(**d)'
)

with open('/app/app/services/auth_service.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('OK')