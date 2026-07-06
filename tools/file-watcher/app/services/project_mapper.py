from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import WatchedProject


class ProjectMapper:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_project(
        self,
        project_name: str,
        local_path: str,
        code_index_project_id: int,
        ignored_dirs: List[str] = None,
        ignored_patterns: List[str] = None,
    ) -> WatchedProject:
        project = WatchedProject(
            project_name=project_name,
            local_path=local_path,
            code_index_project_id=code_index_project_id,
            ignored_dirs=ignored_dirs or [],
            ignored_patterns=ignored_patterns or [],
        )
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def get_project_by_path(self, local_path: str) -> Optional[WatchedProject]:
        result = await self.db.execute(
            select(WatchedProject).where(
                WatchedProject.local_path == local_path,
                WatchedProject.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def get_project_by_id(self, project_id: int) -> Optional[WatchedProject]:
        result = await self.db.execute(
            select(WatchedProject).where(WatchedProject.id == project_id)
        )
        return result.scalar_one_or_none()

    async def get_project_by_name(self, project_name: str) -> Optional[WatchedProject]:
        result = await self.db.execute(
            select(WatchedProject).where(WatchedProject.project_name == project_name)
        )
        return result.scalar_one_or_none()

    async def list_active_projects(self) -> List[WatchedProject]:
        result = await self.db.execute(
            select(WatchedProject).where(WatchedProject.is_active == True)
        )
        return list(result.scalars().all())

    async def deactivate_project(self, project_id: int) -> bool:
        project = await self.get_project_by_id(project_id)
        if not project:
            return False
        project.is_active = False
        await self.db.commit()
        return True

    async def delete_project(self, project_id: int) -> bool:
        project = await self.get_project_by_id(project_id)
        if not project:
            return False
        await self.db.delete(project)
        await self.db.commit()
        return True
