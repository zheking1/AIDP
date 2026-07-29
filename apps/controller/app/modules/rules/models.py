"""
Rules Module Models
规则模块数据库模型 - 三层架构: global/personal/project
"""

import json
from typing import Optional, Dict, Any

from sqlalchemy import Column, String, Text, DateTime, Boolean, Float, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.core.utils import gen_uuid, utcnow


class RuleGroup(Base):
    """规则分组"""

    __tablename__ = "aidp_rule_groups"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    scope = Column(String(20), nullable=False, index=True, default="personal")
    parent_id = Column(String(36), ForeignKey("aidp_rule_groups.id"), nullable=True, index=True)
    user_id = Column(String(100), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("aidp_projects.id"), nullable=True, index=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    children = relationship("RuleGroup", back_populates="parent", cascade="all, delete-orphan")
    parent = relationship("RuleGroup", remote_side="RuleGroup.id", back_populates="children")
    rules = relationship("Rule", back_populates="group", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "description": self.description,
            "scope": self.scope, "parent_id": self.parent_id,
            "user_id": self.user_id, "project_id": self.project_id,
            "sort_order": self.sort_order,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Rule(Base):
    """规则模型"""

    __tablename__ = "aidp_rules"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=False)

    category = Column(String(50), nullable=False, index=True, default="code_style")
    severity = Column(String(20), nullable=False, default="medium")
    priority = Column(Integer, default=0, index=True)
    version = Column(Integer, default=1)

    scope = Column(String(20), nullable=False, index=True, default="personal")
    # global / personal / project

    pattern = Column(Text, nullable=True)
    auto_fix = Column(Text, nullable=True)

    allowed_roles = Column(Text, default="[]")
    tags = Column(Text, default="[]")

    review_status = Column(String(20), default="approved", index=True)
    review_report = Column(Text, nullable=True)
    review_log = Column(Text, default="[]")

    promotion_status = Column(String(20), default="none", index=True)
    # none / pending / reviewed / promoted / rejected / rolled_back
    promotion_report = Column(Text, nullable=True)
    promotion_source_id = Column(String(36), nullable=True, index=True)
    promotion_source_scope = Column(String(20), nullable=True)
    promotion_promoted_at = Column(DateTime(timezone=True), nullable=True)

    embedding = Column(Text, nullable=True)
    embedding_model = Column(String(128), default="text-embedding-3-small")

    group_id = Column(String(36), ForeignKey("aidp_rule_groups.id"), nullable=True, index=True)
    user_id = Column(String(100), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("aidp_projects.id"), nullable=True, index=True)

    is_active = Column(Boolean, default=True, index=True)
    access_count = Column(Integer, default=0)
    extra_data = Column(Text, default="{}")

    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    group = relationship("RuleGroup", back_populates="rules")

    def to_dict(self, include_content: bool = False) -> Dict[str, Any]:
        data = {
            "id": self.id, "name": self.name, "description": self.description,
            "category": self.category, "severity": self.severity,
            "priority": self.priority, "version": self.version,
            "scope": self.scope,
            "pattern": self.pattern, "auto_fix": self.auto_fix,
            "tags": json.loads(self.tags) if self.tags else [],
            "allowed_roles": json.loads(self.allowed_roles) if self.allowed_roles else [],
            "group_id": self.group_id, "user_id": self.user_id, "project_id": self.project_id,
            "is_active": self.is_active, "access_count": self.access_count,
            "review_status": self.review_status,
            "review_report": self.review_report,
            "review_log": self.review_log,
            "promotion_status": self.promotion_status,
            "promotion_report": self.promotion_report,
            "promotion_source_id": self.promotion_source_id,
            "promotion_source_scope": self.promotion_source_scope,
            "promotion_promoted_at": self.promotion_promoted_at.isoformat() if self.promotion_promoted_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
        if include_content:
            data["content"] = self.content
        return data