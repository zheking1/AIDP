from typing import Dict, List, Optional
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Node, Project


class SearchService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search_symbols(self, project_id: int, query: str, node_type: str = None, limit: int = 50) -> List[Dict]:
        conditions = [Node.project_id == project_id]
        if node_type:
            conditions.append(Node.node_type == node_type)
        if query:
            conditions.append(Node.name.ilike(f"%{query}%"))
        result = await self.db.execute(
            select(Node).where(*conditions).limit(limit)
        )
        nodes = result.scalars().all()
        return [{
            "id": n.id,
            "node_type": n.node_type,
            "name": n.name,
            "qualified_name": n.qualified_name,
            "file_path": n.file_path,
            "line_start": n.line_start,
            "language": n.language,
        } for n in nodes]

    async def get_project(self, project_id: int) -> Optional[Project]:
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        return result.scalar_one_or_none()

    async def list_projects(self) -> List[Dict]:
        result = await self.db.execute(select(Project).order_by(Project.id.desc()))
        projects = result.scalars().all()
        return [{
            "id": p.id,
            "name": p.name,
            "path": p.path,
            "language": p.language,
            "framework": p.framework,
            "file_count": p.file_count,
            "node_count": p.node_count,
            "status": p.status,
        } for p in projects]
