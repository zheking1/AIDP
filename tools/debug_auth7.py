import sys; sys.path.insert(0, "/app")
from app.db.database import async_session_factory
from app.db.auth_models import User, UserSession
from sqlalchemy import select
import asyncio

async def go():
    async with async_session_factory() as s:
        token = "nwk_lTKxxWOB-1NH3PbNGxWWZuV5BTCokc926KCnFds"
        r = await s.execute(select(UserSession).where(UserSession.session_token == token))
        sess = r.scalar_one_or_none()
        print("Session:", sess)
        if sess:
            print(f"  user_id={sess.user_id} type={type(sess.user_id)}")
            r2 = await s.execute(select(User).where(User.id == sess.user_id))
            user = r2.scalar_one_or_none()
            print("User by UUID:", user)
            # Try with string
            r3 = await s.execute(select(User).where(User.id == str(sess.user_id)))
            user2 = r3.scalar_one_or_none()
            print("User by str:", user2)
            # Dump all users
            r4 = await s.execute(select(User))
            for u in r4.scalars():
                print(f"  DB User id={u.id} type={type(u.id)} username={u.username}")

asyncio.run(go())