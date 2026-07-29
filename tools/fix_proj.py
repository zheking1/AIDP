import sys, re
with open('/app/app/routers/projects_new.py', 'r', encoding='utf-8') as f:
    c = f.read()
# Only fix ASSIGNMENT lines, NOT the function definition
lines = c.split('\n')
fixed = []
for line in lines:
    if 'def get_current_user_id' in line:
        fixed.append(line)  # keep as-is
    elif '= get_current_user_id(user)' in line:
        line = line.replace('get_current_user_id(user)', 'str(get_current_user_id(user))')
        fixed.append(line)
    else:
        fixed.append(line)
c = '\n'.join(fixed)
with open('/app/app/routers/projects_new.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('Fixed ' + str(c.count('str(get_current_user_id(user))')) + ' occurrences, def count: ' + str(c.count('def str(')))