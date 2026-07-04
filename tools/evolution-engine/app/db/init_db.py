import logging
from app.db.database import engine
from app.db.models import Base

logger = logging.getLogger(__name__)


async def init_database():
    await engine.connect()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("evolution-engine database initialized")
