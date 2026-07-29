c = open('/app/app/services/auth_service.py', encoding='utf-8').read()
i = c.find('await session.commit()')
print(repr(c[i:i+300]))