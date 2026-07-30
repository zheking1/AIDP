import logging
from app.tools.code_index.db.database import engine

logger = logging.getLogger(__name__)

NEW_NODE_COLUMNS = [
    ("signature", "TEXT"),
    ("docstring", "TEXT"),
    ("return_type", "VARCHAR(256)"),
    ("params_json", "TEXT"),
    ("file_hash", "VARCHAR(64)"),
]


async def migrate_add_node_columns():
    """向nodes表添加新字段"""
    async with engine.begin() as conn:
        for col_name, col_type in NEW_NODE_COLUMNS:
            try:
                await conn.exec_driver_sql(
                    f"ALTER TABLE nodes ADD COLUMN {col_name} {col_type}"
                )
                logger.info("Added column nodes.%s", col_name)
            except Exception:
                logger.info("Column nodes.%s already exists, skipping", col_name)