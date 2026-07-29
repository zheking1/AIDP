with open('/app/app/routers/projects_new.py', 'r', encoding='utf-8') as f:
    c = f.read()
c = c.replace(',tech_stack=json.dumps(data.tech_stack)', '')
with open('/app/app/routers/projects_new.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('Done')