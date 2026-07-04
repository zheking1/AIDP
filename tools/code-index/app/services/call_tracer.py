import re
from typing import Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Node, Edge, Project


class CallTracer:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_callers(self, node_id: int, project_id: int, max_depth: int = 3) -> List[Dict]:
        callers = []
        visited = set()
        await self._trace_up(node_id, project_id, max_depth, callers, visited, 0)
        return callers[:100]

    async def get_callees(self, node_id: int, project_id: int, max_depth: int = 3) -> List[Dict]:
        callees = []
        visited = set()
        await self._trace_down(node_id, project_id, max_depth, callees, visited, 0)
        return callees[:100]

    async def _trace_up(self, node_id: int, project_id: int, max_depth: int,
                        callers: List[Dict], visited: set, depth: int):
        if depth >= max_depth or node_id in visited:
            return
        visited.add(node_id)

        result = await self.db.execute(
            select(Edge).where(
                Edge.project_id == project_id,
                Edge.target_id == node_id,
                Edge.edge_type == "calls"
            )
        )
        edges = result.scalars().all()
        for edge in edges:
            caller = await self.db.execute(
                select(Node).where(Node.id == edge.source_id)
            )
            node = caller.scalar_one_or_none()
            if node:
                callers.append({
                    "node_id": node.id,
                    "name": node.name,
                    "type": node.node_type,
                    "file": node.file_path,
                    "line": node.line_start,
                    "depth": depth,
                })
                await self._trace_up(node.id, project_id, max_depth, callers, visited, depth + 1)

    async def _trace_down(self, node_id: int, project_id: int, max_depth: int,
                          callees: List[Dict], visited: set, depth: int):
        if depth >= max_depth or node_id in visited:
            return
        visited.add(node_id)

        result = await self.db.execute(
            select(Edge).where(
                Edge.project_id == project_id,
                Edge.source_id == node_id,
                Edge.edge_type == "calls"
            )
        )
        edges = result.scalars().all()
        for edge in edges:
            callee = await self.db.execute(
                select(Node).where(Node.id == edge.target_id)
            )
            node = callee.scalar_one_or_none()
            if node:
                callees.append({
                    "node_id": node.id,
                    "name": node.name,
                    "type": node.node_type,
                    "file": node.file_path,
                    "line": node.line_start,
                    "depth": depth,
                })
                await self._trace_down(node.id, project_id, max_depth, callees, visited, depth + 1)


class ImpactAnalyzer:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze_impact(self, node_id: int, project_id: int) -> Dict:
        result = await self.db.execute(
            select(Node).where(Node.id == node_id)
        )
        node = result.scalar_one_or_none()
        if not node:
            return {"error": "Node not found"}

        callers = await self._get_dependents(node_id, project_id)
        callees = await self._get_dependencies(node_id, project_id)

        return {
            "node": {
                "id": node.id,
                "name": node.name,
                "type": node.node_type,
                "file": node.file_path,
                "line": node.line_start,
            },
            "direct_callers": len(callers),
            "direct_callees": len(callees),
            "callers": callers[:20],
            "callees": callees[:20],
            "risk_level": self._assess_risk(len(callers), len(callees)),
        }

    async def _get_dependents(self, node_id: int, project_id: int) -> List[Dict]:
        result = await self.db.execute(
            select(Edge).where(
                Edge.project_id == project_id,
                Edge.target_id == node_id,
                Edge.edge_type.in_(["calls", "extends", "implements", "references"])
            )
        )
        edges = result.scalars().all()
        deps = []
        for e in edges:
            node = await self.db.execute(select(Node).where(Node.id == e.source_id))
            n = node.scalar_one_or_none()
            if n:
                deps.append({"id": n.id, "name": n.name, "type": n.node_type})
        return deps

    async def _get_dependencies(self, node_id: int, project_id: int) -> List[Dict]:
        result = await self.db.execute(
            select(Edge).where(
                Edge.project_id == project_id,
                Edge.source_id == node_id,
                Edge.edge_type.in_(["calls", "extends", "implements", "references"])
            )
        )
        edges = result.scalars().all()
        deps = []
        for e in edges:
            node = await self.db.execute(select(Node).where(Node.id == e.target_id))
            n = node.scalar_one_or_none()
            if n:
                deps.append({"id": n.id, "name": n.name, "type": n.node_type})
        return deps

    def _assess_risk(self, callers: int, callees: int) -> str:
        if callers > 10:
            return "high"
        elif callers > 5:
            return "medium"
        return "low"
