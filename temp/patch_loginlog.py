from pathlib import Path
p = Path('/home/docker/AI-Code/controller/app/db/auth_models.py')
s = p.read_text()

# Fix LoginLog.to_dict - action is String(32), not enum
s = s.replace(
    '"action": self.action.value if self.action else None,',
    '"action": self.action if self.action else None,'
)

p.write_text(s)
print('OK')
