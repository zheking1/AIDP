import logging

from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import engine, async_session_factory

logger = logging.getLogger(__name__)

CREATE_TABLES_SQLITE = """
CREATE TABLE IF NOT EXISTS kt_document (
    id VARCHAR(36) PRIMARY KEY,
    workspace_id VARCHAR(128) NOT NULL,
    project_id VARCHAR(128),
    title VARCHAR(512) NOT NULL,
    doc_type VARCHAR(128) NOT NULL,
    visibility VARCHAR(32) NOT NULL DEFAULT 'private',
    source_uri TEXT,
    object_key TEXT,
    mime_type VARCHAR(255),
    file_name VARCHAR(512),
    file_size INTEGER,
    checksum VARCHAR(128),
    version VARCHAR(128) NOT NULL DEFAULT 'v1',
    index_status VARCHAR(32) NOT NULL DEFAULT 'created',
    tags TEXT NOT NULL DEFAULT '[]',
    metadata TEXT NOT NULL DEFAULT '{}',
    created_by VARCHAR(128),
    updated_by VARCHAR(128),
    owner_type VARCHAR(32) NOT NULL DEFAULT 'personal',
    owner_id VARCHAR(128),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS kt_document_chunk (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(36) NOT NULL REFERENCES kt_document(id),
    workspace_id VARCHAR(128) NOT NULL,
    project_id VARCHAR(128),
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    content_hash VARCHAR(128) NOT NULL,
    token_count INTEGER NOT NULL,
    heading_path TEXT NOT NULL DEFAULT '[]',
    source_start_line INTEGER,
    source_end_line INTEGER,
    page_number INTEGER,
    embedding_model VARCHAR(128),
    embedding_provider VARCHAR(128),
    embedding_dimension INTEGER,
    embedding TEXT,
    keyword_tsv TEXT,
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,
    UNIQUE (document_id, chunk_index)
);

CREATE TABLE IF NOT EXISTS kt_document_index_job (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(36) NOT NULL REFERENCES kt_document(id),
    workspace_id VARCHAR(128) NOT NULL,
    project_id VARCHAR(128),
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    trigger_type VARCHAR(32) NOT NULL DEFAULT 'manual',
    force_reindex BOOLEAN NOT NULL DEFAULT 0,
    chunk_size INTEGER,
    overlap_size INTEGER,
    embedding_model VARCHAR(128),
    chunk_count INTEGER,
    error_code VARCHAR(128),
    error_message TEXT,
    error_details TEXT NOT NULL DEFAULT '{}',
    trace_id VARCHAR(128),
    created_by VARCHAR(128),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    finished_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_kt_document_scope ON kt_document (workspace_id, project_id, visibility) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_kt_document_doc_type ON kt_document (doc_type) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_kt_document_index_status ON kt_document (index_status) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_kt_document_owner ON kt_document (workspace_id, owner_type) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_kt_chunk_document ON kt_document_chunk (document_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_kt_chunk_scope ON kt_document_chunk (workspace_id, project_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_kt_index_job_document ON kt_document_index_job (document_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_kt_index_job_status ON kt_document_index_job (status, created_at);
"""


async def init_database():
    logger.info("Initializing knowledge-tool database...")

    async with engine.begin() as conn:
        for statement in CREATE_TABLES_SQLITE.split(";"):
            statement = statement.strip()
            if statement:
                await conn.execute(text(statement))

    logger.info("Knowledge-tool database initialized successfully")
