"""Memory Tool Database Models with Vector Support.

This module defines the SQLAlchemy models for the Memory Tool,
including support for pgvector embeddings.
"""
import uuid
import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Float,
    ForeignKey, UniqueConstraint, Index, text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base

# Try to import pgvector, but make it optional for SQLite compatibility
try:
    from pgvector.sqlalchemy import Vector
    VECTOR_AVAILABLE = True
except ImportError:
    VECTOR_AVAILABLE = False

Base = declarative_base()

# Backward compatibility - these will be properly initialized in init_db.py
engine = None
async_session = None


def init_engine(database_url: str):
    """Initialize engine and session - call this from main app."""
    global engine, async_session
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    engine = create_async_engine(database_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class MemoryEntry(Base):
    """Memory entry with optional vector embedding support.
    
    Attributes:
        id: Unique identifier (UUID)
        project: Project identifier
        category: Memory category (architecture|decision|pattern|issue|bug|other)
        title: Memory title
        content: Full memory content
        embedding: Vector embedding for semantic search (pgvector)
        memory_tier: Memory hierarchy tier (episodic|semantic|procedural)
        parent_id: Parent memory for hierarchical relationships
        confidence_score: Confidence level (0.0-1.0)
        ai_suggested: Whether this memory was AI-generated
        ai_review_status: Review status for AI-generated memories
        access_count: Number of times accessed
        source_type: Source type (manual|auto|imported)
    """
    __tablename__ = "memory_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project = Column(String(100), index=True, nullable=True)
    user_id = Column(String(100), index=True, nullable=True)
    category = Column(String(50), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    
    # Vector embedding for semantic search (384 dimensions for text-embedding-3-small)
    if VECTOR_AVAILABLE:
        embedding = Column(Vector(384), nullable=True)
    else:
        # Fallback for SQLite - store as JSON string
        embedding = Column(Text, nullable=True)
    
    # Memory hierarchy and management
    memory_tier = Column(String(20), default="semantic", index=True)
    parent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("memory_entries.id"),
        nullable=True,
        index=True
    )
    confidence_score = Column(Float, default=1.0)
    
    # AI-generated memory tracking
    ai_suggested = Column(Boolean, default=False, index=True)
    ai_review_status = Column(String(20), default="approved")  # pending|approved|rejected
    ai_review_comment = Column(Text, nullable=True)
    merged_from = Column(Text, nullable=True)  # JSON array of merged memory IDs
    
    # Usage tracking
    access_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime, nullable=True)
    
    # Source tracking
    source_type = Column(String(50), default="manual")  # manual|auto|imported|ai
    source_uri = Column(String(500), nullable=True)
    
    # Soft delete
    deleted_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    parent = relationship(
        "MemoryEntry",
        remote_side="MemoryEntry.id",
        back_populates="children"
    )
    children = relationship(
        "MemoryEntry",
        back_populates="parent",
        cascade="all, delete-orphan"
    )
    outgoing_relations = relationship(
        "MemoryRelation",
        foreign_keys="MemoryRelation.source_id",
        back_populates="source",
        cascade="all, delete-orphan"
    )
    incoming_relations = relationship(
        "MemoryRelation",
        foreign_keys="MemoryRelation.target_id",
        back_populates="target",
        cascade="all, delete-orphan"
    )
    
    def to_dict(self, include_content: bool = True) -> Dict[str, Any]:
        """Convert memory entry to dictionary.
        
        Args:
            include_content: Whether to include full content
            
        Returns:
            Dictionary representation of the memory entry
        """
        data = {
            "id": str(self.id),
            "project": self.project,
            "user_id": self.user_id,
            "category": self.category,
            "title": self.title,
            "memory_tier": self.memory_tier,
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "confidence_score": self.confidence_score,
            "ai_suggested": self.ai_suggested,
            "ai_review_status": self.ai_review_status,
            "access_count": self.access_count,
            "last_accessed_at": self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            "source_type": self.source_type,
            "source_uri": self.source_uri,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "has_embedding": self.embedding is not None,
        }
        
        if include_content:
            data["content"] = self.content
        else:
            # Truncate content for list views
            data["content_preview"] = self.content[:200] + "..." if len(self.content) > 200 else self.content
        
        return data
    
    def to_graph_node(self) -> Dict[str, Any]:
        """Convert to graph node format for D3.js visualization."""
        # Color mapping by category
        color_map = {
            "architecture": "#3b82f6",  # Blue
            "decision": "#10b981",      # Green
            "pattern": "#f59e0b",       # Amber
            "issue": "#ef4444",         # Red
            "bug": "#dc2626",           # Dark Red
            "other": "#6b7280",         # Gray
        }
        
        # Radius based on access count (min 5, max 20)
        radius = min(20, 5 + (self.access_count or 0) * 0.5)
        
        return {
            "id": str(self.id),
            "title": self.title,
            "category": self.category,
            "memory_tier": self.memory_tier,
            "confidence_score": self.confidence_score,
            "access_count": self.access_count or 0,
            "radius": radius,
            "color": color_map.get(self.category, "#6b7280"),
        }


class MemoryRelation(Base):
    """Relationship between memories for graph visualization.
    
    This model creates edges in the memory graph, representing
    various types of relationships between memory entries.
    
    Attributes:
        id: Unique identifier
        source_id: Source memory ID
        target_id: Target memory ID
        relation_type: Type of relationship
        strength: Relationship strength (0.0-1.0)
    """
    __tablename__ = "memory_relations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(
        UUID(as_uuid=True),
        ForeignKey("memory_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    target_id = Column(
        UUID(as_uuid=True),
        ForeignKey("memory_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    relation_type = Column(
        String(50),
        nullable=False,
        index=True,
        default="similar"
    )  # similar|parent_child|reference|sequence|related
    strength = Column(Float, default=0.5)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    source = relationship(
        "MemoryEntry",
        foreign_keys=[source_id],
        back_populates="outgoing_relations"
    )
    target = relationship(
        "MemoryEntry",
        foreign_keys=[target_id],
        back_populates="incoming_relations"
    )
    
    __table_args__ = (
        UniqueConstraint(
            'source_id', 'target_id', 'relation_type',
            name='unique_relation'
        ),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert relation to dictionary."""
        # Color mapping by relation type
        color_map = {
            "similar": "#94a3b8",
            "parent_child": "#3b82f6",
            "reference": "#10b981",
            "sequence": "#f59e0b",
            "related": "#6b7280",
        }
        
        return {
            "id": str(self.id),
            "source_id": str(self.source_id),
            "target_id": str(self.target_id),
            "relation_type": self.relation_type,
            "strength": self.strength,
            "color": color_map.get(self.relation_type, "#6b7280"),
        }


class ContextPackage(Base):
    """User-generated context packages.
    
    Context packages are collections of memories selected by users
    for specific tasks, with generated context strings.
    
    Attributes:
        id: Unique identifier
        name: Package name
        description: Package description
        project: Associated project
        memory_ids: List of memory IDs included
        total_tokens: Estimated token count
        is_template: Whether this is a reusable template
    """
    __tablename__ = "context_packages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    project = Column(String(100), index=True, nullable=True)
    created_by = Column(String(100), nullable=True)
    
    # Memory IDs stored as JSON array
    memory_ids = Column(Text, nullable=False, default="[]")  # JSON array
    
    # Generated context
    generated_context = Column(Text, nullable=True)
    total_tokens = Column(Integer, default=0)
    
    # Template flag
    is_template = Column(Boolean, default=False, index=True)
    usage_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def to_dict(self, include_context: bool = False) -> Dict[str, Any]:
        """Convert context package to dictionary."""
        import json
        
        memory_ids = []
        try:
            memory_ids = json.loads(self.memory_ids) if self.memory_ids else []
        except json.JSONDecodeError:
            pass
        
        data = {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "project": self.project,
            "created_by": self.created_by,
            "total_tokens": self.total_tokens,
            "memory_count": len(memory_ids),
            "memory_ids": memory_ids,
            "is_template": self.is_template,
            "usage_count": self.usage_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_context and self.generated_context:
            data["generated_context"] = self.generated_context
        
        return data


# Legacy models for backward compatibility
class MemNode(Base):
    """Legacy memory node model."""
    __tablename__ = "mem_node"

    id = Column(Integer, primary_key=True, autoincrement=True)
    memory_id = Column(Integer)
    label = Column(String(256))
    memory_type = Column(String(20))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class MemEdge(Base):
    """Legacy memory edge model."""
    __tablename__ = "mem_edge"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer)
    target_id = Column(Integer)
    relation = Column(String(64))
    weight = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
