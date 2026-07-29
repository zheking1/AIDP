import sys; sys.path.insert(0, '/app')
from app.db.database import async_session_factory
from app.db.auth_models import User, UserSession
from sqlalchemy import select
import asyncio

async def go():
    async with async_session_factory() as session:
        users = await session.execute(select(User))
        for u in users.scalars():
            print(f'User: id={u.id} username={u.username} role={u.role}')
        
        # Try validate
        from app.services.auth_service import AuthService
        token = 'nwk_lTKxxWOB-1NH3PbN7gN0FgYV2CkD1l6mY5r5g'
        user = await AuthService.validate_session(token)
        print(f'Validate result: {user}')

asyncio.run(go())