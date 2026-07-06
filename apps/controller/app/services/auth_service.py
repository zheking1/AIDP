"""
AIDP Unified Web UI - Authentication Service
Phase 1: Infrastructure
"""

import uuid
import secrets
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import bcrypt
import jwt
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import async_session_factory
from app.db.auth_models import (
    User, UserSession, LoginLog, UserRole, UserStatus, LoginAction,
    ApiKey
)

logger = logging.getLogger(__name__)

# JWT Configuration
JWT_SECRET_KEY = "your-secret-key-change-in-production"  # TODO: Move to config
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
JWT_REFRESH_TOKEN_EXPIRE_DAYS = 30  # 30 days

# Session Configuration
SESSION_COOKIE_NAME = "aidp_session"
SESSION_EXPIRE_HOURS = 24


class AuthService:
    """Authentication and authorization service"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify a password against its hash (supports bcrypt and pbkdf2_sha256)"""
        if password_hash.startswith('$2'):
            return bcrypt.checkpw(password.encode(), password_hash.encode())
        elif password_hash.startswith('pbkdf2_sha256$'):
            import hashlib, base64, hmac
            parts = password_hash.split('$')
            iterations = int(parts[1])
            salt_b64 = parts[2]
            hash_b64 = parts[3]
            # Add padding if needed
            salt_b64 += '=' * (4 - len(salt_b64) % 4) if len(salt_b64) % 4 else ''
            hash_b64 += '=' * (4 - len(hash_b64) % 4) if len(hash_b64) % 4 else ''
            salt = base64.b64decode(salt_b64)
            expected = base64.b64decode(hash_b64)
            dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, iterations)
            return hmac.compare_digest(dk, expected)
        return False
    
    @staticmethod
    def generate_session_token() -> str:
        """Generate a secure session token"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def generate_refresh_token() -> str:
        """Generate a refresh token"""
        return secrets.token_urlsafe(64)
    
    @classmethod
    async def authenticate_user(cls, username: str, password: str, ip_address: str = None, user_agent: str = None) -> Optional[User]:
        """
        Authenticate a user with username and password
        Returns the user if successful, None otherwise
        """
        async with async_session_factory() as session:
            # Find user by username or email
            result = await session.execute(
                select(User).where(
                    or_(
                        User.username == username,
                        User.email == username
                    )
                )
            )
            user = result.scalar_one_or_none()
            
            # Log the attempt
            success = False
            fail_reason = None
            
            if not user:
                fail_reason = "User not found"
            elif user.status != UserStatus.ACTIVE:
                fail_reason = f"Account is {user.status}"
            elif not cls.verify_password(password, user.password_hash):
                fail_reason = "Invalid password"
            else:
                success = True
                # Update last login
                user.last_login_at = datetime.utcnow()
                await session.commit()
            
            # Log the login attempt
            await cls._log_login_attempt(
                session=session,
                user_id=user.id if user else None,
                username=username,
                action=LoginAction.LOGIN,
                success=success,
                fail_reason=fail_reason,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            if success:
                logger.info(f"User {username} logged in successfully")
                return user
            else:
                logger.warning(f"Failed login attempt for {username}: {fail_reason}")
                return None
    
    @classmethod
    async def create_session(cls, user_id: uuid.UUID, ip_address: str = None, 
                            user_agent: str = None, remember_me: bool = False) -> UserSession:
        """Create a new user session"""
        async with async_session_factory() as session:
            expires_hours = SESSION_EXPIRE_HOURS * 7 if remember_me else SESSION_EXPIRE_HOURS
            
            user_session = UserSession(
                user_id=user_id,
                session_token=cls.generate_session_token(),
                refresh_token=cls.generate_refresh_token() if remember_me else None,
                ip_address=ip_address,
                user_agent=user_agent,
                expires_at=datetime.utcnow() + timedelta(hours=expires_hours)
            )
            
            session.add(user_session)
            await session.commit()
            await session.refresh(user_session)
            
            return user_session
    
    @classmethod
    async def validate_session(cls, session_token: str) -> Optional[User]:
        """Validate a session token and return the user"""
        if not session_token:
            return None
        
        async with async_session_factory() as session:
            result = await session.execute(
                select(UserSession).where(
                    and_(
                        UserSession.session_token == session_token,
                        UserSession.expires_at > datetime.utcnow()
                    )
                )
            )
            user_session = result.scalar_one_or_none()
            
            if user_session:
                # Update last activity
                user_session.last_activity_at = datetime.utcnow()
                await session.commit()
                
                # Get user
                result = await session.execute(
                    select(User).where(User.id == user_session.user_id)
                )
                user = result.scalar_one_or_none()
                
                if user and user.status == UserStatus.ACTIVE:
                    return user
            
            return None
    
    @classmethod
    async def logout(cls, session_token: str) -> bool:
        """Logout a user by invalidating their session"""
        async with async_session_factory() as session:
            result = await session.execute(
                select(UserSession).where(UserSession.session_token == session_token)
            )
            user_session = result.scalar_one_or_none()
            
            if user_session:
                # Log the logout
                await cls._log_login_attempt(
                    session=session,
                    user_id=user_session.user_id,
                    username=None,
                    action=LoginAction.LOGOUT,
                    success=True,
                    ip_address=None,
                    user_agent=None
                )
                
                # Delete the session
                await session.delete(user_session)
                await session.commit()
                return True
            
            return False
    
    @classmethod
    async def logout_all_devices(cls, user_id: uuid.UUID) -> int:
        """Logout a user from all devices"""
        async with async_session_factory() as session:
            result = await session.execute(
                select(UserSession).where(UserSession.user_id == user_id)
            )
            sessions = result.scalars().all()
            
            count = len(sessions)
            for user_session in sessions:
                await session.delete(user_session)
            
            await session.commit()
            logger.info(f"User {user_id} logged out from {count} devices")
            return count
    
    @classmethod
    async def create_user(cls, username: str, password: str, email: str = None,
                         nickname: str = None, role: UserRole = UserRole.USER,
                         created_by: uuid.UUID = None) -> Optional[User]:
        """Create a new user"""
        async with async_session_factory() as session:
            # Check if username exists
            result = await session.execute(
                select(User).where(User.username == username)
            )
            if result.scalar_one_or_none():
                raise ValueError(f"Username '{username}' already exists")
            
            # Check if email exists (if provided)
            if email:
                result = await session.execute(
                    select(User).where(User.email == email)
                )
                if result.scalar_one_or_none():
                    raise ValueError(f"Email '{email}' already exists")
            
            # Create user
            user = User(
                username=username,
                password_hash=cls.hash_password(password),
                email=email,
                nickname=nickname or username,
                role=role,
                status=UserStatus.ACTIVE,
                is_verified=True
            )
            
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            logger.info(f"User {username} created with role {role.value}")
            return user
    
    @classmethod
    async def change_password(cls, user_id: uuid.UUID, old_password: str, 
                              new_password: str) -> bool:
        """Change user password"""
        async with async_session_factory() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return False
            
            if not cls.verify_password(old_password, user.password_hash):
                return False
            
            user.password_hash = cls.hash_password(new_password)
            await session.commit()
            
            # Log password change
            await cls._log_login_attempt(
                session=session,
                user_id=user_id,
                username=user.username,
                action=LoginAction.PASSWORD_CHANGED,
                success=True
            )
            
            logger.info(f"Password changed for user {user.username}")
            return True
    
    @classmethod
    async def reset_password(cls, user_id: uuid.UUID, new_password: str) -> bool:
        """Reset user password (admin only)"""
        async with async_session_factory() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return False
            
            user.password_hash = cls.hash_password(new_password)
            await session.commit()
            
            logger.info(f"Password reset for user {user.username}")
            return True
    
    @classmethod
    async def toggle_user_status(cls, user_id: uuid.UUID, active: bool) -> bool:
        """Enable or disable a user account"""
        async with async_session_factory() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return False
            
            user.status = UserStatus.ACTIVE if active else UserStatus.INACTIVE
            await session.commit()
            
            if not active:
                # Logout from all devices if disabled
                await cls.logout_all_devices(user_id)
            
            logger.info(f"User {user.username} status changed to {user.status}")
            return True
    
    # ============================================================================
    # API Key Management
    # ============================================================================
    
    @classmethod
    async def create_api_key(cls, user_id: uuid.UUID, label: str = None,
                            scopes: list = None, expires_days: int = None) -> tuple:
        """
        Create a new API key for a user
        Returns: (api_key_object, raw_key_string)
        """
        async with async_session_factory() as session:
            # Generate key
            raw_key = "aidp_" + secrets.token_hex(32)
            key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
            key_preview = raw_key[:12] + "..."
            
            api_key = ApiKey(
                user_id=user_id,
                label=label or "Default",
                key_hash=key_hash,
                key_preview=key_preview,
                scopes=scopes or ["read"],
                expires_at=datetime.utcnow() + timedelta(days=expires_days) if expires_days else None
            )
            
            session.add(api_key)
            await session.commit()
            await session.refresh(api_key)
            
            return api_key, raw_key
    
    @classmethod
    async def validate_api_key(cls, key: str) -> Optional[User]:
        """Validate an API key and return the user"""
        if not key or not key.startswith("aidp_"):
            return None
        
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        
        async with async_session_factory() as session:
            result = await session.execute(
                select(ApiKey).where(
                    and_(
                        ApiKey.key_hash == key_hash,
                        ApiKey.is_active == True,
                        or_(
                            ApiKey.expires_at.is_(None),
                            ApiKey.expires_at > datetime.utcnow()
                        )
                    )
                )
            )
            api_key = result.scalar_one_or_none()
            
            if api_key:
                # Update last used
                api_key.last_used_at = datetime.utcnow()
                await session.commit()
                
                # Get user
                result = await session.execute(
                    select(User).where(User.id == api_key.user_id)
                )
                return result.scalar_one_or_none()
            
            return None
    
    @classmethod
    async def revoke_api_key(cls, key_id: uuid.UUID, user_id: uuid.UUID = None) -> bool:
        """Revoke an API key"""
        async with async_session_factory() as session:
            query = select(ApiKey).where(ApiKey.id == key_id)
            if user_id:
                query = query.where(ApiKey.user_id == user_id)
            
            result = await session.execute(query)
            api_key = result.scalar_one_or_none()
            
            if api_key:
                api_key.is_active = False
                await session.commit()
                return True
            
            return False
    
    # ============================================================================
    # Helper Methods
    # ============================================================================
    
    @staticmethod
    async def _log_login_attempt(session: AsyncSession, user_id: uuid.UUID = None,
                                 username: str = None, action: LoginAction = None,
                                 success: bool = False, fail_reason: str = None,
                                 ip_address: str = None, user_agent: str = None):
        """Log a login attempt to the database"""
        log = LoginLog(
            user_id=user_id,
            username=username,
            action=action,
            success=success,
            fail_reason=fail_reason,
            ip_address=ip_address,
            user_agent=user_agent
        )
        session.add(log)
        await session.commit()


# ============================================================================
# Permission Checking
# ============================================================================

class PermissionService:
    """Permission checking service"""
    
    ROLE_HIERARCHY = {
        UserRole.SUPER_ADMIN: 5,
        UserRole.ADMIN: 4,
        UserRole.DEVELOPER: 3,
        UserRole.USER: 2,
        UserRole.READONLY: 1,
    }
    
    @classmethod
    def has_role(cls, user: User, min_role: UserRole) -> bool:
        """Check if user has at least the specified role level"""
        if not user:
            return False
        user_level = cls.ROLE_HIERARCHY.get(user.role, 0)
        min_level = cls.ROLE_HIERARCHY.get(min_role, 0)
        return user_level >= min_level
    
    @classmethod
    def is_admin(cls, user: User) -> bool:
        """Check if user is an admin"""
        return user and user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]
    
    @classmethod
    def is_super_admin(cls, user: User) -> bool:
        """Check if user is a super admin"""
        return user and user.role == UserRole.SUPER_ADMIN
