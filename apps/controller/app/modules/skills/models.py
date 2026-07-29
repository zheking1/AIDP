"""
Skills Module Models
技能模块数据库模型 - 三层架构: global/personal/project
"""

import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    Column, String, Text, DateTime, Boolean, Float,
    ForeignKey, Integer, Index
)
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.core.utils import gen_uuid, utcnow


class SkillGroup(Base):
    """技能分组模型"""

    __tablename__ = "aidp_skill_groups"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    scope = Column(String(20), nullable=False, index=True, default="personal")
    parent_id = Column(String(36), ForeignKey("aidp_skill_groups.id"), nullable=True, index=True)

    user_id = Column(String(100), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("aidp_projects.id"), nullable=True, index=True)

    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    children = relationship("SkillGroup", back_populates="parent", cascade="all, delete-orphan")
    parent = relationship("SkillGroup", remote_side="SkillGroup.id", back_populates="children")
    skills = relationship("Skill", back_populates="group", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "description": self.description,
            "scope": self.scope, "parent_id": self.parent_id,
            "user_id": self.user_id, "project_id": self.project_id,
            "sort_order": self.sort_order,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Skill(Base):
    """技能模型"""

    __tablename__ = "aidp_skills"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)

    scope = Column(String(20), nullable=False, index=True, default="personal")

    instruction = Column(Text, nullable=True)
    content = Column(Text, nullable=True)

    tags = Column(Text, default="[]")
    version = Column(Integer, default=1)
    dependencies = Column(Text, default="[]")

    exec_config = Column(Text, default="{}")

    embedding = Column(Text, nullable=True)
    embedding_model = Column(String(128), default="text-embedding-3-small")

    review_status = Column(String(20), default="approved", index=True)
    review_report = Column(Text, nullable=True)
    review_log = Column(Text, default="[]")
    allow_risk_patterns = Column(Text, default="[]")
    allowed_roles = Column(Text, default="[]")
    sensitive = Column(Boolean, default=False)

    promotion_status = Column(String(20), default="none", index=True)
    # none / pending / reviewed / promoted / rejected / rolled_back
    promotion_report = Column(Text, nullable=True)
    promotion_source_id = Column(String(36), nullable=True, index=True)
    promotion_source_scope = Column(String(20), nullable=True)
    promotion_promoted_at = Column(DateTime(timezone=True), nullable=True)

    weight_config = Column(Text, default="{}")
    examples = Column(Text, default="[]")

    source_url = Column(String(500), nullable=True)
    source_type = Column(String(50), default="manual")
    source_id = Column(String(200), nullable=True)

    group_id = Column(String(36), ForeignKey("aidp_skill_groups.id"), nullable=True, index=True)
    user_id = Column(String(100), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("aidp_projects.id"), nullable=True, index=True)

    extra_data = Column(Text, default="{}")

    access_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    group = relationship("SkillGroup", back_populates="skills")
    files = relationship("SkillFile", back_populates="skill", cascade="all, delete-orphan")
    evolutions = relationship("SkillEvolution", back_populates="skill", cascade="all, delete-orphan")

    def to_dict(self, include_content: bool = False) -> Dict[str, Any]:
        data = {
            "id": self.id, "name": self.name, "description": self.description,
            "scope": self.scope, "tags": json.loads(self.tags) if self.tags else [],
            "version": self.version, "review_status": self.review_status,
            "allowed_roles": json.loads(self.allowed_roles) if self.allowed_roles else [],
            "sensitive": self.sensitive,
            "promotion_status": self.promotion_status,
            "promotion_report": self.promotion_report,
            "promotion_source_id": self.promotion_source_id,
            "promotion_source_scope": self.promotion_source_scope,
            "promotion_promoted_at": self.promotion_promoted_at.isoformat() if self.promotion_promoted_at else None,
            "source_type": self.source_type,
            "source_url": self.source_url, "source_id": self.source_id,
            "group_id": self.group_id,
            "user_id": self.user_id, "project_id": self.project_id,
            "access_count": self.access_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
        if include_content:
            data["instruction"] = self.instruction
            data["content"] = self.content
            data["exec_config"] = json.loads(self.exec_config) if self.exec_config else {}
            data["dependencies"] = json.loads(self.dependencies) if self.dependencies else []
            data["weight_config"] = json.loads(self.weight_config) if self.weight_config else {}
            data["examples"] = json.loads(self.examples) if self.examples else []
            data["review_report"] = self.review_report
            data["review_log"] = json.loads(self.review_log) if self.review_log else []
            data["allow_risk_patterns"] = json.loads(self.allow_risk_patterns) if self.allow_risk_patterns else []
            data["embedding_model"] = self.embedding_model
            data["extra_data"] = json.loads(self.extra_data) if self.extra_data else {}
        return data


class SkillFile(Base):
    """技能文件模型"""

    __tablename__ = "aidp_skill_files"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    skill_id = Column(String(36), ForeignKey("aidp_skills.id", ondelete="CASCADE"), nullable=False, index=True)
    path = Column(String(500), nullable=False)
    content = Column(Text, nullable=True)
    language = Column(String(50), nullable=True)
    is_entry = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    skill = relationship("Skill", back_populates="files")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "skill_id": self.skill_id, "path": self.path,
            "content": self.content, "language": self.language,
            "is_entry": self.is_entry, "sort_order": self.sort_order,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class SkillEvolution(Base):
    """技能版本演进"""

    __tablename__ = "aidp_skill_evolutions"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    skill_id = Column(String(36), ForeignKey("aidp_skills.id", ondelete="CASCADE"), nullable=False, index=True)
    old_version = Column(Integer, nullable=True)
    old_content = Column(Text, nullable=True)
    new_content = Column(Text, nullable=False)
    diff_summary = Column(Text, nullable=True)
    trigger_reason = Column(String(100), default="manual")
    status = Column(String(20), default="pending")
    rollback_to = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    skill = relationship("Skill", back_populates="evolutions")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "skill_id": self.skill_id, "old_version": self.old_version,
            "diff_summary": self.diff_summary, "trigger_reason": self.trigger_reason,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
