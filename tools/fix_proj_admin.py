with open('/app/app/routers/projects_new.py', encoding='utf-8') as f:
    c = f.read()
c = c.replace("user=Depends(get_current_user)", "user=Depends(require_permissions(\"project:admin\"))")
with open('/app/app/routers/projects_new.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('ok')