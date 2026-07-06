import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON
from app.db.database import Base, async_session_factory


class ToolRegistry(Base):
    __tablename__ = "tool_registry"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(256), unique=True, nullable=False, index=True)
    display_name = Column(String(256), nullable=True)
    description = Column(Text, nullable=True)
    version = Column(String(32), nullable=True)
    endpoint = Column(String(512), nullable=False)
    status = Column(String(32), default="registered")
    last_health_check = Column(DateTime, nullable=True)
    capabilities = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class ToolInvocation(Base):
    __tablename__ = "tool_invocation"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    tool_name = Column(String(256), nullable=False, index=True)
    capability = Column(String(256), nullable=True)
    arguments = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    status = Column(String(32), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)
    user_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


async def get_session():
    async with async_session_factory() as session:
        yield session
