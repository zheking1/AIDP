from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON
from sqlalchemy.sql import func
from app.db import Base


class WatchedProject(Base):
    __tablename__ = "watched_projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_name = Column(String(255), nullable=False, unique=True)
    local_path = Column(String(1024), nullable=False)
    code_index_project_id = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    ignored_dirs = Column(JSON, default=list)
    ignored_patterns = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class WatchEvent(Base):
    __tablename__ = "watch_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, nullable=False)
    event_type = Column(String(50), nullable=False)
    file_path = Column(String(1024), nullable=False)
    processed = Column(Boolean, default=False)
    error_message = Column(String(2048), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
