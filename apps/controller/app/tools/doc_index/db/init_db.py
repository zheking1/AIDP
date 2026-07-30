import logging
from app.tools.doc_index.db.database import engine
from app.tools.doc_index.db.models import Base

logger = logging.getLogger(__name__)


async def init_database():
    await engine.connect()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("doc-index database initialized")
