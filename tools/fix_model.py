with open('/app/app/models/project_new.py', 'r', encoding='utf-8') as f:
    c = f.read()
old = '"deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,'
new = old + '\n            "cover_url": None,\n            "member_count": 0,'
c = c.replace(old, new)
with open('/app/app/models/project_new.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('OK')