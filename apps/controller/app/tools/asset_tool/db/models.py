import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Text, Integer, DateTime, JSON, ForeignKey, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB

from app.tools.asset_tool.db.database import Base


def utcnow():
    return datetime.now(timezone.utc)


def gen_uuid():
    return str(uuid.uuid4())


class AtAsset(Base):
    __tablename__ = "at_asset"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    workspace_id = Column(String(128), nullable=False)
    project_id = Column(String(128))
    title = Column(String(512), nullable=False)
    asset_type = Column(String(32), nullable=False)
    language = Column(String(64))
    format = Column(String(64))
    visibility = Column(String(32), nullable=False)
    content = Column(Text, nullable=False)
    description = Column(Text)
    variables = Column(JSONB, nullable=False, default=dict)
    metadata_ = Column("metadata", JSONB, nullable=False, default=dict)
    created_by = Column(String(128))
    updated_by = Column(String(128))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime(timezone=True))


class AtAssetTag(Base):
    __tablename__ = "at_asset_tag"
    __table_args__ = (
        UniqueConstraint("asset_id", "tag", name="uq_at_asset_tag"),
    )

    id = Column(String(36), primary_key=True, default=gen_uuid)
    asset_id = Column(String(36), ForeignKey("at_asset.id"), nullable=False)
    tag = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
