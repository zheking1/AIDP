import logging
from datetime import datetime

from sqlalchemy import text
from app.db.database import engine, Base
import bcrypt

logger = logging.getLogger(__name__)


async def init_database():
    """Initialize database with all required tables"""
    async with engine.begin() as conn:
        # ============================================================================
        # Legacy tables (keep for compatibility)
        # ============================================================================
        
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tool_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(256) UNIQUE NOT NULL,
                display_name VARCHAR(256),
                description TEXT,
                version VARCHAR(32),
                endpoint VARCHAR(512) NOT NULL,
                status VARCHAR(32) DEFAULT 'registered',
                last_health_check TIMESTAMP,
                capabilities TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tool_registry_name ON tool_registry(name)"))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tool_invocation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tool_name VARCHAR(256) NOT NULL,
                capability VARCHAR(256),
                arguments TEXT,
                result TEXT,
                status VARCHAR(32),
                duration_ms INTEGER,
                error TEXT,
                user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tool_invocation_tool_name ON tool_invocation(tool_name)"))

        # ============================================================================
        # Phase 1: Unified Authentication & Authorization (NEW)
        # ============================================================================
        
        # Users table - Enhanced version
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR(36) PRIMARY KEY,
                username VARCHAR(64) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE,
                nickname VARCHAR(128),
                avatar_url TEXT,
                role VARCHAR(32) DEFAULT 'user',
                status VARCHAR(32) DEFAULT 'active',
                is_verified BOOLEAN DEFAULT 0,
                last_login_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)"))

        # User Sessions table (supports multiple device login)
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE,
                session_token VARCHAR(255) UNIQUE NOT NULL,
                refresh_token VARCHAR(255),
                ip_address VARCHAR(45),
                user_agent TEXT,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(session_token)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at)"))

        # Login Logs table (security audit)
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS login_logs (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) REFERENCES users(id),
                username VARCHAR(64),
                action VARCHAR(32) NOT NULL,
                ip_address VARCHAR(45),
                user_agent TEXT,
                success BOOLEAN DEFAULT 0,
                fail_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_login_logs_user ON login_logs(user_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_login_logs_action ON login_logs(action)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_login_logs_created ON login_logs(created_at)"))

        # Permissions table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS permissions (
                id VARCHAR(36) PRIMARY KEY,
                code VARCHAR(64) UNIQUE NOT NULL,
                name VARCHAR(128) NOT NULL,
                description TEXT,
                resource_type VARCHAR(32),
                action VARCHAR(32),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_permissions_code ON permissions(code)"))

        # Role Permissions mapping
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS role_permissions (
                role VARCHAR(32) NOT NULL,
                permission_id VARCHAR(36) REFERENCES permissions(id) ON DELETE CASCADE,
                PRIMARY KEY (role, permission_id)
            )
        """))

        # API Keys table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE,
                label VARCHAR(128),
                key_hash VARCHAR(255) UNIQUE NOT NULL,
                key_preview VARCHAR(20),
                scopes TEXT DEFAULT '["read"]',
                rate_limit_req_per_min INTEGER DEFAULT 60,
                expires_at TIMESTAMP,
                last_used_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id)"))

        # Audit Logs table (enhanced)
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) REFERENCES users(id),
                action VARCHAR(64) NOT NULL,
                resource_type VARCHAR(64),
                resource_id VARCHAR(64),
                resource_name VARCHAR(255),
                old_values TEXT,
                new_values TEXT,
                ip_address VARCHAR(45),
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource_type, resource_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at)"))

        # System Settings table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS system_settings (
                id VARCHAR(36) PRIMARY KEY,
                key VARCHAR(128) UNIQUE NOT NULL,
                value TEXT,
                description TEXT,
                is_encrypted BOOLEAN DEFAULT 0,
                updated_by VARCHAR(36) REFERENCES users(id),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_settings_key ON system_settings(key)"))

        # ============================================================================
        # Default Data
        # ============================================================================
        
        # Create default permissions
        default_permissions = [
            # Tool permissions
            ("tool:read", "View Tools", "View tool list and details", "tool", "read"),
            ("tool:write", "Manage Tools", "Register, update, delete tools", "tool", "write"),
            ("tool:execute", "Execute Tools", "Invoke tool capabilities", "tool", "execute"),
            # User permissions
            ("user:read", "View Users", "View user list", "user", "read"),
            ("user:write", "Manage Users", "Create, update, delete users", "user", "write"),
            # Model permissions
            ("model:read", "View Models", "View LLM models", "model", "read"),
            ("model:write", "Manage Models", "Create, update, delete models", "model", "write"),
            # Settings permissions
            ("settings:read", "View Settings", "View system settings", "settings", "read"),
            ("settings:write", "Manage Settings", "Modify system settings", "settings", "write"),
            # Admin permissions
            ("admin:full", "Full Admin", "Full system access", "admin", "all"),
        ]
        
        import uuid
        for code, name, desc, resource, action in default_permissions:
            perm_id = str(uuid.uuid4())
            await conn.execute(text("""
                INSERT OR IGNORE INTO permissions (id, code, name, description, resource_type, action)
                VALUES (:id, :code, :name, :desc, :resource, :action)
            """), {
                "id": perm_id, "code": code, "name": name, "desc": desc, 
                "resource": resource, "action": action
            })

        # Assign permissions to roles
        role_perms = {
            "super_admin": ["admin:full"],
            "admin": ["tool:read", "tool:write", "tool:execute", "user:read", "user:write", 
                      "model:read", "model:write", "settings:read", "settings:write"],
            "developer": ["tool:read", "tool:write", "tool:execute", "model:read", "user:read"],
            "user": ["tool:read", "tool:execute", "model:read", "user:read"],
            "readonly": ["tool:read", "model:read"],
        }
        
        for role, perms in role_perms.items():
            for perm_code in perms:
                await conn.execute(text("""
                    INSERT OR IGNORE INTO role_permissions (role, permission_id)
                    SELECT :role, id FROM permissions WHERE code = :perm_code
                """), {"role": role, "perm_code": perm_code})

        # Create default admin user (if not exists)
        password = "admin123"
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        
        admin_id = str(uuid.uuid4())
        await conn.execute(text("""
            INSERT OR IGNORE INTO users (id, username, password_hash, email, nickname, role, status, is_verified)
            VALUES (:id, 'admin', :password_hash, 'admin@aidp.local', 'Administrator', 'super_admin', 'active', 1)
        """), {"id": admin_id, "password_hash": password_hash})

        # Create default system settings
        default_settings = [
            ("site.name", "AIDP", "Platform name", False),
            ("site.description", "AI DevOps Platform", "Platform description", False),
            ("auth.allow_registration", False, "Allow new user registration", False),
            ("auth.session_timeout", 3600, "Session timeout in seconds", False),
            ("auth.max_login_attempts", 5, "Max failed login attempts before lockout", False),
            ("auth.lockout_duration", 900, "Account lockout duration in seconds", False),
        ]
        
        for key, value, desc, encrypted in default_settings:
            val = str(value).lower() if isinstance(value, bool) else str(value)
            setting_id = str(uuid.uuid4())
            await conn.execute(text("""
                INSERT OR IGNORE INTO system_settings (id, key, value, description, is_encrypted)
                VALUES (:id, :key, :value, :desc, :encrypted)
            """), {"id": setting_id, "key": key, "value": f'"{val}"', "desc": desc, "encrypted": encrypted})

        logger.info("Database initialized successfully with Phase 1: Unified Authentication")

        # ============================================================================
        # Legacy tables (keep for compatibility)
        # ============================================================================
        
        # App Projects table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS app_projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(256) NOT NULL,
                description VARCHAR(1024),
                project_type VARCHAR(256),
                owner_id VARCHAR(128),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # App Project members table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS app_project_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER REFERENCES app_projects(id),
                user_id VARCHAR(128),
                role VARCHAR(32) DEFAULT 'member',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(project_id, user_id)
            )
        """))

        # App Project configs table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS app_project_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER REFERENCES app_projects(id),
                env_type VARCHAR(32) NOT NULL,
                config_key VARCHAR(256) NOT NULL,
                config_value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(project_id, env_type, config_key)
            )
        """))

        # Review queue table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS review_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER,
                user_id VARCHAR(36),
                action VARCHAR(64) NOT NULL,
                content TEXT,
                status VARCHAR(32) DEFAULT 'pending',
                review_comment TEXT,
                reviewed_by VARCHAR(36),
                reviewed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # Agent Instructions table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS agent_instructions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER DEFAULT 0,
                agent_type VARCHAR(100) NOT NULL DEFAULT 'main',
                role TEXT,
                constraints TEXT,
                rules TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
