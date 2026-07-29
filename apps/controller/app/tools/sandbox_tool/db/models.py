import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.tools.sandbox_tool.config import settings


class Base(DeclarativeBase):
    pass


class Execution(Base):
    __tablename__ = "sb_execution"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True, index=True)
    language = Column(String(32), nullable=False, index=True)
    code = Column(Text, nullable=False)
    stdin = Column(Text, nullable=True)
    stdout = Column(Text, nullable=True)
    stderr = Column(Text, nullable=True)
    exit_code = Column(Integer, nullable=True)
    timed_out = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    duration_ms = Column(Integer, nullable=True)


engine = create_async_engine(settings.DATABASE_URL, echo=settings.DATABASE_ECHO)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session():
    async with async_session() as session:
        yield session
