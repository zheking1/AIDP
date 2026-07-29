with open('/app/app/models/project_new.py', 'r', encoding='utf-8') as f:
    c = f.read()
old = '"cover_url": None,'
new = '"tech_stack": [],\n            "cover_url": None,'
c = c.replace(old, new)
with open('/app/app/models/project_new.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('OK')