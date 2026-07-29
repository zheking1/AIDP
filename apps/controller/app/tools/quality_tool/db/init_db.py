import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.tools.quality_tool.db.database import engine, Base

logger = logging.getLogger(__name__)


async def init_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("quality-tool database initialized")
