import uuid
from datetime import datetime, timezone

import json

from sqlalchemy import (
    Column, String, Text, Boolean, Integer, DateTime, JSON, Float, ForeignKey, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB

from app.db.database import Base


def utcnow():
    return datetime.now(timezone.utc)


def gen_uuid():
    return str(uuid.uuid4())


def _json_default(value):
    """JSON default for SQLite TEXT columns storing JSON."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _json_loads(value):
    """JSON loads for reading TEXT columns on SQLite."""
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return value


# ── KnowledgeBase (NEW) ──────────────────────────────────

class KnowledgeBase(Base):
    __tablename__ = "kt_knowledge_bases"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(128), nullable=False)
    slug = Column(String(128), unique=True, nullable=False)
    description = Column(Text)

    kb_level = Column(String(32), nullable=False, default="project")
    parent_id = Column(String(36), ForeignKey("kt_knowledge_bases.id"), nullable=True)

    domains = Column(Text, default="[]")
    keywords = Column(Text, default="[]")
    tech_stack = Column(Text, default="[]")

    visibility = Column(String(20), default="private")
    owner_id = Column(String(128))

    chunk_size = Column(Integer, default=512)
    overlap_size = Column(Integer, default=50)
    embedding_model = Column(String(128), default="text-embedding-3-small")

    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow)
    deleted_at = Column(DateTime(timezone=True))


# ── Project-KnowledgeBinding (NEW) ───────────────────────

class ProjectKnowledgeBinding(Base):
    __tablename__ = "kt_project_knowledge_bindings"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    project_id = Column(String(128), nullable=False)
    knowledge_base_id = Column(String(36), ForeignKey("kt_knowledge_bases.id"), nullable=False)
    binding_type = Column(String(32), default="auto_matched")
    priority = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=utcnow)


# ── KtDocument (UPDATED) ─────────────────────────────────

class KtDocument(Base):
    __tablename__ = "kt_document"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    workspace_id = Column(String(128), nullable=True)
    project_id = Column(String(128), nullable=True)
    knowledge_base_id = Column(String(36), ForeignKey("kt_knowledge_bases.id"), nullable=True)
    title = Column(String(512), nullable=False)
    doc_type = Column(String(128), nullable=False)
    visibility = Column(String(32), nullable=False)
    owner_type = Column(String(32), nullable=False, default='personal')
    owner_id = Column(String(128))
    source_uri = Column(Text)
    object_key = Column(Text)
    mime_type = Column(String(255))
    file_name = Column(String(512))
    file_size = Column(Integer)
    checksum = Column(String(128))
    version = Column(String(128), nullable=False, default="v1")
    index_status = Column(String(32), nullable=False, default="created")
    tags = Column(Text, default="[]")
    metadata_ = Column("metadata", Text, default="{}")
    summary = Column(Text)
    summary_embedding = Column(Text)
    created_by = Column(String(128))
    updated_by = Column(String(128))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime(timezone=True))


class KtDocumentChunk(Base):
    __tablename__ = "kt_document_chunk"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_kt_chunk_doc_index"),
    )

    id = Column(String(36), primary_key=True, default=gen_uuid)
    document_id = Column(String(36), ForeignKey("kt_document.id"), nullable=False)
    workspace_id = Column(String(128), nullable=False)
    project_id = Column(String(128))
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    content_hash = Column(String(128), nullable=False)
    token_count = Column(Integer, nullable=False)
    heading_path = Column(JSONB, nullable=False, default=list)
    source_start_line = Column(Integer)
    source_end_line = Column(Integer)
    page_number = Column(Integer)
    embedding_model = Column(String(128))
    embedding_provider = Column(String(128))
    embedding_dimension = Column(Integer)
    embedding = Column(Text)
    keyword_tsv = Column(Text)
    metadata_ = Column("metadata", JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime(timezone=True))


class KtDocumentIndexJob(Base):
    __tablename__ = "kt_document_index_job"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    document_id = Column(String(36), ForeignKey("kt_document.id"), nullable=False)
    workspace_id = Column(String(128), nullable=False)
    project_id = Column(String(128))
    status = Column(String(32), nullable=False, default="pending")
    trigger_type = Column(String(32), nullable=False, default="manual")
    force_reindex = Column(Boolean, nullable=False, default=False)
    chunk_size = Column(Integer)
    overlap_size = Column(Integer)
    embedding_model = Column(String(128))
    chunk_count = Column(Integer)
    error_code = Column(String(128))
    error_message = Column(Text)
    error_details = Column(JSONB, nullable=False, default=dict)
    trace_id = Column(String(128))
    created_by = Column(String(128))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))
