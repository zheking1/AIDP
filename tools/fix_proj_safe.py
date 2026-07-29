c = open('/app/app/routers/projects_new.py', encoding='utf-8').read()
lines = c.split('\n')
new_lines = []
for line in lines:
    # Fix tech_stack in constructor
    if 'tech_stack=json.dumps(data.tech_stack)' in line:
        continue  # remove this line
    # Fix function calls: user_id = get_current_user_id(user) -> user_id = str(get_current_user_id(user))
    if '= get_current_user_id(user)' in line:
        line = line.replace('get_current_user_id(user)', 'str(get_current_user_id(user))')
    new_lines.append(line)
c = '\n'.join(new_lines)
open('/app/app/routers/projects_new.py', 'w', encoding='utf-8').write(c)
print('Fixed proj')