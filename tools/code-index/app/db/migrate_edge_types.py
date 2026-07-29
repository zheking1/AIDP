import logging
from app.db.database import engine

logger = logging.getLogger(__name__)


async def migrate_edge_types():
    """将edges表中所有edge_type统一为小写"""
    async with engine.begin() as conn:
        result = await conn.exec_driver_sql(
            "UPDATE edges SET edge_type = LOWER(edge_type) WHERE edge_type != LOWER(edge_type)"
        )
        logger.info("edge_type migration completed, rows affected: %s", result.rowcount)