import re
with open('/app/app/routers/projects_new.py', encoding='utf-8') as f:
    c = f.read()
c = re.sub(r'tech_stack=json.dumps\(data\.tech_stack\)', '', c)
c = re.sub(r', response_model=ProjectResponse', '', c)
open('/app/app/routers/projects_new.py', 'w', encoding='utf-8').write(c)
print('proj ok')