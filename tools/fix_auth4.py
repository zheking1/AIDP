with open('/app/app/services/auth_service.py', 'r', encoding='utf-8') as f:
    c = f.read()
# Remove the last_login_at update entirely
c = c.replace(
    "                # Update last login\n                user.last_login_at = datetime.utcnow()",
    "                # Last login tracking disabled for stability"
)
with open('/app/app/services/auth_service.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('Fixed')