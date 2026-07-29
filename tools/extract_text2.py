c = open('/app/app/services/auth_service.py', encoding='utf-8').read()
# Find second occurrence of 'await session.commit()'
first = c.find('await session.commit()')
second = c.find('await session.commit()', first + 1)
print('Second at position', second)
if second >= 0:
    print(repr(c[second:second+250]))