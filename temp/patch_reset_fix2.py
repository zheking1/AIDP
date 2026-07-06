from pathlib import Path
p = Path('/home/docker/AI-Code/controller/app/api/auth.py')
s = p.read_text()

# Fix the specific line
s = s.replace(
    'from app.services.auth_service import get_password_hash',
    '# from app.services.auth_service import get_password_hash'
)
s = s.replace(
    'hashed = get_password_hash(data.new_password)',
    'hashed = AuthService.hash_password(data.new_password)'
)

p.write_text(s)
print('OK')
