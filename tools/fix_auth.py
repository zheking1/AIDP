import re
with open('/app/app/services/auth_service.py', 'r', encoding='utf-8') as f:
    c = f.read()
old = "await session.commit()\n\n            # Log the login attempt"
new = "await session.flush()\n            await session.refresh(user)\n            await session.commit()\n\n            # Log the login attempt"
c = c.replace(old, new)
with open('/app/app/services/auth_service.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('OK')