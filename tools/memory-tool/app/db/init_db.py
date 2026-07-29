"""Database initialization for Memory Tool.

This module handles database migration and initialization,
supporting both PostgreSQL with pgvector and SQLite.
"""
import logging
from sqlalchemy import text
from app.db.models import Base, init_engine
from app.db.database import engine
from app.config import settings

logger = logging.getLogger(__name__)


async def init_database():
    """Initialize database tables and extensions.
    
    This function:
    1. Creates pgvector extension (PostgreSQL only)
    2. Creates new tables with vector support
    3. Creates indexes for performance
    4. Migrates existing data if needed
    """
    # Initialize backward compatibility exports
    init_engine(settings.DATABASE_URL)
    
    is_postgres = "postgresql" in settings.DATABASE_URL.lower()
    
    async with engine.begin() as conn:
        if is_postgres:
            await _init_postgresql(conn)
        else:
            await _init_sqlite(conn)
        
        logger.info("Memory-tool database initialized successfully")


async def _init_postgresql(conn):
    """Initialize PostgreSQL with pgvector support."""
    logger.info("Initializing PostgreSQL with pgvector...")
    
    # 1. Enable pgvector extension
    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    
    # 2. Create memory_entries table with vector support
    await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS memory_entries (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project VARCHAR(100),
            user_id VARCHAR(100),
            category VARCHAR(50) NOT NULL,
            title VARCHAR(200) NOT NULL,
            content TEXT NOT NULL,
            embedding VECTOR(384),
            memory_tier VARCHAR(20) DEFAULT 'semantic',
            parent_id UUID REFERENCES memory_entries(id) ON DELETE SET NULL,
            confidence_score FLOAT DEFAULT 1.0,
            ai_suggested BOOLEAN DEFAULT FALSE,
            ai_review_status VARCHAR(20) DEFAULT 'approved',
            ai_review_comment TEXT,
            merged_from TEXT,
            access_count INTEGER DEFAULT 0,
            last_accessed_at TIMESTAMP,
            source_type VARCHAR(50) DEFAULT 'manual',
            source_uri VARCHAR(500),
            deleted_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))
    
    # 3. Create indexes for memory_entries
    indexes = [
        ("idx_mem_entries_project", "project"),
        ("idx_mem_entries_user_id", "user_id"),
        ("idx_mem_entries_category", "category"),
        ("idx_mem_entries_tier", "memory_tier"),
        ("idx_mem_entries_parent", "parent_id"),
        ("idx_mem_entries_ai", "ai_suggested"),
        ("idx_mem_entries_review", "ai_review_status"),
        ("idx_mem_entries_created", "created_at DESC"),
    ]
    
    for idx_name, column in indexes:
        await conn.execute(text(f"""
            CREATE INDEX IF NOT EXISTS {idx_name} 
            ON memory_entries({column})
        """))
    
    # 4. Create HNSW index for vector search (high performance ANN)
    await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_mem_entries_embedding_hnsw 
        ON memory_entries 
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """))
    
    # 5. Create memory_relations table
    await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS memory_relations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            source_id UUID NOT NULL REFERENCES memory_entries(id) ON DELETE CASCADE,
            target_id UUID NOT NULL REFERENCES memory_entries(id) ON DELETE CASCADE,
            relation_type VARCHAR(50) NOT NULL DEFAULT 'similar',
            strength FLOAT DEFAULT 0.5,
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(source_id, target_id, relation_type)
        )
    """))
    
    # 6. Create indexes for memory_relations
    await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_mem_relations_source 
        ON memory_relations(source_id)
    """))
    await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_mem_relations_target 
        ON memory_relations(target_id)
    """))
    await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_mem_relations_type 
        ON memory_relations(relation_type)
    """))
    
    # 7. Create context_packages table
    await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS context_packages (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(200) NOT NULL,
            description TEXT,
            project VARCHAR(100),
            created_by VARCHAR(100),
            memory_ids TEXT DEFAULT '[]',
            generated_context TEXT,
            total_tokens INTEGER DEFAULT 0,
            is_template BOOLEAN DEFAULT FALSE,
            usage_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))
    
    # 8. Create indexes for context_packages
    await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_context_packages_project 
        ON context_packages(project)
    """))
    await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_context_packages_template 
        ON context_packages(is_template) 
        WHERE is_template = TRUE
    """))
    
    # 9. Create legacy tables for backward compatibility
    await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS mem_entry (
            id SERIAL PRIMARY KEY,
            project VARCHAR(256) NOT NULL,
            user_id INTEGER,
            category VARCHAR(64) NOT NULL,
            title VARCHAR(512) NOT NULL,
            content TEXT NOT NULL,
            tags TEXT,
            pinned BOOLEAN DEFAULT FALSE,
            memory_tier VARCHAR(20) DEFAULT 'episodic',
            parent_id INTEGER REFERENCES mem_entry(id),
            source_type VARCHAR(50) DEFAULT 'manual',
            source_ref VARCHAR(512),
            access_count INTEGER DEFAULT 0,
            last_accessed_at TIMESTAMP,
            confidence FLOAT DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            deleted_at TIMESTAMP
        )
    """))
    
    await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_mem_entry_project ON mem_entry(project)
    """))
    await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_mem_entry_user_id ON mem_entry(user_id)
    """))
    await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_mem_entry_category ON mem_entry(category)
    """))
    await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_mem_entry_tier ON mem_entry(memory_tier)
    """))
    
    logger.info("PostgreSQL tables and indexes created")


async def _init_sqlite(conn):
    """Initialize SQLite (without vector support)."""
    logger.info("Initializing SQLite (vector search disabled)...")
    
    # 1. Create memory_entries table (without vector type)
    await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS memory_entries (
            id TEXT PRIMARY KEY,
            project TEXT,
            user_id TEXT,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            embedding TEXT,  -- Stored as JSON string
            memory_tier TEXT DEFAULT 'semantic',
            parent_id TEXT REFERENCES memory_entries(id) ON DELETE SET NULL,
            confidence_score REAL DEFAULT 1.0,
            ai_suggested INTEGER DEFAULT 0,
            ai_review_status TEXT DEFAULT 'approved',
            ai_review_comment TEXT,
            merged_from TEXT,
            access_count INTEGER DEFAULT 0,
            last_accessed_at TIMESTAMP,
            source_type TEXT DEFAULT 'manual',
            source_uri TEXT,
            deleted_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # 2. Create indexes
    await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_mem_entries_project ON memory_entries(project)
    """))
    await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_mem_entries_category ON memory_entries(category)
    """))
    await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_mem_entries_tier ON memory_entries(memory_tier)
    """))
    await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_mem_entries_ai ON memory_entries(ai_suggested)
    """))
    
    # 3. Create memory_relations table
    await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS memory_relations (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL REFERENCES memory_entries(id) ON DELETE CASCADE,
            target_id TEXT NOT NULL REFERENCES memory_entries(id) ON DELETE CASCADE,
            relation_type TEXT NOT NULL DEFAULT 'similar',
            strength REAL DEFAULT 0.5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source_id, target_id, relation_type)
        )
    """))
    
    await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_mem_relations_source ON memory_relations(source_id)
    """))
    await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_mem_relations_target ON memory_relations(target_id)
    """))
    
    # 4. Create context_packages table
    await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS context_packages (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            project TEXT,
            created_by TEXT,
            memory_ids TEXT DEFAULT '[]',
            generated_context TEXT,
            total_tokens INTEGER DEFAULT 0,
            is_template INTEGER DEFAULT 0,
            usage_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_context_packages_project ON context_packages(project)
    """))
    
    # 5. Create legacy tables
    await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS mem_entry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT NOT NULL,
            user_id INTEGER,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT,
            pinned INTEGER DEFAULT 0,
            memory_tier TEXT DEFAULT 'episodic',
            parent_id INTEGER REFERENCES mem_entry(id),
            source_type TEXT DEFAULT 'manual',
            source_ref TEXT,
            access_count INTEGER DEFAULT 0,
            last_accessed_at TIMESTAMP,
            confidence REAL DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP
        )
    """))
    
    await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_mem_entry_project ON mem_entry(project)
    """))
    await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_mem_entry_category ON mem_entry(category)
    """))
    
    logger.info("SQLite tables created (vector search not available)")


async def migrate_legacy_data():
    """Migrate data from legacy tables to new schema.
    
    This function migrates existing data from mem_entry to memory_entries.
    Should be run once during upgrade.
    """
    from sqlalchemy import select
    from app.db.database import async_session_factory
    import uuid
    import json
    
    logger.info("Checking for legacy data migration...")
    
    async with async_session_factory() as session:
        async with session.begin():
            # Check if there's data in old table
            result = await session.execute(text("SELECT COUNT(*) FROM mem_entry WHERE deleted_at IS NULL"))
            count = result.scalar()
            
            if count == 0:
                logger.info("No legacy data to migrate")
                return
            
            logger.info(f"Found {count} legacy entries to migrate")
            
            # Fetch legacy entries
            legacy_result = await session.execute(
                text("""
                    SELECT id, project, category, title, content, memory_tier,
                           parent_id, source_type, source_ref, access_count,
                           last_accessed_at, confidence, created_at
                    FROM mem_entry
                    WHERE deleted_at IS NULL
                """)
            )
            
            legacy_entries = legacy_result.fetchall()
            migrated_count = 0
            
            for old_entry in legacy_entries:
                # Create new UUID-based entry
                new_id = str(uuid.uuid4())
                
                await session.execute(
                    text("""
                        INSERT INTO memory_entries (
                            id, project, category, title, content, memory_tier,
                            parent_id, source_type, source_uri, access_count,
                            last_accessed_at, confidence_score, created_at, ai_suggested
                        ) VALUES (
                            :id, :project, :category, :title, :content, :memory_tier,
                            :parent_id, :source_type, :source_uri, :access_count,
                            :last_accessed_at, :confidence, :created_at, FALSE
                        )
                    """),
                    {
                        "id": new_id,
                        "project": old_entry.project,
                        "category": old_entry.category,
                        "title": old_entry.title,
                        "content": old_entry.content,
                        "memory_tier": old_entry.memory_tier or "semantic",
                        "parent_id": None,  # Reset parent relationships
                        "source_type": old_entry.source_type or "manual",
                        "source_uri": old_entry.source_ref,
                        "access_count": old_entry.access_count or 0,
                        "last_accessed_at": old_entry.last_accessed_at,
                        "confidence": old_entry.confidence or 1.0,
                        "created_at": old_entry.created_at,
                    }
                )
                migrated_count += 1
            
            logger.info(f"Migrated {migrated_count} entries successfully")
