"""
Agents Module Models
Agent = 领域专家身份模板, LLM 根据技术栈自动生成
管线 Agent 匹配: intent.domains → agent.domain_tags → 加载专用 instructions
"""

import json
from typing import Optional, Dict, Any

from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.core.utils import gen_uuid, utcnow


class Agent(Base):
    __tablename__ = "aidp_agents"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(200), nullable=False, index=True)
    agent_key = Column(String(100), unique=True, nullable=False, index=True)

    role = Column(Text, nullable=True)
    instructions = Column(Text, nullable=True)
    domain_tags = Column(Text, default="[]")

    scope = Column(String(20), nullable=False, index=True, default="project")
    project_id = Column(Integer, nullable=True, index=True)
    user_id = Column(String(100), nullable=True, index=True)

    source = Column(String(20), default="auto")
    source_version = Column(Text, nullable=True)

    config = Column(Text, default="{}")
    is_active = Column(Boolean, default=True, index=True)
    is_template = Column(Boolean, default=False, index=True)
    sort_order = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "agent_key": self.agent_key,
            "role": self.role,
            "instructions": self.instructions,
            "domain_tags": json.loads(self.domain_tags) if self.domain_tags else [],
            "scope": self.scope,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "source": self.source,
            "source_version": self.source_version,
            "is_active": self.is_active,
            "is_template": self.is_template,
            "sort_order": self.sort_order,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }