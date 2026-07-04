import hashlib
import re
from typing import Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import KtDocument


class FTS5SearchService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search(self, query: str, workspace_id: str, limit: int = 20) -> List[Dict]:
        result = await self.db.execute(
            select(KtDocument).where(
                KtDocument.workspace_id == workspace_id,
                KtDocument.deleted_at.is_(None),
                KtDocument.title.ilike(f"%{query}%")
            ).limit(limit)
        )
        docs = result.scalars().all()
        return [{
            "id": d.id, "title": d.title, "doc_type": d.doc_type,
            "workspace_id": d.workspace_id, "project_id": d.project_id,
            "snippet": self._extract_snippet(d.title or "", query),
            "rank": 0,
        } for d in docs]

    def _extract_snippet(self, content: str, query: str, max_len: int = 200) -> str:
        idx = content.lower().find(query.lower())
        if idx == -1:
            return (content[:max_len] + "...") if len(content) > max_len else content
        start = max(0, idx - 50)
        end = min(len(content), idx + len(query) + 50)
        snippet = content[start:end]
        return ("..." if start > 0 else "") + snippet + ("..." if end < len(content) else "")


class SemanticSearchService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search(self, query: str, workspace_id: str, limit: int = 10) -> List[Dict]:
        result = await self.db.execute(
            select(KtDocument).where(
                KtDocument.workspace_id == workspace_id,
                KtDocument.deleted_at.is_(None)
            ).limit(limit)
        )
        docs = result.scalars().all()
        scored = []
        for doc in docs:
            score = self._compute_similarity(query, doc.title or "")
            if score > 0.3:
                scored.append({"doc": doc, "score": score})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return [{
            "id": d["doc"].id,
            "title": d["doc"].title,
            "doc_type": d["doc"].doc_type,
            "workspace_id": d["doc"].workspace_id,
            "score": round(d["score"], 4),
        } for d in scored[:limit]]

    def _compute_similarity(self, a: str, b: str) -> float:
        a_words = set(a.lower().split())
        b_words = set(b.lower().split())
        if not a_words or not b_words:
            return 0.0
        intersection = a_words & b_words
        union = a_words | b_words
        return len(intersection) / len(union)
