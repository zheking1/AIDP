import logging

from sqlalchemy import text
from app.db.database import engine, Base

logger = logging.getLogger(__name__)


async def init_database():
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tool_registry (
                id SERIAL PRIMARY KEY,
                name VARCHAR(256) UNIQUE NOT NULL,
                display_name VARCHAR(256),
                description TEXT,
                version VARCHAR(32),
                endpoint VARCHAR(512) NOT NULL,
                status VARCHAR(32) DEFAULT 'registered',
                last_health_check TIMESTAMP,
                capabilities JSONB,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tool_registry_name ON tool_registry(name)"))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tool_invocation (
                id SERIAL PRIMARY KEY,
                tool_name VARCHAR(256) NOT NULL,
                capability VARCHAR(256),
                arguments JSONB,
                result JSONB,
                status VARCHAR(32),
                duration_ms INTEGER,
                error TEXT,
                user_id INTEGER,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tool_invocation_tool_name ON tool_invocation(tool_name)"))

        # Phase 1: Data ownership and permissions

        # Users table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(128) UNIQUE NOT NULL,
                password_hash VARCHAR(256) NOT NULL,
                role VARCHAR(32) DEFAULT 'user',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)"))

        # App Projects table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS app_projects (
                id SERIAL PRIMARY KEY,
                name VARCHAR(256) NOT NULL,
                description TEXT,
                project_type VARCHAR(64),
                owner_id VARCHAR(128),
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))

        # App Project members table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS app_project_members (
                id SERIAL PRIMARY KEY,
                project_id INTEGER REFERENCES app_projects(id),
                user_id VARCHAR(128),
                role VARCHAR(32) DEFAULT 'member',
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(project_id, user_id)
            )
        """))

        # App Project configs table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS app_project_configs (
                id SERIAL PRIMARY KEY,
                project_id INTEGER REFERENCES app_projects(id),
                env_type VARCHAR(32) NOT NULL,
                config_key VARCHAR(256) NOT NULL,
                config_value TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(project_id, env_type, config_key)
            )
        """))

        # Review queue table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS review_queue (
                id SERIAL PRIMARY KEY,
                document_id INTEGER,
                user_id INTEGER REFERENCES users(id),
                action VARCHAR(64) NOT NULL,
                content TEXT,
                status VARCHAR(32) DEFAULT 'pending',
                review_comment TEXT,
                reviewed_by INTEGER REFERENCES users(id),
                reviewed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))

        # Create default admin user
        await conn.execute(text("""
            INSERT INTO users (username, password_hash, role)
            SELECT 'admin', 'admin123_hash', 'admin'
            WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'admin')
        """))

        # Audit logs table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(128),
                action VARCHAR(256),
                resource_id VARCHAR(128),
                details TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))

        logger.info("controller database initialized")

        # Agent Instructions table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS agent_instructions (
                id SERIAL PRIMARY KEY,
                project_id INTEGER DEFAULT 0,
                agent_type VARCHAR(100) NOT NULL DEFAULT 'main',
                role TEXT,
                constraints JSONB,
                rules JSONB,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_agent_instructions_type ON agent_instructions(project_id, agent_type)"))

        result = await conn.execute(text("SELECT 1 FROM agent_instructions WHERE agent_type = 'main'"))
        if not result.first():
            await conn.execute(text("""
                INSERT INTO agent_instructions (project_id, agent_type, role, constraints, rules)
                VALUES (0, 'main', 'You are a full-stack developer working on the AIDP project.',
                    '{"preferred_tools": ["quality-tool", "sandbox-tool"], "max_files_per_change": 5}',
                    '[]')
            """))
