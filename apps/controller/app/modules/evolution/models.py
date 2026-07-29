import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean
from sqlalchemy.sql import func
from app.db.database import Base


class EvolutionVersion(Base):
    __tablename__ = "evolution_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(String(20), nullable=False, default="0.1.0")
    level = Column(String(20), nullable=False, default="project")
    title = Column(String(256), nullable=False)
    description = Column(Text)
    source_project_id = Column(Integer, default=0)
    created_by = Column(Integer, default=0)
    created_by_name = Column(String(128))

    changes = Column(JSON, default=dict)
    affected_tools = Column(JSON, default=list)
    affected_projects = Column(JSON, default=list)

    review_status = Column(String(20), default="pending")
    reviewed_by = Column(Integer)
    reviewed_by_name = Column(String(128))
    reviewed_at = Column(DateTime)
    review_comment = Column(Text)
    review_log = Column(JSON, default=list)

    source_event_id = Column(Integer)
    source_analysis_id = Column(Integer)
    source_tool = Column(String(64))

    is_rollback_point = Column(Boolean, default=False)
    parent_version = Column(String(20))

    published_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())