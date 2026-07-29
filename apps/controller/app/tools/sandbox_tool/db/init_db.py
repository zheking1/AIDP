import logging

from sqlalchemy.ext.asyncio import AsyncSession
from app.tools.sandbox_tool.db.models import engine, Base

logger = logging.getLogger(__name__)


async def init_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("sandbox-tool database initialized")
