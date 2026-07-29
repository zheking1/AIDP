with open('/app/app/services/auth_service.py', encoding='utf-8') as f:
    c = f.read()
c = c.replace("select(User).where(User.id == user_session.user_id)", "select(User).where(User.id == user_session.user_id.hex)")
with open('/app/app/services/auth_service.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('OK')