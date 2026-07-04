from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.project import Project, ProjectMember


class ProjectService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_project(self, name: str, description: str, project_type: str, owner_id: str) -> Project:
        project = Project(name=name, description=description, project_type=project_type, owner_id=owner_id)
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        member = ProjectMember(project_id=project.id, user_id=owner_id, role="owner")
        self.db.add(member)
        await self.db.commit()
        return project

    async def get_project(self, project_id: int) -> Optional[Project]:
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        return result.scalar_one_or_none()

    async def get_projects(self, user_id: str) -> list:
        result = await self.db.execute(
            select(Project).join(
                ProjectMember, Project.id == ProjectMember.project_id
            ).where(
                ProjectMember.user_id == user_id
            )
        )
        return result.scalars().all()

    async def add_member(self, project_id: int, user_id: str, role: str = "member") -> ProjectMember:
        member = ProjectMember(project_id=project_id, user_id=user_id, role=role)
        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(member)
        return member

    async def remove_member(self, project_id: int, user_id: str) -> bool:
        result = await self.db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id
            )
        )
        member = result.scalar_one_or_none()
        if member:
            await self.db.delete(member)
            await self.db.commit()
            return True
        return False

    async def get_members(self, project_id: int) -> list:
        result = await self.db.execute(
            select(ProjectMember).where(ProjectMember.project_id == project_id)
        )
        return result.scalars().all()

    async def update_project(self, project_id: int, name: str = None, description: str = None, project_type: str = None) -> Optional[Project]:
        project = await self.get_project(project_id)
        if not project:
            return None
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        if project_type is not None:
            project.project_type = project_type
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def delete_project(self, project_id: int) -> bool:
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if project:
            await self.db.delete(project)
            await self.db.commit()
            return True
        return False