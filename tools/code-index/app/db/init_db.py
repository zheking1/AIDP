import logging
from app.db.database import engine
from app.db.models import Base
from app.db.migrate_edge_types import migrate_edge_types
from app.db.migrate_add_columns import migrate_add_node_columns

logger = logging.getLogger(__name__)


async def init_database():
    await engine.connect()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await migrate_edge_types()
    await migrate_add_node_columns()
    logger.info("code-index database initialized")
