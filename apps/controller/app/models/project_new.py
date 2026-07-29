"""
Project Database Models
Define project and project member SQLAlchemy models
"""

from datetime import datetime
from typing import Optional, List
import json

from sqlalchemy import (
    Column, Integer, String, Text, DateTime,
    ForeignKey, Enum, Table, UniqueConstraint
)
from sqlalchemy.orm import relationship
import enum

from app.db.database import Base


class ProjectVisibility(str, enum.Enum):
    PRIVATE = "private"
    INTERNAL = "internal"
    PUBLIC = "public"


class ProjectRole(str, enum.Enum):
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class Project(Base):
    __tablename__ = "aidp_projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    visibility = Column(String(20), default="private")
    owner_id = Column(String(100), nullable=True, index=True)
    status = Column(String(20), default="active", index=True)
    tech_stack = Column(Text, nullable=True)  # JSON array stored as string

    settings = relationship("app.models.project_new.ProjectSettings", uselist=False, back_populates="project", cascade="all, delete-orphan")
    members = relationship("app.models.project_new.ProjectMember", back_populates="project", cascade="all, delete-orphan")
    access_logs = relationship("app.models.project_new.ProjectAccessLog", back_populates="project", cascade="all, delete-orphan")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "visibility": self.visibility,
            "owner_id": self.owner_id,
            "status": self.status,
            "tech_stack": json.loads(self.tech_stack) if self.tech_stack else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "cover_url": None,
            "member_count": 0,
        }


class ProjectMember(Base):
    __tablename__ = "aidp_project_members"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("aidp_projects.id"), nullable=False, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    role = Column(String(20), default="viewer")
    invited_by = Column(String(100), nullable=True)
    joined_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("app.models.project_new.Project", back_populates="members")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "role": self.role,
            "invited_by": self.invited_by,
            "joined_at": self.joined_at.isoformat() if self.joined_at else None,
        }


class ProjectSettings(Base):
    __tablename__ = "aidp_project_settings"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("aidp_projects.id"), nullable=False, unique=True, index=True)
    instructions = Column(Text, nullable=True)
    config = Column(Text, nullable=True)
    integrations = Column(Text, nullable=True)

    project = relationship("app.models.project_new.Project", back_populates="settings")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "instructions": self.instructions,
            "config": self.config,
            "integrations": self.integrations,
        }


class ProjectAccessLog(Base):
    __tablename__ = "aidp_project_access_logs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("aidp_projects.id"), nullable=False, index=True)
    user_id = Column(String(100), nullable=True)
    action = Column(String(50), nullable=False)
    detail = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    project = relationship("app.models.project_new.Project", back_populates="access_logs")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "action": self.action,
            "detail": self.detail,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ProjectMapping(Base):
    """项目 ID 映射表 — 统一 controller/code-index/skillrouter 等工具的项目 ID"""
    __tablename__ = "aidp_project_mappings"

    id = Column(Integer, primary_key=True, index=True)
    controller_project_id = Column(Integer, ForeignKey("aidp_projects.id"), nullable=False, index=True)
    tool_name = Column(String(64), nullable=False)  # code-index / skillrouter / knowledge-tool
    tool_project_id = Column(String(128), nullable=False)  # 工具内部的 project_id
    local_path = Column(String(1024), nullable=True)  # 本地项目路径
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "controller_project_id": self.controller_project_id,
            "tool_name": self.tool_name,
            "tool_project_id": self.tool_project_id,
            "local_path": self.local_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


INIT_TASKS = [
    {"id": "code_index",    "name": "代码索引",     "phase": 1, "depends_on": []},
    {"id": "doc_import",    "name": "文档导入",     "phase": 2, "depends_on": ["code_index"]},
    {"id": "tech_analysis", "name": "技术栈分析",   "phase": 1, "depends_on": []},
    {"id": "official_docs", "name": "官方文档导入", "phase": 2, "depends_on": ["tech_analysis"]},
    {"id": "file_watcher",  "name": "文件监听安装", "phase": 3, "depends_on": []},
    {"id": "git_hook",      "name": "Git 钩子安装", "phase": 3, "depends_on": []},
    {"id": "rules_extract", "name": "规则提取",     "phase": 2, "depends_on": ["doc_import"]},
    {"id": "agent_setup",   "name": "Agent 创建",   "phase": 2, "depends_on": []},
    {"id": "mcp_register",  "name": "MCP 注册检查", "phase": 1, "depends_on": []},
]

INIT_TASK_IDS = [t["id"] for t in INIT_TASKS]


class ProjectInitTask(Base):
    """项目初始化任务跟踪"""
    __tablename__ = "aidp_project_init_tasks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("aidp_projects.id"), nullable=False, index=True)
    task_id = Column(String(64), nullable=False)  # code_index / doc_import / ...
    status = Column(String(20), default="pending")  # pending / running / completed / skipped / failed
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_msg = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)  # JSON

    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        task_def = next((t for t in INIT_TASKS if t["id"] == self.task_id), {})
        return {
            "id": self.id,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "name": task_def.get("name", self.task_id),
            "phase": task_def.get("phase", 0),
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_msg": self.error_msg,
            "metadata": json.loads(self.metadata_json) if self.metadata_json else {},
        }