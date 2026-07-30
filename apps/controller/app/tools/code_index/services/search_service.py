import logging
from typing import Dict, List, Optional
from sqlalchemy import select, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.tools.code_index.db.models import Node, Project

logger = logging.getLogger(__name__)


class SearchService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search_symbols(self, project_id: int, query: str, node_type: str = None, limit: int = 50) -> List[Dict]:
        conditions = [Node.project_id == project_id]
        if node_type:
            conditions.append(Node.node_type == node_type)
        if query:
            conditions.append(
                or_(
                    Node.name.ilike(f"%{query}%"),
                    Node.signature.ilike(f"%{query}%"),
                    Node.docstring.ilike(f"%{query}%"),
                )
            )
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

    async def semantic_search(self, project_id: int, query: str, top_k: int = 10,
                              node_type: str = None) -> List[Dict]:
        from app.tools.code_index.services.node_embedding_store import NodeEmbeddingStore
        store = NodeEmbeddingStore(self.db)

        vector_scores = {}
        try:
            vec_results = await store.vector_search(query, project_id, top_k=top_k * 2)
            for node_id, score in vec_results:
                vector_scores[node_id] = score
        except Exception as e:
            logger.warning(f"Vector search failed (falling back to exact): {e}")

        exact_conditions = [Node.project_id == project_id]
        if node_type:
            exact_conditions.append(Node.node_type == node_type)
        query_lower = query.lower()
        exact_conditions.append(
            (Node.name == query_lower) |
            (Node.name.ilike(f"%{query_lower}%")) |
            (Node.signature.ilike(f"%{query_lower}%")) |
            (Node.docstring.ilike(f"%{query_lower}%"))
        )
        exact_result = await self.db.execute(
            select(Node).where(*exact_conditions).limit(top_k * 2)
        )
        exact_nodes = exact_result.scalars().all()

        all_nodes_covered = list(exact_nodes)
        if vector_scores:
            vec_node_ids = list(vector_scores.keys())
            vec_result = await self.db.execute(
                select(Node).where(Node.id.in_(vec_node_ids))
            )
            for n in vec_result.scalars().all():
                if n.id not in {x.id for x in all_nodes_covered}:
                    all_nodes_covered.append(n)

        scored = {}
        for node in all_nodes_covered:
            vec_score = vector_scores.get(node.id, 0.0)
            exact_score = 1.0 if node.name.lower() == query_lower else (
                0.4 if query_lower in (node.name or "").lower() else 0.0
            )
            fuzzy_score = self._fuzzy_match(query, node.name, node.signature, node.docstring)

            total = round(vec_score * 0.5 + exact_score * 0.3 + fuzzy_score * 0.2, 4)
            scored[node.id] = {
                "node": node,
                "score": total,
                "score_breakdown": {
                    "vector": round(vec_score, 4),
                    "exact": round(exact_score, 4),
                    "fuzzy": round(fuzzy_score, 4),
                }
            }

        ranked = sorted(scored.values(), key=lambda x: x["score"], reverse=True)[:top_k]
        return [{
            "id": r["node"].id,
            "node_type": r["node"].node_type,
            "name": r["node"].name,
            "qualified_name": r["node"].qualified_name,
            "file_path": r["node"].file_path,
            "line_start": r["node"].line_start,
            "language": r["node"].language,
            "signature": r["node"].signature,
            "return_type": r["node"].return_type,
            "docstring": r["node"].docstring,
            "score": r["score"],
            "score_breakdown": r["score_breakdown"],
        } for r in ranked]

    def _fuzzy_match(self, query: str, name: str = None, signature: str = None, docstring: str = None) -> float:
        q_words = set(query.lower().split())
        if not q_words:
            return 0.0
        texts = [t for t in [name, signature, docstring] if t]
        if not texts:
            return 0.0
        best = 0.0
        for text in texts:
            t_words = set(text.lower().split())
            overlap = q_words & t_words
            score = len(overlap) / len(q_words) if q_words else 0.0
            best = max(best, score)
        return best
