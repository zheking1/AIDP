from sqlalchemy import text

from app.tools.importer_tool.db.models import engine


async def init_database():
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS it_import_session (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(100) NOT NULL,
                project_id INTEGER,
                scope VARCHAR(20) DEFAULT 'personal',
                source_type VARCHAR(20) NOT NULL,
                source_uri TEXT,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                total_items INTEGER DEFAULT 0,
                completed_items INTEGER DEFAULT 0,
                failed_items INTEGER DEFAULT 0,
                skipped_items INTEGER DEFAULT 0,
                metadata TEXT DEFAULT '{}',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                completed_at TIMESTAMPTZ
            )
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_it_session_user
            ON it_import_session (user_id, created_at DESC)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_it_session_status
            ON it_import_session (status)
        """))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS it_import_item (
                id VARCHAR(36) PRIMARY KEY,
                session_id VARCHAR(36) NOT NULL REFERENCES it_import_session(id),
                item_index INTEGER NOT NULL,
                filename VARCHAR(500),
                content TEXT,
                content_hash VARCHAR(64),
                classified_type VARCHAR(20),
                classified_confidence VARCHAR(10),
                suggested_title VARCHAR(500),
                suggested_tags TEXT DEFAULT '[]',
                suggested_category VARCHAR(200),
                suggested_severity VARCHAR(20),
                quality_passed INTEGER,
                quality_issues TEXT DEFAULT '[]',
                confirmed_type VARCHAR(20),
                confirmed_tags TEXT DEFAULT '[]',
                confirmed_category VARCHAR(200),
                confirmed_severity VARCHAR(20),
                persist_type VARCHAR(20),
                persist_id VARCHAR(36),
                persist_url TEXT,
                persist_version INTEGER,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                error_message TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                persisted_at TIMESTAMPTZ
            )
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_it_item_session
            ON it_import_item (session_id, item_index)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_it_item_status
            ON it_import_item (status)
        """))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS it_promotion_review_config (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(100) NOT NULL,
                provider VARCHAR(50) DEFAULT 'openai',
                api_base VARCHAR(500) DEFAULT 'https://api.openai.com/v1',
                model_name VARCHAR(128) DEFAULT 'gpt-4o',
                api_key TEXT,
                max_tokens INTEGER DEFAULT 4096,
                temperature FLOAT DEFAULT 0.3,
                redact_regexes TEXT DEFAULT '[]',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_it_promotion_config_user
            ON it_promotion_review_config (user_id)
        """))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS it_promotion_log (
                id VARCHAR(36) PRIMARY KEY,
                entity_type VARCHAR(20) NOT NULL,
                entity_id VARCHAR(36) NOT NULL,
                action VARCHAR(20) NOT NULL,
                from_scope VARCHAR(20),
                to_scope VARCHAR(20),
                review_report TEXT,
                triggered_by VARCHAR(100),
                metadata TEXT DEFAULT '{}',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_it_promotion_log_entity
            ON it_promotion_log (entity_type, entity_id, created_at DESC)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_it_promotion_log_action
            ON it_promotion_log (action)
        """))
