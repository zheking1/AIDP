import logging

from sqlalchemy import text
from app.db.models import engine, Base

logger = logging.getLogger(__name__)


async def init_database():
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sb_execution (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                language VARCHAR(32) NOT NULL,
                code TEXT NOT NULL,
                stdin TEXT,
                stdout TEXT,
                stderr TEXT,
                exit_code INTEGER,
                timed_out BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW(),
                duration_ms INTEGER
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sb_execution_user_id ON sb_execution(user_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sb_execution_language ON sb_execution(language)"))

    logger.info("sandbox-tool database initialized")
