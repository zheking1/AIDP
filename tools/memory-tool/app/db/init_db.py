import logging

from sqlalchemy import text
from app.db.models import engine, Base

logger = logging.getLogger(__name__)


async def init_database():
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS mem_entry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project VARCHAR(256) NOT NULL,
                user_id INTEGER,
                category VARCHAR(64) NOT NULL,
                title VARCHAR(512) NOT NULL,
                content TEXT NOT NULL,
                tags TEXT,
                pinned BOOLEAN DEFAULT 0,
                memory_tier VARCHAR(20) DEFAULT 'episodic',
                parent_id INTEGER REFERENCES mem_entry(id),
                source_type VARCHAR(50) DEFAULT 'manual',
                source_ref VARCHAR(512),
                access_count INTEGER DEFAULT 0,
                last_accessed_at TIMESTAMP,
                confidence FLOAT DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_mem_entry_project ON mem_entry(project)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_mem_entry_user_id ON mem_entry(user_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_mem_entry_category ON mem_entry(category)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_mem_entry_tier ON mem_entry(memory_tier)"))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS mem_node (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_id INTEGER REFERENCES mem_entry(id),
                label VARCHAR(256),
                memory_type VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS mem_edge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER REFERENCES mem_node(id),
                target_id INTEGER REFERENCES mem_node(id),
                relation VARCHAR(64),
                weight FLOAT DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

    logger.info("memory-tool database initialized")
