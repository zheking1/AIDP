import sys; sys.path.insert(0, '/app')
from app.db.database import async_session_factory
from app.db.auth_models import User, UserSession
from sqlalchemy import select, and_
from datetime import datetime, timezone
import asyncio

async def go():
    async with async_session_factory() as session:
        token = 'nwk_lTKxxWOB-1NH3PbN7gN0FgYV2CkD1l6mY5r5g'
        now_naive = datetime.utcnow()
        now_aware = datetime.now(timezone.utc)
        
        # Get all sessions with their expires_at
        all_s = await session.execute(select(UserSession))
        for s in all_s.scalars():
            e = s.expires_at
            print(f'token={s.session_token[:15]}... expires={e} tzinfo={e.tzinfo} naive_gt={e > now_naive} aware_gt={e > now_aware if hasattr(e, "tzinfo") and e.tzinfo else "N/A"}')

asyncio.run(go())