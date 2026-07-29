with open('/app/app/services/auth_service.py', encoding='utf-8') as f:
    c = f.read()

# Fix: use datetime.datetime instead of local import
c = c.replace(
    'from datetime import datetime\n'
    '                            d[k] = datetime.fromisoformat(d[k])',
    'd[k] = __import__("datetime").datetime.fromisoformat(d[k])'
)

with open('/app/app/services/auth_service.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('OK')