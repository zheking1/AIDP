import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.tools.quality_tool.config import settings


class Base(DeclarativeBase):
    pass


class CheckResult(Base):
    __tablename__ = "ql_check_result"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True, index=True)
    filename = Column(String(512), nullable=True)
    language = Column(String(32), nullable=True)
    check_type = Column(String(32), nullable=False)
    issues = Column(JSON, nullable=True)
    issue_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


engine = create_async_engine(settings.DATABASE_URL, echo=settings.DATABASE_ECHO)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session():
    async with async_session() as session:
        yield session
