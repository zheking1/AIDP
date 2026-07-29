import asyncio
from sqlalchemy import text
from app.db.database import engine

async def go():
    async with engine.begin() as conn:
        await conn.execute(text("ALTER TABLE aidp_projects ADD COLUMN IF NOT EXISTS tech_stack TEXT"))
        print("Column tech_stack added successfully")

asyncio.run(go())