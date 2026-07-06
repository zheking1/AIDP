from pathlib import Path
p = Path('/home/docker/AI-Code/controller/app/web/routes.py')
s = p.read_text()

# Fix register_page - compare with True instead of "true"
old = '''    if not setting or setting.value != "true":
        return RedirectResponse(url="/login", status_code=302)'''

new = '''    if not setting or setting.value not in ("true", True):
        return RedirectResponse(url="/login", status_code=302)'''

s = s.replace(old, new)

p.write_text(s)
print('OK')
