from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, Index, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from app.db.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(256), nullable=False)
    path = Column(String(1024), nullable=False, unique=True)
    language = Column(String(32))
    framework = Column(String(64))
    status = Column(String(32), default="scanning")
    file_count = Column(Integer, default=0)
    node_count = Column(Integer, default=0)
    last_scan_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Node(Base):
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, nullable=False)
    node_type = Column(String(32), nullable=False)
    name = Column(String(512), nullable=False)
    qualified_name = Column(String(1024))
    file_path = Column(String(1024))
    line_start = Column(Integer)
    line_end = Column(Integer)
    language = Column(String(32))
    framework = Column(String(64))
    metadata_ = Column("metadata", JSON, default=dict)
    parent_id = Column(Integer)
    checksum = Column(String(64))
    signature = Column(Text)
    docstring = Column(Text)
    return_type = Column(String(256))
    params_json = Column(Text)
    file_hash = Column(String(64))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_node_project", "project_id", "node_type"),
        Index("idx_node_file", "project_id", "file_path"),
    )


class Edge(Base):
    __tablename__ = "edges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, nullable=False)
    source_id = Column(Integer, nullable=False)
    target_id = Column(Integer, nullable=False)
    edge_type = Column(String(32), nullable=False)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now())


class FileFingerprint(Base):
    __tablename__ = "file_fingerprints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, nullable=False)
    file_path = Column(String(1024), nullable=False)
    file_hash = Column(String(64), nullable=False)
    last_indexed_at = Column(DateTime, nullable=False, server_default=func.now())
    node_count = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("project_id", "file_path", name="uq_fingerprint_file"),
    )


class NodeEmbedding(Base):
    __tablename__ = "node_embeddings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    node_id = Column(Integer, nullable=False)
    project_id = Column(Integer, nullable=False)
    embedding = Column(Text, nullable=False)
    embedding_model = Column(String(64), nullable=False)
    content_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("node_id", "embedding_model", name="uq_node_embedding"),
    )
