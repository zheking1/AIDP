"""
Agents Module Models
Agent 数据库模型
Agent = Instructions + Skills + Rules + Knowledge
"""

import json
from typing import Optional, Dict, Any

from sqlalchemy import Column, String, Text, DateTime, Boolean, Float, ForeignKey, Integer, Table
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.core.utils import gen_uuid, utcnow


# Agent <-> Skill 关联表
agent_skills = Table(
    "aidp_agent_skills", Base.metadata,
    Column("agent_id", String(36), ForeignKey("aidp_agents.id", ondelete="CASCADE"), primary_key=True),
    Column("skill_id", String(36), ForeignKey("aidp_skills.id", ondelete="CASCADE"), primary_key=True),
)

# Agent <-> Rule 关联表
agent_rules = Table(
    "aidp_agent_rules", Base.metadata,
    Column("agent_id", String(36), ForeignKey("aidp_agents.id", ondelete="CASCADE"), primary_key=True),
    Column("rule_id", String(36), ForeignKey("aidp_rules.id", ondelete="CASCADE"), primary_key=True),
)

# Agent <-> KnowledgeBase 关联表
agent_knowledge = Table(
    "aidp_agent_knowledge", Base.metadata,
    Column("agent_id", String(36), ForeignKey("aidp_agents.id", ondelete="CASCADE"), primary_key=True),
    Column("knowledge_base_id", String(36), ForeignKey("aidp_knowledge_bases.id", ondelete="CASCADE"), primary_key=True),
)


class Agent(Base):
    """Agent 定义"""

    __tablename__ = "aidp_agents"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(200), nullable=False, index=True)
    role = Column(String(100), nullable=True)
    instructions = Column(Text, nullable=True)

    scope = Column(String(20), nullable=False, index=True, default="personal")
    # global / personal / project

    parent_agent_id = Column(String(36), ForeignKey("aidp_agents.id"), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("aidp_projects.id"), nullable=True, index=True)
    user_id = Column(String(100), nullable=True, index=True)

    config = Column(Text, default="{}")
    extra_data = Column(Text, default="{}")

    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, index=True)
    is_template = Column(Boolean, default=False, index=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # 关联
    parent = relationship("Agent", remote_side="Agent.id", back_populates="children")
    children = relationship("Agent", back_populates="parent")

    skills = relationship("Skill", secondary=agent_skills, lazy="selectin")
    rules = relationship("Rule", secondary=agent_rules, lazy="selectin")
    knowledge_bases = relationship("KnowledgeBase", secondary=agent_knowledge, lazy="selectin")

    def to_dict(self, include_relations: bool = False) -> Dict[str, Any]:
        data = {
            "id": self.id, "name": self.name, "role": self.role,
            "instructions": self.instructions,
            "scope": self.scope, "parent_agent_id": self.parent_agent_id,
            "project_id": self.project_id, "user_id": self.user_id,
            "config": json.loads(self.config) if self.config else {},
            "sort_order": self.sort_order, "is_active": self.is_active,
            "is_template": self.is_template,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
        if include_relations:
            data["skills"] = [{"id": s.id, "name": s.name} for s in self.skills] if self.skills else []
            data["rules"] = [{"id": r.id, "name": r.name} for r in self.rules] if self.rules else []
            data["knowledge_bases"] = [{"id": k.id, "name": k.name} for k in self.knowledge_bases] if self.knowledge_bases else []
        return data