"""
Workflows Module Models
流程引擎数据库模型
"""

import json
from typing import Optional, Dict, Any

from sqlalchemy import Column, String, Text, DateTime, Boolean, Float, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.core.utils import gen_uuid, utcnow


class Workflow(Base):
    """流程定义"""

    __tablename__ = "aidp_workflows"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)

    category = Column(String(50), default="development", index=True)
    # development / testing / deployment / review

    trigger = Column(String(50), default="manual", index=True)
    # manual / webhook / schedule / event

    trigger_config = Column(Text, default="{}")
    variables = Column(Text, default="[]")
    extra_data = Column(Text, default="{}")

    project_id = Column(Integer, ForeignKey("aidp_projects.id"), nullable=True, index=True)
    user_id = Column(String(100), nullable=True, index=True)

    is_active = Column(Boolean, default=True, index=True)
    is_template = Column(Boolean, default=False, index=True)
    version = Column(Integer, default=1)

    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    steps = relationship("WorkflowStep", back_populates="workflow", cascade="all, delete-orphan", order_by="WorkflowStep.order")

    def to_dict(self, include_steps: bool = False) -> Dict[str, Any]:
        data = {
            "id": self.id, "name": self.name, "description": self.description,
            "category": self.category, "trigger": self.trigger,
            "trigger_config": json.loads(self.trigger_config) if self.trigger_config else {},
            "variables": json.loads(self.variables) if self.variables else [],
            "project_id": self.project_id, "user_id": self.user_id,
            "is_active": self.is_active, "is_template": self.is_template,
            "version": self.version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
        if include_steps:
            data["steps"] = [s.to_dict() for s in self.steps] if self.steps else []
        return data


class WorkflowStep(Base):
    """流程步骤"""

    __tablename__ = "aidp_workflow_steps"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    workflow_id = Column(String(36), ForeignKey("aidp_workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    order = Column(Integer, nullable=False)

    agent_id = Column(String(36), ForeignKey("aidp_agents.id"), nullable=True)
    skill_ids = Column(Text, default="[]")
    rule_ids = Column(Text, default="[]")

    conditions = Column(Text, default="{}")
    input_mapping = Column(Text, default="{}")
    output_mapping = Column(Text, default="{}")

    timeout = Column(Integer, default=300)
    on_success = Column(Text, default="{}")
    on_fail = Column(Text, default="{}")

    extra_data = Column(Text, default="{}")
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    workflow = relationship("Workflow", back_populates="steps")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "workflow_id": self.workflow_id, "name": self.name,
            "order": self.order, "agent_id": self.agent_id,
            "skill_ids": json.loads(self.skill_ids) if self.skill_ids else [],
            "rule_ids": json.loads(self.rule_ids) if self.rule_ids else [],
            "conditions": json.loads(self.conditions) if self.conditions else {},
            "input_mapping": json.loads(self.input_mapping) if self.input_mapping else {},
            "output_mapping": json.loads(self.output_mapping) if self.output_mapping else {},
            "timeout": self.timeout,
            "on_success": json.loads(self.on_success) if self.on_success else {},
            "on_fail": json.loads(self.on_fail) if self.on_fail else {},
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class WorkflowExecution(Base):
    """流程执行记录"""

    __tablename__ = "aidp_workflow_executions"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    workflow_id = Column(String(36), ForeignKey("aidp_workflows.id"), nullable=False, index=True)
    status = Column(String(20), default="running", index=True)
    # running / completed / failed / cancelled

    trigger_type = Column(String(50), default="manual")
    trigger_data = Column(Text, default="{}")

    current_step = Column(Integer, default=0)
    variables = Column(Text, default="{}")

    started_at = Column(DateTime(timezone=True), default=utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    workflow = relationship("Workflow")
    step_records = relationship("WorkflowExecutionStep", back_populates="execution", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "workflow_id": self.workflow_id, "status": self.status,
            "trigger_type": self.trigger_type, "current_step": self.current_step,
            "variables": json.loads(self.variables) if self.variables else {},
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "step_records": [s.to_dict() for s in self.step_records] if self.step_records else []
        }


class WorkflowExecutionStep(Base):
    """流程步骤执行记录"""

    __tablename__ = "aidp_workflow_execution_steps"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    execution_id = Column(String(36), ForeignKey("aidp_workflow_executions.id"), nullable=False, index=True)
    step_id = Column(String(36), ForeignKey("aidp_workflow_steps.id"), nullable=True)
    step_name = Column(String(200), nullable=True)
    step_order = Column(Integer, nullable=True)

    status = Column(String(20), default="pending")
    # pending / running / completed / failed / skipped

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)

    input_data = Column(Text, default="{}")
    output_data = Column(Text, default="{}")
    error = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), default=utcnow)

    execution = relationship("WorkflowExecution", back_populates="step_records")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "execution_id": self.execution_id, "step_id": self.step_id,
            "step_name": self.step_name, "step_order": self.step_order,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms, "error": self.error, "retry_count": self.retry_count
        }