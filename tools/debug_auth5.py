import sys; sys.path.insert(0, '/app')
from app.db.database import async_session_factory
from app.db.auth_models import User, UserSession
from sqlalchemy import select, and_
from datetime import datetime
import asyncio

async def go():
    async with async_session_factory() as session:
        token = 'nwk_lTKxxWOB-1NH3PbN7gN0FgYV2CkD1l6mY5r5g'
        now = datetime.utcnow()
        
        # Try just token match
        r1 = await session.execute(
            select(UserSession).where(UserSession.session_token == token)
        )
        s1 = r1.scalar_one_or_none()
        print(f'By token only: {s1}')
        
        # Try just expires
        r2 = await session.execute(
            select(UserSession).where(UserSession.expires_at > now)
        )
        s2_count = len(r2.scalars().all())
        print(f'By expires only: {s2_count} sessions')
        
        # Try with AND
        r3 = await session.execute(
            select(UserSession).where(
                and_(
                    UserSession.session_token == token + 'x',
                    UserSession.expires_at > now
                )
            )
        )
        s3 = r3.scalar_one_or_none()
        print(f'With wrong token: {s3}')

asyncio.run(go())