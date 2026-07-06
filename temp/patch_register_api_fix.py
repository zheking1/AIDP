from pathlib import Path
p = Path('/home/docker/AI-Code/controller/app/api/auth.py')
s = p.read_text()

# Fix api_register - compare with True instead of "true"
old = '''    if not setting or setting.value != "true":
        raise HTTPException(status_code=403, detail="Registration is disabled")'''

new = '''    if not setting or setting.value not in ("true", True):
        raise HTTPException(status_code=403, detail="Registration is disabled")'''

s = s.replace(old, new)

p.write_text(s)
print('OK')
