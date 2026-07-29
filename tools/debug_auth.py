import sys
sys.path.insert(0, '/app')
from app.services.auth_service import AuthService
import asyncio

async def debug():
    # Try validating the token
    token = 'test'
    # First list all active sessions
    from app.db.database import async_session_factory
    from app.db.auth_models import UserSession
    from sqlalchemy import select
    from datetime import datetime
    
    async with async_session_factory() as session:
        result = await session.execute(select(UserSession))
        all_sessions = result.scalars().all()
        print(f'Total sessions: {len(all_sessions)}')
        for s in all_sessions:
            print(f'  token={s.session_token[:20]}... expires={s.expires_at} user_id={s.user_id}')

asyncio.run(debug())