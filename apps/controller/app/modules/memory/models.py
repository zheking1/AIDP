"""
Memory Module Models
记忆模块数据库模型
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


class MemoryEntry(Base):
    """记忆条目模型"""

    __tablename__ = "aidp_memory_entries"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    project_id = Column(Integer, ForeignKey("aidp_projects.id"), nullable=True, index=True)
    user_id = Column(String(100), nullable=True, index=True)

    category = Column(String(50), nullable=False, index=True, default="other")
    memory_tier = Column(String(20), default="semantic", index=True)

    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)

    embedding = Column(Text, nullable=True)
    embedding_model = Column(String(128), default="text-embedding-3-small")

    parent_id = Column(String(36), ForeignKey("aidp_memory_entries.id"), nullable=True, index=True)
    confidence_score = Column(Float, default=1.0)

    ai_suggested = Column(Boolean, default=False, index=True)
    ai_review_status = Column(String(20), default="approved")
    ai_review_comment = Column(Text, nullable=True)
    merged_from = Column(Text, nullable=True)

    access_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)

    source_type = Column(String(50), default="manual")
    source_uri = Column(String(500), nullable=True)

    extra_data = Column(Text, default="{}")

    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    parent = relationship("MemoryEntry", remote_side="MemoryEntry.id", back_populates="children")
    children = relationship("MemoryEntry", back_populates="parent", cascade="all, delete-orphan")
    outgoing_relations = relationship("MemoryRelation", foreign_keys="MemoryRelation.source_id", back_populates="source", cascade="all, delete-orphan")
    incoming_relations = relationship("MemoryRelation", foreign_keys="MemoryRelation.target_id", back_populates="target", cascade="all, delete-orphan")

    def to_dict(self, include_content: bool = True) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "category": self.category,
            "memory_tier": self.memory_tier,
            "title": self.title,
            "parent_id": self.parent_id,
            "confidence_score": self.confidence_score,
            "ai_suggested": self.ai_suggested,
            "ai_review_status": self.ai_review_status,
            "access_count": self.access_count,
            "last_accessed_at": self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            "source_type": self.source_type,
            "source_uri": self.source_uri,
            "extra_data": json.loads(self.extra_data) if self.extra_data else {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
        if include_content:
            data["content"] = self.content
            data["ai_review_comment"] = self.ai_review_comment
            data["merged_from"] = json.loads(self.merged_from) if self.merged_from else []
        return data


class MemoryRelation(Base):
    """记忆关系模型"""

    __tablename__ = "aidp_memory_relations"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    source_id = Column(String(36), ForeignKey("aidp_memory_entries.id"), nullable=False, index=True)
    target_id = Column(String(36), ForeignKey("aidp_memory_entries.id"), nullable=False, index=True)

    relation_type = Column(String(50), nullable=False, index=True)
    strength = Column(Float, default=1.0)
    description = Column(Text, nullable=True)

    extra_data = Column(Text, default="{}")

    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    source = relationship("MemoryEntry", foreign_keys=[source_id], back_populates="outgoing_relations")
    target = relationship("MemoryEntry", foreign_keys=[target_id], back_populates="incoming_relations")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type,
            "strength": self.strength,
            "description": self.description,
            "extra_data": json.loads(self.extra_data) if self.extra_data else {},
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class MemoryAccessLog(Base):
    """记忆访问日志"""

    __tablename__ = "aidp_memory_access_logs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    memory_id = Column(String(36), ForeignKey("aidp_memory_entries.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("aidp_projects.id"), nullable=True, index=True)

    action = Column(String(50), nullable=False)
    query = Column(Text, nullable=True)
    user_id = Column(String(100), nullable=True)
    ip_address = Column(String(45), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "memory_id": self.memory_id,
            "project_id": self.project_id,
            "action": self.action,
            "query": self.query,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class ContextPackage(Base):
    """上下文包模型"""

    __tablename__ = "aidp_context_packages"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    project_id = Column(Integer, ForeignKey("aidp_projects.id"), nullable=True, index=True)
    user_id = Column(String(100), nullable=True, index=True)
    created_by = Column(String(100), nullable=True)

    memory_ids = Column(Text, default="[]")
    generated_context = Column(Text, nullable=True)
    total_tokens = Column(Integer, default=0)
    is_template = Column(Boolean, default=False, index=True)
    usage_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    def to_dict(self, include_context: bool = False) -> Dict[str, Any]:
        import json
        data = {
            "id": self.id, "name": self.name, "description": self.description,
            "project_id": self.project_id, "user_id": self.user_id,
            "created_by": self.created_by,
            "total_tokens": self.total_tokens,
            "memory_ids": json.loads(self.memory_ids) if self.memory_ids else [],
            "is_template": self.is_template, "usage_count": self.usage_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_context and self.generated_context:
            data["generated_context"] = self.generated_context
        return data
