with open('/app/app/services/auth_service.py', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    # Disable last_login update
    if 'user.last_login_at = datetime.utcnow()' in line:
        new_lines.append('                # ' + line.strip() + '  # DISABLED\n')
    # Fix UUID comparison: session.get -> raw string comparison
    elif 'user = await session.get(User, user_session.user_id)' in line:
        new_lines.append('                from sqlalchemy import text as _t\n')
        new_lines.append('                _row = (await session.execute(_t("SELECT * FROM users WHERE id = :uid"), {"uid": str(user_session.user_id)})).fetchone()\n')
        new_lines.append('                if _row:\n')
        new_lines.append('                    user = User(**_row._mapping)\n')
        new_lines.append('                else:\n')
        new_lines.append('                    user = None\n')
    else:
        new_lines.append(line)

with open('/app/app/services/auth_service.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('OK')