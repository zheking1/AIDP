with open('/app/app/services/auth_service.py', 'r', encoding='utf-8') as f:
    c = f.read()
# Remove the early commit/flush for last_login_at
c = c.replace(
    "                # Update last login\n                user.last_login_at = datetime.utcnow()\n                await session.flush()\n                await session.refresh(user)\n                await session.commit()",
    "                # Update last login\n                user.last_login_at = datetime.utcnow()"
)
with open('/app/app/services/auth_service.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('Fixed')