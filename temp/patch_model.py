from pathlib import Path
p = Path('/home/docker/AI-Code/controller/app/db/auth_models.py')
s = p.read_text()

old = '''        if include_sensitive:
            data["password_hash"] = self.password_hash
        return data'''

new = '''        if include_sensitive:
            data["password_hash"] = self.password_hash
        if caller_role in ("super_admin", "admin"):
            data["remark"] = self.remark
        return data'''

s = s.replace(old, new)
p.write_text(s)
print('OK')
