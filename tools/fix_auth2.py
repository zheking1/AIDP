with open('/app/app/services/auth_service.py', 'r', encoding='utf-8') as f:
    c = f.read()
old = "                # Update last login\n                user.last_login_at = datetime.utcnow()\n                await session.commit()"
new = "                # Update last login\n                user.last_login_at = datetime.utcnow()\n                await session.flush()"
c = c.replace(old, new)
with open('/app/app/services/auth_service.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('Fixed')