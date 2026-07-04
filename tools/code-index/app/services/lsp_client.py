import re
from typing import Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Node, Edge, Project


class LSPClient:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_references(self, project_id: int, symbol_name: str, file_path: str = None, kind: str = None) -> List[Dict]:
        conditions = [Node.project_id == project_id, Node.name == symbol_name]
        if file_path:
            conditions.append(Node.file_path == file_path)
        if kind:
            conditions.append(Node.node_type == kind)
        result = await self.db.execute(select(Node).where(*conditions))
        nodes = result.scalars().all()
        return [{"file_path": n.file_path, "line": n.line_start, "kind": n.node_type, "symbol": n.name} for n in nodes]

    async def find_implementation(self, project_id: int, interface_name: str) -> List[Dict]:
        result = await self.db.execute(select(Node).where(Node.project_id == project_id, Node.node_type == "class", Node.qualified_name.ilike(f"%{interface_name}%")))
        classes = result.scalars().all()
        return [{"name": c.name, "file": c.file_path, "line": c.line_start} for c in classes]

    async def hover(self, project_id: int, file_path: str, line: int) -> Optional[Dict]:
        result = await self.db.execute(select(Node).where(Node.project_id == project_id, Node.file_path == file_path, Node.line_start <= line).order_by(Node.line_start.desc()).limit(1))
        node = result.scalar_one_or_none()
        if node:
            return {"symbol": node.name, "type": node.node_type, "file": node.file_path, "line": node.line_start, "signature": f"{node.node_type} {node.name}"}
        return None
