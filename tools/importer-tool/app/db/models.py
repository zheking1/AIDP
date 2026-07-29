import json
from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy import (
    Column, String, Text, DateTime, Integer, JSON, ForeignKey, Index, Float, Boolean,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DATABASE_ECHO)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class ImportSession(Base):
    __tablename__ = "it_import_session"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    project_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    scope: Mapped[str] = mapped_column(String(20), default="personal")

    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    source_uri: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    completed_items: Mapped[int] = mapped_column(Integer, default=0)
    failed_items: Mapped[int] = mapped_column(Integer, default=0)
    skipped_items: Mapped[int] = mapped_column(Integer, default=0)

    metadata_: Mapped[str] = mapped_column("metadata", Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    items = relationship("ImportItem", back_populates="session", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "scope": self.scope,
            "source_type": self.source_type,
            "source_uri": self.source_uri,
            "status": self.status,
            "total_items": self.total_items,
            "completed_items": self.completed_items,
            "failed_items": self.failed_items,
            "skipped_items": self.skipped_items,
            "metadata": json.loads(self.metadata_) if self.metadata_ else {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class ImportItem(Base):
    __tablename__ = "it_import_item"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("it_import_session.id"), nullable=False, index=True)
    item_index: Mapped[int] = mapped_column(Integer, nullable=False)

    filename: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    classified_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    classified_confidence: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    suggested_title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    suggested_tags: Mapped[str] = mapped_column(Text, default="[]")
    suggested_category: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    suggested_severity: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    quality_passed: Mapped[Optional[bool]] = mapped_column(Integer, nullable=True)
    quality_issues: Mapped[str] = mapped_column(Text, default="[]")

    confirmed_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    confirmed_tags: Mapped[str] = mapped_column(Text, default="[]")
    confirmed_category: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    confirmed_severity: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    persist_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    persist_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    persist_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    persist_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    persisted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    session = relationship("ImportSession", back_populates="items")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "item_index": self.item_index,
            "filename": self.filename,
            "content": self.content[:500] + "..." if self.content and len(self.content) > 500 else self.content,
            "content_hash": self.content_hash,
            "classified_type": self.classified_type,
            "classified_confidence": self.classified_confidence,
            "suggested_title": self.suggested_title,
            "suggested_tags": json.loads(self.suggested_tags) if self.suggested_tags else [],
            "suggested_category": self.suggested_category,
            "suggested_severity": self.suggested_severity,
            "quality_passed": bool(self.quality_passed) if self.quality_passed is not None else None,
            "quality_issues": json.loads(self.quality_issues) if self.quality_issues else [],
            "confirmed_type": self.confirmed_type,
            "confirmed_tags": json.loads(self.confirmed_tags) if self.confirmed_tags else [],
            "confirmed_category": self.confirmed_category,
            "confirmed_severity": self.confirmed_severity,
            "persist_type": self.persist_type,
            "persist_id": self.persist_id,
            "persist_url": self.persist_url,
            "persist_version": self.persist_version,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "persisted_at": self.persisted_at.isoformat() if self.persisted_at else None,
        }


class PromotionReviewConfig(Base):
    __tablename__ = "it_promotion_review_config"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), default="openai")
    api_base: Mapped[str] = mapped_column(String(500), default="https://api.openai.com/v1")
    model_name: Mapped[str] = mapped_column(String(128), default="gpt-4o")
    api_key: Mapped[str] = mapped_column(Text, nullable=True)
    max_tokens: Mapped[int] = mapped_column(Integer, default=4096)
    temperature: Mapped[float] = mapped_column(Float, default=0.3)
    redact_regexes: Mapped[str] = mapped_column(Text, default="[]")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "provider": self.provider,
            "api_base": self.api_base,
            "model_name": self.model_name,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "redact_regexes": json.loads(self.redact_regexes) if self.redact_regexes else [],
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class PromotionLog(Base):
    __tablename__ = "it_promotion_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # submitted / reviewed / promoted / rejected / rolled_back
    from_scope: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    to_scope: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    review_report: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    triggered_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    metadata_: Mapped[str] = mapped_column("metadata", Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "action": self.action,
            "from_scope": self.from_scope,
            "to_scope": self.to_scope,
            "review_report": self.review_report,
            "triggered_by": self.triggered_by,
            "metadata": json.loads(self.metadata_) if self.metadata_ else {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
