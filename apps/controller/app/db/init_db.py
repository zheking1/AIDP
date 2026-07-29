import logging
import uuid
from datetime import datetime

from sqlalchemy import text
from sqlalchemy import exc as sa_exc
from app.db.database import engine
import bcrypt
import json

logger = logging.getLogger(__name__)


def generate_uuid():
    """Generate a UUID string"""
    return str(uuid.uuid4())


async def init_database():
    """Initialize database with default data only.
    
    Note: Tables are created by SQLAlchemy models. This function only inserts default data.
    """
    logger.info("Database initialization started...")
    
    # Migration: make base_id nullable in aidp_knowledge_documents
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("PRAGMA table_info(aidp_knowledge_documents)"))
            cols = result.fetchall()
            base_id_col = [c for c in cols if c[1] == 'base_id']
            if base_id_col and base_id_col[0][3]:  # notnull = True
                logger.info("Migrating aidp_knowledge_documents: base_id NOT NULL -> NULL")
                await conn.execute(text("""
                    CREATE TABLE aidp_knowledge_documents_new (
                        id VARCHAR(36) PRIMARY KEY,
                        base_id VARCHAR(36),
                        project_id INTEGER,
                        user_id VARCHAR(100),
                        title VARCHAR(500) NOT NULL,
                        source_type VARCHAR(50),
                        source_uri VARCHAR(1000),
                        content TEXT,
                        mime_type VARCHAR(100),
                        file_size INTEGER,
                        chunk_count INTEGER,
                        category VARCHAR(100),
                        tags TEXT,
                        checksum VARCHAR(128),
                        version VARCHAR(128),
                        index_status VARCHAR(20),
                        summary TEXT,
                        visibility VARCHAR(20),
                        owner_type VARCHAR(32),
                        created_by VARCHAR(100),
                        updated_by VARCHAR(100),
                        processing_status VARCHAR(20),
                        extra_data TEXT,
                        created_at DATETIME,
                        updated_at DATETIME,
                        deleted_at DATETIME
                    )
                """))
                await conn.execute(text("""
                    INSERT INTO aidp_knowledge_documents_new 
                    SELECT * FROM aidp_knowledge_documents
                """))
                await conn.execute(text("DROP TABLE aidp_knowledge_documents"))
                await conn.execute(text("ALTER TABLE aidp_knowledge_documents_new RENAME TO aidp_knowledge_documents"))
                await conn.execute(text("CREATE INDEX ix_aidp_knowledge_documents_base_id ON aidp_knowledge_documents(base_id)"))
                await conn.execute(text("CREATE INDEX ix_aidp_knowledge_documents_project_id ON aidp_knowledge_documents(project_id)"))
                await conn.execute(text("CREATE INDEX ix_aidp_knowledge_documents_user_id ON aidp_knowledge_documents(user_id)"))
                await conn.execute(text("CREATE INDEX ix_aidp_knowledge_documents_category ON aidp_knowledge_documents(category)"))
                await conn.execute(text("CREATE INDEX ix_aidp_knowledge_documents_index_status ON aidp_knowledge_documents(index_status)"))
                await conn.execute(text("CREATE INDEX ix_aidp_knowledge_documents_processing_status ON aidp_knowledge_documents(processing_status)"))
                await conn.execute(text("CREATE INDEX ix_aidp_knowledge_documents_created_at ON aidp_knowledge_documents(created_at)"))
                logger.info("Migration complete")
    except sa_exc.SQLAlchemyError as e:
        logger.warning(f"Migration skipped: {e}")
    
    async with engine.begin() as conn:
        
        # Create default permissions
        default_permissions = [
            ("tool:read", "View Tools", "View tool list and details", "tool", "read"),
            ("tool:write", "Manage Tools", "Register, update, delete tools", "tool", "write"),
            ("tool:execute", "Execute Tools", "Invoke tool capabilities", "tool", "execute"),
            ("user:read", "View Users", "View user list", "user", "read"),
            ("user:write", "Manage Users", "Create, update, delete users", "user", "write"),
            ("model:read", "View Models", "View LLM models", "model", "read"),
            ("model:write", "Manage Models", "Create, update, delete models", "model", "write"),
            ("settings:read", "View Settings", "View system settings", "settings", "read"),
            ("settings:write", "Manage Settings", "Modify system settings", "settings", "write"),
            ("admin:full", "Full Admin", "Full system access", "admin", "all"),
        ]
        
        async with conn.begin_nested():
            for code, name, desc, resource, action in default_permissions:
                perm_id = generate_uuid()
                try:
                    await conn.execute(text("""
                        INSERT INTO permissions (id, code, name, description, resource_type, action)
                        VALUES (:id, :code, :name, :desc, :resource, :action)
                        ON CONFLICT (code) DO NOTHING
                    """), {
                        "id": perm_id, "code": code, "name": name, "desc": desc, 
                        "resource": resource, "action": action
                    })
                except sa_exc.SQLAlchemyError as e:
                    logger.warning(f"Permission {code} may already exist: {e}")

        # Assign permissions to roles
        role_perms = {
            "super_admin": ["admin:full"],
            "admin": ["tool:read", "tool:write", "tool:execute", "user:read", "user:write", 
                      "model:read", "model:write", "settings:read", "settings:write"],
            "developer": ["tool:read", "tool:write", "tool:execute", "model:read", "user:read"],
            "user": ["tool:read", "tool:execute", "model:read", "user:read"],
            "readonly": ["tool:read", "model:read"],
        }
        async with conn.begin_nested():
            for role, perms in role_perms.items():
                for perm_code in perms:
                    try:
                        result = await conn.execute(text("SELECT id FROM permissions WHERE code = :code"), {"code": perm_code})
                        row = result.fetchone()
                        if row:
                            perm_id = row[0]
                            await conn.execute(text("""
                                INSERT INTO role_permissions (role, permission_id)
                                VALUES (:role, :perm_id)
                                ON CONFLICT DO NOTHING
                            """), {"role": role, "perm_id": perm_id})
                    except sa_exc.SQLAlchemyError as e:
                        logger.warning(f"Role permission {role}/{perm_code} may already exist: {e}")

        # Create default admin user
        async with conn.begin_nested():
            try:
                result = await conn.execute(text("SELECT 1 FROM users WHERE username = 'admin'"))
                if not result.first():
                    password = "admin123"
                    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
                    
                    admin_id = generate_uuid()
                    await conn.execute(text("""
                        INSERT INTO users (id, username, password_hash, email, nickname, role, status, is_verified)
                        VALUES (:id, 'admin', :password_hash, 'admin@aidp.local', 'Administrator', 'super_admin', 'active', true)
                        ON CONFLICT (username) DO NOTHING
                    """), {"id": admin_id, "password_hash": password_hash})
                    logger.info("Default admin user created")
            except sa_exc.SQLAlchemyError as e:
                logger.warning(f"Admin user may already exist: {e}")

        # Create default system settings
        default_settings = [
            ("site.name", "AIDP", "Platform name", False),
            ("site.description", "AI DevOps Platform", "Platform description", False),
            ("auth.allow_registration", "false", "Allow new user registration", False),
            ("auth.session_timeout", "3600", "Session timeout in seconds", False),
            ("auth.max_login_attempts", "5", "Max failed login attempts before lockout", False),
            ("auth.lockout_duration", "900", "Account lockout duration in seconds", False),
        ]
        async with conn.begin_nested():
            for key, value, desc, encrypted in default_settings:
                try:
                    setting_id = generate_uuid()
                    await conn.execute(text("""
                        INSERT INTO system_settings (id, key, value, description, is_encrypted)
                        VALUES (:id, :key, :value, :desc, :encrypted)
                        ON CONFLICT (key) DO NOTHING
                    """), {"id": setting_id, "key": key, "value": json.dumps(value), "desc": desc, "encrypted": encrypted})
                except sa_exc.SQLAlchemyError as e:
                    logger.warning(f"Setting {key} may already exist: {e}")

        await _seed_default_models(conn)

        logger.info("Database initialized successfully")


async def _seed_default_models(conn):
    """初始化默认模型配置"""
    try:
        result = await conn.execute(text("SELECT 1 FROM aidp_models LIMIT 1"))
        if result.first():
            return
    except Exception:
        pass
    defaults = [
        ("DeepSeek Chat", "DeepSeek", "deepseek-chat", "https://api.deepseek.com/v1", '["chat"]', 10),
        ("DeepSeek Coder", "DeepSeek", "deepseek-coder", "https://api.deepseek.com/v1", '["chat"]', 5),
        ("text-embedding-3-small", "OpenAI", "text-embedding-3-small", "https://api.openai.com/v1", '["embedding"]', 10),
        ("all-MiniLM-L6-v2", "Local", "all-MiniLM-L6-v2", "none", '["embedding"]', 5),
    ]
    async with conn.begin_nested():
        for name, prov, mname, api_base, tasks, prio in defaults:
            await conn.execute(text("""
                INSERT INTO aidp_models (name, provider, model_name, api_base, task_types, status, priority)
                VALUES (:name, :prov, :mname, :api_base, :tasks, 'active', :prio)
            """), {"name": name, "prov": prov, "mname": mname, "api_base": api_base, "tasks": tasks, "prio": prio})
    logger.info("Seeded %d default models", len(defaults))