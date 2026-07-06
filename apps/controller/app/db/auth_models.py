"""
AIDP Unified Web UI - Authentication and Authorization Models
Phase 1: Infrastructure
"""

import uuid
import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, String, Text, DateTime, Boolean, JSON, 
    ForeignKey, Integer, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship

from app.db.database import Base


# ============================================================================
# Enums
# ============================================================================

class UserRole(str, PyEnum):
    """User roles hierarchy"""
    SUPER_ADMIN = "super_admin"  # Full system access
    ADMIN = "admin"              # Manage users, settings
    DEVELOPER = "developer"      # Create/edit skills/tools
    USER = "user"                # Use tools
    READONLY = "readonly"        # View only


class UserStatus(str, PyEnum):
    """User account status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class LoginAction(str, PyEnum):
    """Login log actions"""
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    TOKEN_REFRESH = "token_refresh"
    PASSWORD_CHANGED = "password_changed"


# ============================================================================
# Core Models
# ============================================================================

class User(Base):
    """User account model"""
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=True, index=True)
    nickname = Column(String(128), nullable=True)
    avatar_url = Column(Text, nullable=True)
    
    # Role and status (stored as varchar in DB, enum validation in service layer)
    role = Column(String(32), default=UserRole.USER.value, nullable=False)
    status = Column(String(32), default=UserStatus.ACTIVE.value, nullable=False)
    is_verified = Column(Boolean, default=False)
    
    # Timestamps
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"
    
    def to_dict(self, include_sensitive=False):
        """Convert to dictionary"""
        data = {
            "id": str(self.id),
            "username": self.username,
            "email": self.email,
            "nickname": self.nickname,
            "avatar_url": self.avatar_url,
            "role": self.role if self.role else None,
            "status": self.status if self.status else None,
            "is_verified": self.is_verified,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_sensitive:
            data["password_hash"] = self.password_hash
        return data


class UserSession(Base):
    """User session for web login (supports multiple devices)"""
    __tablename__ = "user_sessions"
    __table_args__ = {'extend_existing': True}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Session tokens
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    refresh_token = Column(String(255), nullable=True)
    
    # Session info
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    
    # Expiration
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_activity_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id})>"
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_activity_at": self.last_activity_at.isoformat() if self.last_activity_at else None,
        }


class LoginLog(Base):
    """Login history for security audit"""
    __tablename__ = "login_logs"
    __table_args__ = {'extend_existing': True}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    username = Column(String(64), nullable=True)  # Attempted username
    
    action = Column(String(32), nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    success = Column(Boolean, default=False)
    fail_reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    user = relationship("User")
    
    def __repr__(self):
        return f"<LoginLog(id={self.id}, username={self.username}, action={self.action})>"
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "username": self.username,
            "action": self.action.value if self.action else None,
            "ip_address": self.ip_address,
            "success": self.success,
            "fail_reason": self.fail_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ============================================================================
# Permission Models
# ============================================================================

class Permission(Base):
    """Permission definitions"""
    __tablename__ = "permissions"
    __table_args__ = {'extend_existing': True}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(64), unique=True, nullable=False, index=True)  # e.g., "tool:read", "user:write"
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    
    # Resource categorization
    resource_type = Column(String(32), nullable=True)  # tool, user, model, etc.
    action = Column(String(32), nullable=True)  # read, write, delete, execute
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f"<Permission(id={self.id}, code={self.code})>"
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "resource_type": self.resource_type,
            "action": self.action,
        }


class RolePermission(Base):
    """Many-to-many: Roles <-> Permissions"""
    __tablename__ = "role_permissions"
    __table_args__ = {'extend_existing': True}
    
    role = Column(String(32), primary_key=True)  # UserRole value
    permission_id = Column(UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)
    
    def __repr__(self):
        return f"<RolePermission(role={self.role}, permission_id={self.permission_id})>"


# ============================================================================
# API Key Model
# ============================================================================

class ApiKey(Base):
    """API keys for programmatic access"""
    __tablename__ = "api_keys"
    __table_args__ = {'extend_existing': True}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    label = Column(String(128), nullable=True)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)  # SHA256 of the key
    key_preview = Column(String(20), nullable=True)  # First few chars for display
    
    scopes = Column(JSON, default=list)  # ["read", "write"]
    rate_limit_req_per_min = Column(Integer, default=60)
    
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    
    def __repr__(self):
        return f"<ApiKey(id={self.id}, user_id={self.user_id}, label={self.label})>"
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "label": self.label,
            "key_preview": self.key_preview,
            "scopes": self.scopes,
            "rate_limit_req_per_min": self.rate_limit_req_per_min,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ============================================================================
# Audit Log Model
# ============================================================================

class AuditLog(Base):
    """Audit trail for all important operations"""
    __tablename__ = "audit_logs"
    __table_args__ = {'extend_existing': True}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    
    action = Column(String(64), nullable=False, index=True)  # CREATE, UPDATE, DELETE, LOGIN, etc.
    resource_type = Column(String(64), nullable=True, index=True)  # user, model, tool, etc.
    resource_id = Column(String(64), nullable=True, index=True)
    resource_name = Column(String(255), nullable=True)  # Redundant for easy querying
    
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, resource_type={self.resource_type})>"
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "resource_name": self.resource_name,
            "old_values": self.old_values,
            "new_values": self.new_values,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ============================================================================
# System Settings Model
# ============================================================================

class SystemSetting(Base):
    """Key-value store for system configuration"""
    __tablename__ = "system_settings"
    __table_args__ = {'extend_existing': True}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(128), unique=True, nullable=False, index=True)
    value = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)
    is_encrypted = Column(Boolean, default=False)
    
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f"<SystemSetting(key={self.key})>"
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "key": self.key,
            "value": self.value,
            "description": self.description,
            "is_encrypted": self.is_encrypted,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ============================================================================
# Indexes
# ============================================================================

# Additional indexes defined in table definitions above
# Composite indexes for common query patterns
Index("idx_audit_logs_user_action", AuditLog.user_id, AuditLog.action)
Index("idx_audit_logs_resource", AuditLog.resource_type, AuditLog.resource_id)
Index("idx_audit_logs_created", AuditLog.created_at)
