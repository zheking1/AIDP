import logging

from sqlalchemy import text
from app.db.database import engine

logger = logging.getLogger(__name__)

CREATE_TABLES_SQLITE = """
CREATE TABLE IF NOT EXISTS at_asset (
    id VARCHAR(36) PRIMARY KEY,
    workspace_id VARCHAR(128) NOT NULL,
    project_id VARCHAR(128),
    name VARCHAR(512) NOT NULL,
    title VARCHAR(512) NOT NULL,
    asset_type VARCHAR(32) NOT NULL,
    language VARCHAR(64),
    format VARCHAR(64),
    visibility VARCHAR(32) NOT NULL DEFAULT 'private',
    content TEXT NOT NULL,
    description TEXT,
    variables TEXT NOT NULL DEFAULT '{}',
    metadata TEXT NOT NULL DEFAULT '{}',
    tags TEXT NOT NULL DEFAULT '[]',
    created_by VARCHAR(128),
    updated_by VARCHAR(128),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS at_asset_tag (
    id VARCHAR(36) PRIMARY KEY,
    asset_id VARCHAR(36) NOT NULL REFERENCES at_asset(id),
    tag VARCHAR(128) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (asset_id, tag)
);

CREATE INDEX IF NOT EXISTS idx_at_asset_scope ON at_asset (workspace_id, project_id, visibility) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_at_asset_type ON at_asset (asset_type) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_at_asset_language ON at_asset (language) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_at_asset_tag_asset ON at_asset_tag (asset_id);
CREATE INDEX IF NOT EXISTS idx_at_asset_tag_tag ON at_asset_tag (tag);
"""


async def init_database():
    """Initialize database tables."""
    logger.info("Initializing asset-tool database...")

    async with engine.begin() as conn:
        for statement in CREATE_TABLES_SQLITE.split(";"):
            statement = statement.strip()
            if statement:
                await conn.execute(text(statement))

    logger.info("Asset-tool database initialized successfully")
