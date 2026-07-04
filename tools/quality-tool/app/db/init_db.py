import logging

from sqlalchemy import text
from app.db.models import engine, Base

logger = logging.getLogger(__name__)


async def init_database():
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ql_check_result (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                filename VARCHAR(512),
                language VARCHAR(32),
                check_type VARCHAR(32) NOT NULL,
                issues JSONB,
                issue_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ql_check_result_user_id ON ql_check_result(user_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ql_check_result_check_type ON ql_check_result(check_type)"))

    logger.info("quality-tool database initialized")
