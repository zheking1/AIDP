from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.project import ProjectMember


class PermissionChecker:
    def __init__(self, db: AsyncSession, current_user: Optional[User] = None):
        self.db = db
        self.current_user = current_user

    async def is_admin(self) -> bool:
        if not self.current_user:
            return False
        return self.current_user.role == "admin"

    async def is_owner(self, user_id: int, project_id: int) -> bool:
        result = await self.db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
                ProjectMember.role == "owner"
            )
        )
        return result.scalar_one_or_none() is not None

    async def is_member(self, user_id: int, project_id: int) -> bool:
        result = await self.db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_project_role(self, user_id: int, project_id: int) -> Optional[str]:
        result = await self.db.execute(
            select(ProjectMember.role).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def can_manage_project(self, user_id: int, project_id: int) -> bool:
        if await self.is_admin():
            return True
        role = await self.get_project_role(user_id, project_id)
        return role in ["owner", "member"]

    async def can_view_project(self, user_id: int, project_id: int) -> bool:
        if await self.is_admin():
            return True
        return await self.is_member(user_id, project_id)

    async def can_modify_document(self, user_id: int, document: dict) -> bool:
        if await self.is_admin():
            return True
        owner_type = document.get("owner_type")
        owner_id = document.get("owner_id")
        if owner_type == "system":
            return False
        elif owner_type == "personal":
            return owner_id == user_id
        elif owner_type == "project":
            return await self.is_member(user_id, owner_id)
        return False
