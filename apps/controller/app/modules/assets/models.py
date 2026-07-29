"""
Assets Module Models
"""

import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from sqlalchemy import (
    Column, String, Text, DateTime, Boolean, Float,
    ForeignKey, Integer, Index
)
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.core.utils import gen_uuid, utcnow


class Asset(Base):
    __tablename__ = "aidp_assets"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    project_id = Column(Integer, ForeignKey("aidp_projects.id"), nullable=True, index=True)
    user_id = Column(String(100), nullable=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    asset_type = Column(String(50), nullable=False, index=True, default="snippet")
    language = Column(String(50), nullable=True, index=True)
    format = Column(String(50), nullable=True, default="text")
    visibility = Column(String(20), default="project", index=True)
    content = Column(Text, nullable=False)
    variables = Column(Text, default="{}")
    extra_data = Column(Text, default="{}")
    created_by = Column(String(100), nullable=True)
    updated_by = Column(String(100), nullable=True)
    access_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    tags = relationship("AssetTag", back_populates="asset", cascade="all, delete-orphan")

    def to_dict(self, include_content: bool = True) -> Dict[str, Any]:
        data = {
            "id": self.id, "project_id": self.project_id, "user_id": self.user_id,
            "title": self.title, "description": self.description,
            "asset_type": self.asset_type, "language": self.language,
            "format": self.format, "visibility": self.visibility,
            "variables": json.loads(self.variables) if self.variables else {},
            "extra_data": json.loads(self.extra_data) if self.extra_data else {},
            "created_by": self.created_by, "updated_by": self.updated_by,
            "access_count": self.access_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
        try:
            data["tags"] = [t.tag for t in self.tags] if self.tags else []
        except Exception:
            data["tags"] = []
        if include_content:
            data["content"] = self.content
        return data


class AssetTag(Base):
    __tablename__ = "aidp_asset_tags"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    asset_id = Column(String(36), ForeignKey("aidp_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    tag = Column(String(100), nullable=False, index=True)

    asset = relationship("Asset", back_populates="tags")

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "asset_id": self.asset_id, "tag": self.tag}