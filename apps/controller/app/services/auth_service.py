import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User


class AuthService:
    """认证服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    def hash_password(self, password: str) -> str:
        """哈希密码"""
        return hashlib.sha256(password.encode()).hexdigest()

    def verify_password(self, password: str, password_hash: str) -> bool:
        """验证密码"""
        return self.hash_password(password) == password_hash

    async def authenticate(self, username: str, password: str) -> Optional[User]:
        """认证用户"""
        result = await self.db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

        if user and self.verify_password(password, user.password_hash):
            return user
        return None

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """根据 ID 获取用户"""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def create_user(self, username: str, password: str, role: str = "user") -> User:
        """创建用户"""
        user = User(
            username=username,
            password_hash=self.hash_password(password),
            role=role
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def list_users(self):
        """获取用户列表"""
        result = await self.db.execute(select(User))
        return result.scalars().all()
