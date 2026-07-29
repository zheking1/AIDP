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
        print(f'Now: {now}')
        
        # Step 1: Find session
        result = await session.execute(
            select(UserSession).where(
                and_(
                    UserSession.session_token == token,
                    UserSession.expires_at > now
                )
            )
        )
        user_session = result.scalar_one_or_none()
        print(f'Session found: {user_session}')
        if user_session:
            print(f'  user_id={user_session.user_id} type={type(user_session.user_id)}')
            print(f'  expires_at={user_session.expires_at} > now={now} = {user_session.expires_at > now}')
            
            # Step 2: Find user
            result2 = await session.execute(
                select(User).where(User.id == user_session.user_id)
            )
            user = result2.scalar_one_or_none()
            print(f'User found: {user}')
            if user:
                print(f'  id={user.id} type={type(user.id)}')
            else:
                # Try with string comparison
                print(f'  Looking for User.id = {str(user_session.user_id)}')
                result3 = await session.execute(
                    select(User).where(User.id == str(user_session.user_id))
                )
                user3 = result3.scalar_one_or_none()
                print(f'  With str: {user3}')

asyncio.run(go())