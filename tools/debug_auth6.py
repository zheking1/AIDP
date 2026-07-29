import sys; sys.path.insert(0, '/app')
from app.db.database import async_session_factory
from app.db.auth_models import User, UserSession
from sqlalchemy import select, and_
from datetime import datetime
import asyncio

async def go():
    async with async_session_factory() as s:
        # Print raw tokens for comparison
        rs = await s.execute(select(UserSession))
        for x in rs.scalars():
            print(f'DB token: [{x.session_token}] len={len(x.session_token)}')
        
        # Get the first token
        rs = await s.execute(select(UserSession))
        first = rs.scalar_one_or_none()
        if first:
            t = first.session_token
            print(f'\nFirst token repr: {repr(t)}')
            print(f'First token hex: {t.encode().hex()}')
            
            # Now try to find by this exact token
            r2 = await s.execute(
                select(UserSession).where(UserSession.session_token == t)
            )
            found = r2.scalar_one_or_none()
            print(f'Find by exact token: {found}')

asyncio.run(go())