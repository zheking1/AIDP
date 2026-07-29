"""
Knowledge Module Models
知识库模块数据库模型
"""

import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    Column, String, Text, DateTime, Boolean, Float,
    ForeignKey, Integer, Index
)
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.core.utils import gen_uuid, utcnow


class KnowledgeBase(Base):
    """知识库模型"""

    __tablename__ = "aidp_knowledge_bases"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    project_id = Column(Integer, ForeignKey("aidp_projects.id"), nullable=True, index=True)
    user_id = Column(String(100), nullable=True, index=True)

    name = Column(String(200), nullable=False)
    slug = Column(String(128), nullable=True, index=True)
    description = Column(Text, nullable=True)
    kb_level = Column(String(32), default="project")  # framework / template / project
    parent_id = Column(String(36), ForeignKey("aidp_knowledge_bases.id"), nullable=True, index=True)

    domains = Column(Text, default="[]")  # JSON array
    keywords = Column(Text, default="[]")  # JSON array
    tech_stack = Column(Text, default="[]")  # JSON array

    visibility = Column(String(20), default="private")  # private / team / public

    chunking_strategy = Column(String(50), default="fixed")
    chunk_size = Column(Integer, default=500)
    chunk_overlap = Column(Integer, default=50)
    embedding_model = Column(String(128), default="text-embedding-3-small")

    document_count = Column(Integer, default=0)
    total_chunks = Column(Integer, default=0)

    extra_data = Column(Text, default="{}")

    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    documents = relationship("KnowledgeDocument", back_populates="base", cascade="all, delete-orphan")
    children = relationship("KnowledgeBase", backref="parent", remote_side=[id])

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "kb_level": self.kb_level,
            "parent_id": self.parent_id,
            "domains": json.loads(self.domains) if self.domains else [],
            "keywords": json.loads(self.keywords) if self.keywords else [],
            "tech_stack": json.loads(self.tech_stack) if self.tech_stack else [],
            "visibility": self.visibility,
            "chunking_strategy": self.chunking_strategy,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "embedding_model": self.embedding_model,
            "document_count": self.document_count,
            "total_chunks": self.total_chunks,
            "extra_data": json.loads(self.extra_data) if self.extra_data else {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
        return data


class KnowledgeDocument(Base):
    """知识库文档模型"""

    __tablename__ = "aidp_knowledge_documents"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    base_id = Column(String(36), ForeignKey("aidp_knowledge_bases.id"), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("aidp_projects.id"), nullable=True, index=True)
    user_id = Column(String(100), nullable=True, index=True)

    title = Column(String(500), nullable=False)
    source_type = Column(String(50), default="manual")
    source_uri = Column(String(1000), nullable=True)

    content = Column(Text, nullable=True)
    mime_type = Column(String(100), nullable=True)
    file_size = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)
    category = Column(String(100), nullable=True, index=True)

    embedding = Column(Text, nullable=True)
    embedding_model = Column(String(128), nullable=True)

    tags = Column(Text, default="[]")  # JSON array
    checksum = Column(String(128), nullable=True)
    version = Column(String(128), default="v1")
    index_status = Column(String(20), default="pending", index=True)  # pending / indexing / indexed / error
    summary = Column(Text, nullable=True)
    visibility = Column(String(20), default="private")  # private / team / public
    owner_type = Column(String(32), default="personal")  # personal / team / system
    created_by = Column(String(100), nullable=True)
    updated_by = Column(String(100), nullable=True)

    processing_status = Column(String(20), default="pending", index=True)
    extra_data = Column(Text, default="{}")

    promotion_status = Column(String(20), default="none", index=True)
    # none / pending / reviewed / promoted / rejected / rolled_back
    promotion_report = Column(Text, nullable=True)
    promotion_source_id = Column(String(36), nullable=True, index=True)
    promotion_source_scope = Column(String(20), nullable=True)
    promotion_promoted_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    base = relationship("KnowledgeBase", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    def to_dict(self, include_content: bool = False) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "base_id": self.base_id,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "title": self.title,
            "category": self.category,
            "source_type": self.source_type,
            "source_uri": self.source_uri,
            "mime_type": self.mime_type,
            "file_size": self.file_size,
            "chunk_count": self.chunk_count,
            "tags": json.loads(self.tags) if self.tags else [],
            "checksum": self.checksum,
            "version": self.version,
            "index_status": self.index_status,
            "summary": self.summary,
            "visibility": self.visibility,
            "owner_type": self.owner_type,
            "created_by": self.created_by,
            "updated_by": self.updated_by,
            "processing_status": self.processing_status,
            "extra_data": json.loads(self.extra_data) if self.extra_data else {},
            "promotion_status": self.promotion_status,
            "promotion_report": self.promotion_report,
            "promotion_source_id": self.promotion_source_id,
            "promotion_source_scope": self.promotion_source_scope,
            "promotion_promoted_at": self.promotion_promoted_at.isoformat() if self.promotion_promoted_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
        if include_content:
            data["content"] = self.content
        return data


class DocumentChunk(Base):
    """文档分块模型"""

    __tablename__ = "aidp_document_chunks"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    document_id = Column(String(36), ForeignKey("aidp_knowledge_documents.id"), nullable=False, index=True)
    base_id = Column(String(36), ForeignKey("aidp_knowledge_bases.id"), nullable=False, index=True)

    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)

    embedding = Column(Text, nullable=True)
    token_count = Column(Integer, default=0)

    extra_data = Column(Text, default="{}")

    created_at = Column(DateTime(timezone=True), default=utcnow)

    document = relationship("KnowledgeDocument", back_populates="chunks")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "base_id": self.base_id,
            "chunk_index": self.chunk_index,
            "content": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "token_count": self.token_count,
            "extra_data": json.loads(self.extra_data) if self.extra_data else {},
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class KnowledgeSearchLog(Base):
    """知识库搜索日志"""

    __tablename__ = "aidp_knowledge_search_logs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    base_id = Column(String(36), nullable=True, index=True)
    project_id = Column(Integer, nullable=True, index=True)
    user_id = Column(String(100), nullable=True)

    query = Column(Text, nullable=False)
    results_count = Column(Integer, default=0)
    top_score = Column(Float, nullable=True)
    duration_ms = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "base_id": self.base_id,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "query": self.query,
            "results_count": self.results_count,
            "top_score": self.top_score,
            "duration_ms": self.duration_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class ProjectKnowledgeBinding(Base):
    """项目-知识库绑定"""

    __tablename__ = "aidp_project_knowledge_bindings"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    project_id = Column(String(128), nullable=False, index=True)
    knowledge_base_id = Column(String(36), ForeignKey("aidp_knowledge_bases.id"), nullable=False, index=True)
    binding_type = Column(String(32), default="auto_matched")  # explicit / auto_matched
    priority = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "knowledge_base_id": self.knowledge_base_id,
            "binding_type": self.binding_type,
            "priority": self.priority,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class DocumentTemplate(Base):
    """文档模板模型"""

    __tablename__ = "aidp_document_templates"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(200), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)
    # research / prd / arch / plan / dev / test / ops / meeting

    content = Column(Text, nullable=False)
    variables = Column(Text, default="[]")

    scope = Column(String(20), default="global", index=True)
    project_id = Column(Integer, ForeignKey("aidp_projects.id"), nullable=True, index=True)
    user_id = Column(String(100), nullable=True, index=True)

    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "category": self.category,
            "content": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "variables": json.loads(self.variables) if self.variables else [],
            "scope": self.scope, "project_id": self.project_id, "user_id": self.user_id,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
