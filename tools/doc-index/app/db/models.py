from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, Index
from sqlalchemy.sql import func
from app.db.database import Base


class DocPage(Base):
    __tablename__ = "doc_pages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(512), nullable=False)
    url = Column(String(1024), unique=True)
    content = Column(Text)
    summary = Column(String(2048))
    language = Column(String(32))
    framework = Column(String(64))
    source = Column(String(64))  # wiki/markdown/github/api
    word_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class DocSection(Base):
    __tablename__ = "doc_sections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(Integer, nullable=False)
    heading = Column(String(256))
    content = Column(Text)
    level = Column(Integer, default=1)
    parent_id = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())


class CodeLink(Base):
    __tablename__ = "code_links"

    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(Integer, nullable=False)
    node_type = Column(String(32))  # class/function/method
    node_name = Column(String(512))
    file_path = Column(String(1024))
    line_start = Column(Integer)
    line_end = Column(Integer)
    language = Column(String(32))
    confidence = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now())


class DocDrift(Base):
    __tablename__ = "doc_drifts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(Integer, nullable=False)
    section_heading = Column(String(256))
    drift_score = Column(Float, default=0.0)
    status = Column(String(32), default="detected")
    detected_at = Column(DateTime, server_default=func.now())
    resolved_at = Column(DateTime)
