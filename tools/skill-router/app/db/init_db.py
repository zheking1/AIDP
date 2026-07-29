import hashlib
import uuid
from contextlib import asynccontextmanager

import bcrypt
from sqlalchemy import text

from app.config import settings
from app.db.database import engine, async_session_factory
from app.db.models import Base, User, ApiKey, Project


@asynccontextmanager
async def get_session():
    async with async_session_factory() as session:
        yield session


async def init_database():
    async with engine.begin() as conn:
        # drop stale projects table if schema doesn't match (safe - no important data yet)
        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_name='projects' AND column_name='name'"
        ))
        if not result.fetchone():
            await conn.execute(text("DROP TABLE IF EXISTS projects CASCADE"))

        await conn.run_sync(Base.metadata.create_all)

        # legacy: ensure exec_config column exists
        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_name='skills' AND column_name='exec_config'"
        ))
        if not result.fetchone():
            await conn.execute(text("ALTER TABLE skills ADD COLUMN exec_config JSONB DEFAULT NULL"))

        # ensure projects.user_id column exists (table may be stale from previous model)
        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_name='projects' AND column_name='user_id'"
        ))
        if not result.fetchone():
            await conn.execute(text("ALTER TABLE projects ADD COLUMN user_id UUID"))

        # ensure project_id columns exist on skills/rules/llm_configs
        for tbl in ("skills", "rules", "llm_configs"):
            result = await conn.execute(text(
                f"SELECT column_name FROM information_schema.columns WHERE table_name='{tbl}' AND column_name='project_id'"
            ))
            if not result.fetchone():
                await conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN project_id UUID"))

        # ensure instruction column on skills, rules, projects
        for tbl in ("skills", "rules", "projects"):
            result = await conn.execute(text(
                f"SELECT column_name FROM information_schema.columns WHERE table_name='{tbl}' AND column_name='instruction'"
            ))
            if not result.fetchone():
                await conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN instruction TEXT DEFAULT NULL"))

        # ensure allowed_roles + scope + sensitive + weight_config on skills/rules
        for tbl in ("skills", "rules"):
            for col, coltype in [
                ("allowed_roles", "VARCHAR[] DEFAULT NULL"),
                ("scope", "VARCHAR(20) DEFAULT 'private'"),
                ("sensitive", "BOOLEAN DEFAULT FALSE"),
                ("weight_config", "JSONB DEFAULT NULL"),
            ]:
                result = await conn.execute(text(
                    f"SELECT column_name FROM information_schema.columns WHERE table_name='{tbl}' AND column_name='{col}'"
                ))
                if not result.fetchone():
                    await conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN {col} {coltype}"))

        # ensure examples column on skills for better embedding matching
        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_name='skills' AND column_name='examples'"
        ))
        if not result.fetchone():
            await conn.execute(text("ALTER TABLE skills ADD COLUMN examples TEXT[] DEFAULT '{}'::text[]"))

        # ensure group_id on skills
        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_name='skills' AND column_name='group_id'"
        ))
        if not result.fetchone():
            await conn.execute(text("ALTER TABLE skills ADD COLUMN group_id UUID"))
            await conn.execute(text("CREATE INDEX idx_skills_group_id ON skills(group_id)"))

        # create skill_groups table if not exists
        result = await conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='skill_groups')"
        ))
        if not result.scalar():
            await conn.execute(text("""
                CREATE TABLE skill_groups (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    name VARCHAR(255) NOT NULL,
                    parent_id UUID REFERENCES skill_groups(id),
                    user_id UUID NOT NULL REFERENCES users(id),
                    sort_order INTEGER DEFAULT 0,
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
                )
            """))
            await conn.execute(text("CREATE INDEX idx_skill_groups_user_id ON skill_groups(user_id)"))
            await conn.execute(text("CREATE INDEX idx_skill_groups_parent_id ON skill_groups(parent_id)"))
        else:
            # ensure columns exist
            for col, coltype in [
                ("updated_at", "TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()"),
            ]:
                result = await conn.execute(text(
                    f"SELECT column_name FROM information_schema.columns WHERE table_name='skill_groups' AND column_name='{col}'"
                ))
                if not result.fetchone():
                    await conn.execute(text(f"ALTER TABLE skill_groups ADD COLUMN {col} {coltype}"))

        # ensure group_id on rules
        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_name='rules' AND column_name='group_id'"
        ))
        if not result.fetchone():
            await conn.execute(text("ALTER TABLE rules ADD COLUMN group_id UUID"))
            await conn.execute(text("CREATE INDEX idx_rules_group_id ON rules(group_id)"))

        # create rule_groups table if not exists
        result = await conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='rule_groups')"
        ))
        if not result.scalar():
            await conn.execute(text("""
                CREATE TABLE rule_groups (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    name VARCHAR(255) NOT NULL,
                    parent_id UUID REFERENCES rule_groups(id),
                    user_id UUID NOT NULL REFERENCES users(id),
                    sort_order INTEGER DEFAULT 0,
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
                )
            """))
            await conn.execute(text("CREATE INDEX idx_rule_groups_user_id ON rule_groups(user_id)"))
            await conn.execute(text("CREATE INDEX idx_rule_groups_parent_id ON rule_groups(parent_id)"))
        else:
            # ensure columns exist
            for col, coltype in [
                ("updated_at", "TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()"),
            ]:
                result = await conn.execute(text(
                    f"SELECT column_name FROM information_schema.columns WHERE table_name='rule_groups' AND column_name='{col}'"
                ))
                if not result.fetchone():
                    await conn.execute(text(f"ALTER TABLE rule_groups ADD COLUMN {col} {coltype}"))

        # Migration: alter embedding column from Vector(384) to Vector(1024)
        try:
            await conn.execute(text(
                "ALTER TABLE skills ALTER COLUMN embedding TYPE vector(1024)"
            ))
            await conn.execute(text(
                "ALTER TABLE rules ALTER COLUMN embedding TYPE vector(1024)"
            ))
        except Exception:
            pass  # Column already correct or doesn't exist
        
        # ensure HNSW indexes exist with optimized parameters (P3优化)
        result = await conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_skill_embedding_hnsw')"
        ))
        exists = result.scalar()
        if not exists:
            # HNSW优化参数：
            # m=16: 每个节点最大连接数，平衡搜索精度和内存消耗
            # ef_construction=64: 构建时候选列表大小，影响构建质量和速度
            await conn.execute(text(
                "CREATE INDEX idx_skill_embedding_hnsw ON skills USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
            ))
            await conn.execute(text(
                "CREATE INDEX idx_rule_embedding_hnsw ON rules USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
            ))
        
        # P3优化：添加复合索引，加速权限过滤后的向量查询
        # User权限过滤索引
        result = await conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_skills_user_active')"
        ))
        if not result.scalar():
            await conn.execute(text(
                "CREATE INDEX idx_skills_user_active ON skills(user_id, is_active)"
            ))
        
        # Scope权限索引
        result = await conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_skills_scope_active')"
        ))
        if not result.scalar():
            await conn.execute(text(
                "CREATE INDEX idx_skills_scope_active ON skills(scope, is_active)"
            ))
        
        # Tags数组索引（使用GIN索引加速数组查询）
        result = await conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_skills_tags_gin')"
        ))
        if not result.scalar():
            await conn.execute(text(
                "CREATE INDEX idx_skills_tags_gin ON skills USING gin(tags)"
            ))
        
        # Review状态索引
        result = await conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_skills_review_status')"
        ))
        if not result.scalar():
            await conn.execute(text(
                "CREATE INDEX idx_skills_review_status ON skills(review_status)"
            ))

        # P0: 创建SkillPermission表
        result = await conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='skill_permissions')"
        ))
        if not result.scalar():
            await conn.execute(text("""
                CREATE TABLE skill_permissions (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
                    allowed_roles VARCHAR[] DEFAULT NULL,
                    denied_roles VARCHAR[] DEFAULT NULL,
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
                )
            """))
            await conn.execute(text("CREATE INDEX idx_skill_permissions_skill_id ON skill_permissions(skill_id)"))

        # P0: 添加用户角色约束
        result = await conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE table_name='users' AND constraint_name='check_user_role')"
        ))
        if not result.scalar():
            await conn.execute(text(
                "ALTER TABLE users ADD CONSTRAINT check_user_role CHECK (role IN ('super_admin', 'admin', 'developer', 'user', 'readonly'))"
            ))

        # P1: 添加LLM角色约束
        result = await conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE table_name='llm_configs' AND constraint_name='check_llm_role')"
        ))
        if not result.scalar():
            await conn.execute(text(
                "ALTER TABLE llm_configs ADD CONSTRAINT check_llm_role CHECK (role IN ('Intent Analyzer', 'Embedding', 'Review', 'Ranker'))"
            ))

        # ensure user nickname, is_active, remark columns
        for col, coltype in [
            ("nickname", "VARCHAR(100) DEFAULT ''"),
            ("is_active", "BOOLEAN DEFAULT TRUE"),
            ("remark", "TEXT DEFAULT ''"),
        ]:
            result = await conn.execute(text(
                f"SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='{col}'"
            ))
            if not result.fetchone():
                await conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {coltype}"))

    async with async_session_factory() as session:
        admin_id = uuid.UUID(int=1)

        # get actual admin user id from DB
        admin_row = await session.execute(
            text("SELECT id FROM users ORDER BY created_at LIMIT 1")
        )
        admin_row_id = admin_row.scalar_one_or_none()
        if admin_row_id:
            admin_id = admin_row_id

        result = await session.execute(text("SELECT COUNT(*) FROM users"))
        if result.scalar() == 0:
            hashed = bcrypt.hashpw(settings.admin_password.encode(), bcrypt.gensalt()).decode()
            session.add(User(
                id=admin_id,
                username=settings.admin_username,
                password=hashed,
                role="admin",
            ))

            if settings.skill_manager_api_key:
                key_hash = hashlib.sha256(settings.skill_manager_api_key.encode()).hexdigest()
                session.add(ApiKey(
                    user_id=admin_id,
                    key_hash=key_hash,
                    label="default-admin-key",
                ))

        # backfill projects.user_id for orphaned rows
        await session.execute(
            text("UPDATE projects SET user_id=:uid WHERE user_id IS NULL"),
            {"uid": admin_id},
        )

        # ensure default project for admin
        default_proj = await session.execute(
            text("SELECT id FROM projects WHERE user_id=:uid AND name='Default'"),
            {"uid": admin_id},
        )
        default_proj_id = default_proj.scalar_one_or_none()
        if not default_proj_id:
            dp = Project(
                id=uuid.UUID(int=2),
                user_id=admin_id,
                name="Default",
                slug="default",
                title="Default",
                status="active",
                description="Default project for all resources",
                config={"is_default": True},
            )
            session.add(dp)
            await session.flush()
            default_proj_id = dp.id

        # backfill existing skills/rules/models without project_id
        for tbl in ("skills", "rules", "llm_configs"):
            await session.execute(
                text(f"UPDATE {tbl} SET project_id=:pid WHERE project_id IS NULL AND user_id=:uid"),
                {"pid": default_proj_id, "uid": admin_id},
            )

        await session.commit()
