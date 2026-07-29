from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.tools.evolution_engine.db.database import Base


class EvolutionEvent(Base):
    __tablename__ = "evolution_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(32), nullable=False)
    source = Column(String(64), nullable=False)
    content = Column(Text)
    result = Column(Text)
    metadata_ = Column("metadata", JSON, default=dict)
    status = Column(String(32), default="pending")
    created_at = Column(DateTime, server_default=func.now())


class EvolutionAnalysis(Base):
    __tablename__ = "evolution_analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, nullable=False)
    category = Column(String(32))
    error_type = Column(String(128))
    root_cause = Column(Text)
    fix_pattern = Column(Text)
    success_pattern = Column(Text)
    affected_tools = Column(JSON, default=list)
    update_type = Column(String(32))
    priority = Column(String(16))
    confidence = Column(Float)
    created_at = Column(DateTime, server_default=func.now())


class EvolutionUpdate(Base):
    __tablename__ = "evolution_updates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(Integer, nullable=False)
    target_tool = Column(String(64), nullable=False)
    update_type = Column(String(32), nullable=False)
    status = Column(String(32), default="pending")
    error_message = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
