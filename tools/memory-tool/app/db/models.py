import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


class MemoryEntry(Base):
    __tablename__ = "mem_entry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project = Column(String(256), nullable=False, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    category = Column(String(64), nullable=False, index=True)
    title = Column(String(512), nullable=False)
    content = Column(Text, nullable=False)
    tags = Column(Text, nullable=True)
    pinned = Column(Boolean, default=False)
    memory_tier = Column(String(20), default="episodic")
    parent_id = Column(Integer, ForeignKey("mem_entry.id"))
    source_type = Column(String(50), default="manual")
    source_ref = Column(String(512))
    access_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime)
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    deleted_at = Column(DateTime)


class MemNode(Base):
    __tablename__ = "mem_node"

    id = Column(Integer, primary_key=True, autoincrement=True)
    memory_id = Column(Integer, ForeignKey("mem_entry.id"))
    label = Column(String(256))
    memory_type = Column(String(20))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class MemEdge(Base):
    __tablename__ = "mem_edge"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("mem_node.id"))
    target_id = Column(Integer, ForeignKey("mem_node.id"))
    relation = Column(String(64))
    weight = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session():
    async with async_session() as session:
        yield session
