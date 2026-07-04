from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.db.database import Base


class ContextRecord(Base):
    __tablename__ = "context_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(128), nullable=False)
    content = Column(Text, nullable=False)
    token_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())


class BudgetAllocation(Base):
    __tablename__ = "budget_allocations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(128), nullable=False)
    tool_name = Column(String(64), nullable=False)
    budget = Column(Integer, nullable=False)
    tokens_used = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())


class CacheEntry(Base):
    __tablename__ = "cache_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query_hash = Column(String(64), unique=True, nullable=False)
    query = Column(Text, nullable=False)
    result = Column(JSON, nullable=False)
    tokens = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime)
