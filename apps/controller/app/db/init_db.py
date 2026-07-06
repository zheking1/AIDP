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

        # ============================================================================
        # Phase 1: Unified Authentication & Authorization (NEW)
        # ============================================================================
        
        # Users table - Enhanced version
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                username VARCHAR(64) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE,
                nickname VARCHAR(128),
                avatar_url TEXT,
                role VARCHAR(32) DEFAULT 'user',
                status VARCHAR(32) DEFAULT 'active',
                is_verified BOOLEAN DEFAULT FALSE,
                last_login_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)"))

        # User Sessions table (supports multiple device login)
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                session_token VARCHAR(255) UNIQUE NOT NULL,
                refresh_token VARCHAR(255),
                ip_address VARCHAR(45),
                user_agent TEXT,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                last_activity_at TIMESTAMP DEFAULT NOW()
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(session_token)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at)"))

        # Login Logs table (security audit)
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS login_logs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES users(id),
                username VARCHAR(64),
                action VARCHAR(32) NOT NULL,
                ip_address VARCHAR(45),
                user_agent TEXT,
                success BOOLEAN DEFAULT FALSE,
                fail_reason TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_login_logs_user ON login_logs(user_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_login_logs_action ON login_logs(action)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_login_logs_created ON login_logs(created_at)"))

        # Permissions table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS permissions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                code VARCHAR(64) UNIQUE NOT NULL,
                name VARCHAR(128) NOT NULL,
                description TEXT,
                resource_type VARCHAR(32),
                action VARCHAR(32),
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_permissions_code ON permissions(code)"))

        # Role Permissions mapping
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS role_permissions (
                role VARCHAR(32) NOT NULL,
                permission_id UUID REFERENCES permissions(id) ON DELETE CASCADE,
                PRIMARY KEY (role, permission_id)
            )
        """))

        # API Keys table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                label VARCHAR(128),
                key_hash VARCHAR(255) UNIQUE NOT NULL,
                key_preview VARCHAR(20),
                scopes JSONB DEFAULT '["read"]',
                rate_limit_req_per_min INTEGER DEFAULT 60,
                expires_at TIMESTAMP,
                last_used_at TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id)"))

        # Audit Logs table (enhanced)
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES users(id),
                action VARCHAR(64) NOT NULL,
                resource_type VARCHAR(64),
                resource_id VARCHAR(64),
                resource_name VARCHAR(255),
                old_values JSONB,
                new_values JSONB,
                ip_address VARCHAR(45),
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource_type, resource_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at)"))

        # System Settings table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS system_settings (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                key VARCHAR(128) UNIQUE NOT NULL,
                value JSONB,
                description TEXT,
                is_encrypted BOOLEAN DEFAULT FALSE,
                updated_by UUID REFERENCES users(id),
                updated_at TIMESTAMP DEFAULT NOW()
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
        
        for code, name, desc, resource, action in default_permissions:
            await conn.execute(text("""
                INSERT INTO permissions (code, name, description, resource_type, action)
                VALUES (:code, :name, :desc, :resource, :action)
                ON CONFLICT (code) DO NOTHING
            """), {
                "code": code, "name": name, "desc": desc, 
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
                    INSERT INTO role_permissions (role, permission_id)
                    SELECT :role, id FROM permissions WHERE code = :perm_code
                    ON CONFLICT (role, permission_id) DO NOTHING
                """), {"role": role, "perm_code": perm_code})

        # Create default admin user (if not exists)
        # Generate proper bcrypt hash for 'admin123'
        password = "admin123"
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        
        await conn.execute(text("""
            INSERT INTO users (username, password_hash, email, nickname, role, status, is_verified)
            SELECT 'admin', :password_hash, 'admin@aidp.local', 'Administrator', 'super_admin', 'active', TRUE
            WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'admin')
        """), {"password_hash": password_hash})

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
            await conn.execute(text("""
                INSERT INTO system_settings (key, value, description, is_encrypted)
                VALUES (:key, CAST(:value AS JSONB), :desc, :encrypted)
                ON CONFLICT (key) DO NOTHING
            """), {"key": key, "value": f'"{val}"', "desc": desc, "encrypted": encrypted})

        logger.info("Database initialized successfully with Phase 1: Unified Authentication")

        # ============================================================================
        # Legacy tables (keep for compatibility)
        # ============================================================================
        
        # App Projects table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS app_projects (
                id SERIAL PRIMARY KEY,
                name VARCHAR(256) NOT NULL,
                description VARCHAR(1024),
                project_type VARCHAR(256),
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
                user_id UUID,
                action VARCHAR(64) NOT NULL,
                content TEXT,
                status VARCHAR(32) DEFAULT 'pending',
                review_comment TEXT,
                reviewed_by UUID,
                reviewed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))

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
