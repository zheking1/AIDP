c = open('/app/app/services/auth_service.py', encoding='utf-8').read()
old = 'result = await session.execute(\n                select(User).where(User.id == user_session.user_id)\n                )\n                user = result.scalar_one_or_none()'
print('old in file:', old in c)
if old not in c:
    # Find the closest match
    idx = c.find('result = await session.execute')
    if idx >= 0:
        print('Found at', idx)
        print('File has:', repr(c[idx:idx+150]))
        print('Old has:', repr(old))