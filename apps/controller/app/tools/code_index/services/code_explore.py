from typing import Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.tools.code_index.db.models import Node, Edge, Project
from app.tools.code_index.services.call_tracer import CallTracer, ImpactAnalyzer


class CodeExploreService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def explore(self, project_id: int, action: str, params: Dict = None) -> Dict:
        params = params or {}

        if action == "symbols":
            return await self._search_symbols(project_id, params)
        elif action == "file":
            return await self._get_file(project_id, params)
        elif action == "calls":
            return await self._get_calls(project_id, params)
        elif action == "dependents":
            return await self._get_dependents(project_id, params)
        elif action == "structure":
            return await self._get_structure(project_id, params)
        elif action == "summary":
            return await self._get_summary(project_id)
        elif action == "callers":
            return await self._get_callers(project_id, params)
        elif action == "callees":
            return await self._get_callees(project_id, params)
        elif action == "impact":
            return await self._analyze_impact(project_id, params)
        else:
            return {"error": f"Unknown action: {action}"}

    async def _search_symbols(self, project_id: int, params: Dict) -> Dict:
        query_str = params.get("query", "")
        node_type = params.get("type")
        limit = params.get("limit", 50)

        conditions = [Node.project_id == project_id]
        if node_type:
            conditions.append(Node.node_type == node_type)
        if query_str:
            conditions.append(Node.name.ilike(f"%{query_str}%"))

        result = await self.db.execute(select(Node).where(*conditions).limit(limit))
        nodes = result.scalars().all()
        return {
            "symbols": [{
                "id": n.id, "node_type": n.node_type, "name": n.name,
                "qualified_name": n.qualified_name, "file_path": n.file_path,
                "line_start": n.line_start, "language": n.language,
            } for n in nodes],
            "total": len(nodes),
        }

    async def _get_file(self, project_id: int, params: Dict) -> Dict:
        file_path = params.get("path", "")
        result = await self.db.execute(
            select(Node).where(
                Node.project_id == project_id,
                Node.node_type == "file",
                Node.qualified_name == file_path
            )
        )
        node = result.scalar_one_or_none()
        return {"found": bool(node), "node": self._node_to_dict(node) if node else None}

    async def _get_calls(self, project_id: int, params: Dict) -> Dict:
        result = await self.db.execute(
            select(Edge).where(Edge.project_id == project_id, Edge.edge_type == "calls").limit(100)
        )
        edges = result.scalars().all()
        return {"calls": [{"source_id": e.source_id, "target_id": e.target_id} for e in edges]}

    async def _get_dependents(self, project_id: int, params: Dict) -> Dict:
        node_name = params.get("name", "")
        result = await self.db.execute(
            select(Node).where(Node.project_id == project_id, Node.name == node_name)
        )
        node = result.scalar_one_or_none()
        if not node:
            return {"found": False}

        result = await self.db.execute(
            select(Edge).where(
                Edge.project_id == project_id,
                Edge.target_id == node.id,
                Edge.edge_type.in_(["calls", "extends", "implements"])
            )
        )
        edges = result.scalars().all()
        return {
            "found": True,
            "node": self._node_to_dict(node),
            "dependents": [{"source_id": e.source_id, "edge_type": e.edge_type} for e in edges][:50],
        }

    async def _get_structure(self, project_id: int, params: Dict) -> Dict:
        result = await self.db.execute(
            select(Node).where(
                Node.project_id == project_id,
                Node.node_type.in_(["class", "function", "method"]),
            ).limit(200)
        )
        nodes = result.scalars().all()
        return {"structure": [{
            "id": n.id, "type": n.node_type, "name": n.name,
            "file": n.file_path, "line": n.line_start,
        } for n in nodes]}

    async def _get_summary(self, project_id: int) -> Dict:
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            return {"error": "Project not found"}

        node_count = await self.db.execute(
            select(Node).where(Node.project_id == project_id)
        )
        nodes = node_count.scalars().all()

        return {
            "project": {
                "id": project.id, "name": project.name, "path": project.path,
                "language": project.language, "framework": project.framework,
                "file_count": project.file_count, "node_count": len(nodes),
                "status": project.status,
            }
        }

    async def _get_callers(self, project_id: int, params: Dict) -> Dict:
        tracer = CallTracer(self.db)
        node_id = params.get("node_id")
        if not node_id:
            return {"error": "node_id required"}
        callers = await tracer.get_callers(node_id, project_id)
        return {"callers": callers}

    async def _get_callees(self, project_id: int, params: Dict) -> Dict:
        tracer = CallTracer(self.db)
        node_id = params.get("node_id")
        if not node_id:
            return {"error": "node_id required"}
        callees = await tracer.get_callees(node_id, project_id)
        return {"callees": callees}

    async def _analyze_impact(self, project_id: int, params: Dict) -> Dict:
        analyzer = ImpactAnalyzer(self.db)
        node_id = params.get("node_id")
        if not node_id:
            return {"error": "node_id required"}
        return await analyzer.analyze_impact(node_id, project_id)

    def _node_to_dict(self, node) -> Optional[Dict]:
        if not node:
            return None
        return {
            "id": node.id, "node_type": node.node_type, "name": node.name,
            "qualified_name": node.qualified_name, "file_path": node.file_path,
            "line_start": node.line_start, "line_end": node.line_end,
            "language": node.language,
        }
