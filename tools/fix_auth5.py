with open('/app/app/services/auth_service.py', encoding='utf-8') as f:
    c = f.read()
c = c.replace('user.last_login_at = datetime.utcnow()', '# last_login disabled')
with open('/app/app/services/auth_service.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('OK')