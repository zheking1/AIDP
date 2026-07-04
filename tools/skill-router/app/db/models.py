import uuid
from datetime import datetime
from enum import Enum

from pgvector.sqlalchemy import Vector
from sqlalchemy import BOOLEAN, Column, DateTime, ForeignKey, Integer, JSON, Text, VARCHAR, Float, ARRAY, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, relationship


ROLES = ['super_admin', 'admin', 'developer', 'user', 'readonly']
LLM_ROLES = ['Intent Analyzer', 'Embedding', 'Review', 'Ranker']


class RoleEnum(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    DEVELOPER = "developer"
    USER = "user"
    READONLY = "readonly"


class LLMRoleEnum(str, Enum):
    INTENT_ANALYZER = "Intent Analyzer"
    EMBEDDING = "Embedding"
    REVIEW = "Review"
    RANKER = "Ranker"


class Base(DeclarativeBase):
    def to_dict(self):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        for k, v in d.items():
            if isinstance(v, uuid.UUID):
                d[k] = str(v)
            elif isinstance(v, datetime):
                d[k] = v.isoformat() if v else None
            elif hasattr(v, 'tolist'):
                d[k] = v.tolist()
        return d


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(VARCHAR(100), unique=True, nullable=False)
    password = Column(VARCHAR(255), nullable=False)
    nickname = Column(VARCHAR(100), default="")
    remark = Column(Text, default="")
    role = Column(VARCHAR(20), default="admin")
    is_active = Column(BOOLEAN, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("role IN ('super_admin', 'admin', 'developer', 'user', 'readonly')", name="check_user_role"),
    )

    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    skill_groups = relationship("SkillGroup", back_populates="user", cascade="all, delete-orphan")
    rule_groups = relationship("RuleGroup", back_populates="user", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    name = Column(VARCHAR(255), nullable=False)
    slug = Column(VARCHAR(255), nullable=False, unique=True)
    title = Column(VARCHAR(255), nullable=False)
    status = Column(VARCHAR(50), default="active")
    description = Column(Text)
    instruction = Column(Text, default=None)
    config = Column(JSON, default=dict)
    settings = Column(JSONB, default=dict)
    workspace_id = Column(UUID(as_uuid=True), nullable=True)
    is_active = Column(BOOLEAN, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="projects")
    skills = relationship("Skill", back_populates="project")
    rules = relationship("Rule", back_populates="project")
    llm_configs = relationship("LLMConfig", back_populates="project")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    key_hash = Column(VARCHAR(64), unique=True, nullable=False)
    label = Column(VARCHAR(100))
    last_used = Column(DateTime)
    is_active = Column(BOOLEAN, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="api_keys")


class SkillGroup(Base):
    __tablename__ = "skill_groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(VARCHAR(255), nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("skill_groups.id"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="skill_groups")
    parent = relationship("SkillGroup", remote_side="SkillGroup.id", back_populates="children")
    children = relationship("SkillGroup", back_populates="parent", order_by="SkillGroup.sort_order")
    skills = relationship("Skill", back_populates="group")


class Skill(Base):
    __tablename__ = "skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(VARCHAR(255), nullable=False)
    description = Column(Text)
    instruction = Column(Text, default=None)
    content = Column(Text, nullable=False)
    tags = Column(ARRAY(VARCHAR), default=list)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    version = Column(Integer, default=1)
    dependencies = Column(ARRAY(UUID(as_uuid=True)), default=list)
    exec_config = Column(JSON, default=None)
    embedding = Column(Vector(384))
    review_status = Column(VARCHAR(20), default="pending")
    review_report = Column(Text)
    review_log = Column(ARRAY(Text), default=list)
    allow_risk_patterns = Column(ARRAY(Text), default=list)
    scope = Column(VARCHAR(20), default="private")
    allowed_roles = Column(ARRAY(VARCHAR), default=None)
    sensitive = Column(BOOLEAN, default=False)
    weight_config = Column(JSONB, default=None)
    is_active = Column(BOOLEAN, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)
    project = relationship("Project", back_populates="skills")

    group_id = Column(UUID(as_uuid=True), ForeignKey("skill_groups.id"), nullable=True)
    group = relationship("SkillGroup", back_populates="skills")

    source_url = Column(VARCHAR(500), nullable=True)
    source_type = Column(VARCHAR(20), nullable=True)  # github, clawhub
    source_id = Column(VARCHAR(255), nullable=True)    # owner/repo/path or slug

    files = relationship("SkillFile", back_populates="skill", cascade="all, delete-orphan", order_by="SkillFile.sort_order")
    permissions = relationship("SkillPermission", back_populates="skill", cascade="all, delete-orphan")
    
    examples = Column(ARRAY(Text), default=list)

    def to_dict(self, include_files=True):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        for k, v in d.items():
            if isinstance(v, uuid.UUID):
                d[k] = str(v)
            elif isinstance(v, datetime):
                d[k] = v.isoformat() if v else None
            elif hasattr(v, 'tolist'):
                d[k] = v.tolist()
        if include_files:
            try:
                d["files"] = [f.to_dict() for f in self.files]
            except Exception:
                d["files"] = []
        return d


class SkillFile(Base):
    __tablename__ = "skill_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False)
    path = Column(VARCHAR(500), nullable=False)
    content = Column(Text, nullable=False)
    language = Column(VARCHAR(20), default="text")
    is_entry = Column(BOOLEAN, default=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    skill = relationship("Skill", back_populates="files")


class RuleGroup(Base):
    __tablename__ = "rule_groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(VARCHAR(255), nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("rule_groups.id"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="rule_groups")
    parent = relationship("RuleGroup", remote_side="RuleGroup.id", back_populates="children")
    children = relationship("RuleGroup", back_populates="parent", order_by="RuleGroup.sort_order")
    rules = relationship("Rule", back_populates="group")


class Rule(Base):
    __tablename__ = "rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(VARCHAR(255), nullable=False)
    content = Column(Text, nullable=False)
    tags = Column(ARRAY(VARCHAR), default=list)
    priority = Column(Integer, default=0)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    embedding = Column(Vector(384))
    version = Column(Integer, default=1)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)
    project = relationship("Project", back_populates="rules")

    group_id = Column(UUID(as_uuid=True), ForeignKey("rule_groups.id"), nullable=True)
    group = relationship("RuleGroup", back_populates="rules")

    scope = Column(VARCHAR(20), default="private")
    allowed_roles = Column(ARRAY(VARCHAR), default=None)
    is_active = Column(BOOLEAN, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Evolution(Base):
    __tablename__ = "evolutions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_type = Column(VARCHAR(10), nullable=False)
    target_id = Column(UUID(as_uuid=True), nullable=False)
    target_name = Column(VARCHAR(255), nullable=False)
    old_version = Column(Integer, nullable=False)
    old_content = Column(Text, nullable=False)
    new_content = Column(Text, nullable=False)
    diff_summary = Column(Text)
    trigger_reason = Column(Text, nullable=False)
    status = Column(VARCHAR(20), default="applied")
    applied_by = Column(VARCHAR(100), default="local")
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    rollback_to = Column(UUID(as_uuid=True), ForeignKey("evolutions.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    applied_at = Column(DateTime)


class LLMConfig(Base):
    __tablename__ = "llm_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(VARCHAR(100), nullable=False)
    endpoint = Column(VARCHAR(500), nullable=False)
    api_key = Column(VARCHAR(500), nullable=False)
    model_name = Column(VARCHAR(100))
    role = Column(VARCHAR(50))
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=2048)
    timeout_secs = Column(Integer, default=30)
    is_healthy = Column(BOOLEAN, default=True)
    is_default = Column(BOOLEAN, default=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)
    project = relationship("Project", back_populates="llm_configs")
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("role IN ('Intent Analyzer', 'Embedding', 'Review', 'Ranker')", name="check_llm_role"),
    )


class SkillPermission(Base):
    __tablename__ = "skill_permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False)
    allowed_roles = Column(ARRAY(VARCHAR), default=None)
    denied_roles = Column(ARRAY(VARCHAR), default=None)
    created_at = Column(DateTime, default=datetime.utcnow)

    skill = relationship("Skill", back_populates="permissions")


class ReviewPattern(Base):
    __tablename__ = "review_patterns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(VARCHAR(100), nullable=False)
    pattern = Column(VARCHAR(500), nullable=False)
    risk_level = Column(VARCHAR(20), default="high")
    is_active = Column(BOOLEAN, default=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    resource_type = Column(VARCHAR(50), nullable=False)
    resource_id = Column(UUID(as_uuid=True))
    action = Column(VARCHAR(50), nullable=False)
    detail = Column(JSON)
    trace_id = Column(VARCHAR(64))
    created_at = Column(DateTime, default=datetime.utcnow)


class ResolveCache(Base):
    __tablename__ = "resolve_cache"

    key_hash = Column(VARCHAR(64), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    task_hash = Column(VARCHAR(64), nullable=False)
    result = Column(JSON, nullable=False)
    ttl_seconds = Column(Integer, default=3600)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
