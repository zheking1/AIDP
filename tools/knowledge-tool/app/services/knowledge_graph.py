import math
from typing import List, Dict, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import KtDocument, KtDocumentChunk


class KnowledgeGraph:
    DIRECT_LINK_WEIGHT = 3.0
    SOURCE_OVERLAP_WEIGHT = 2.0
    ADAMIC_ADAR_WEIGHT = 1.0
    TYPE_AFFINITY_WEIGHT = 1.5

    def __init__(self, db: AsyncSession):
        self.db = db

    async def compute_relevance(self, doc_id_a: int, doc_id_b: int) -> float:
        score = 0.0
        a = await self._get_doc(doc_id_a)
        b = await self._get_doc(doc_id_b)
        if not a or not b:
            return 0.0

        # Direct link
        if self._has_direct_link(a.title, b.title):
            score += self.DIRECT_LINK_WEIGHT

        # Source overlap
        overlap = self._source_overlap(a, b)
        score += overlap * self.SOURCE_OVERLAP_WEIGHT

        # Type affinity
        if a.doc_type == b.doc_type:
            score += self.TYPE_AFFINITY_WEIGHT

        return round(score, 4)

    async def get_communities(self, project_id: str = None, limit: int = 20) -> List[Dict]:
        query = select(KtDocument).where(KtDocument.deleted_at.is_(None))
        if project_id:
            query = query.where(KtDocument.project_id == project_id)
        result = await self.db.execute(query.limit(limit))
        docs = result.scalars().all()

        communities = []
        for doc in docs:
            community = {
                "id": doc.id,
                "title": doc.title,
                "doc_type": doc.doc_type,
                "project_id": doc.project_id,
                "tags": doc.tags or [],
            }
            communities.append(community)
        return communities

    async def _get_doc(self, doc_id: int):
        result = await self.db.execute(
            select(KtDocument).where(KtDocument.id == doc_id, KtDocument.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    def _has_direct_link(self, title_a: str, title_b: str) -> bool:
        return title_b.replace(" ", "") in title_a.replace(" ", "") or title_a.replace(" ", "") in title_b.replace(" ", "")

    def _source_overlap(self, doc_a, doc_b) -> float:
        tags_a = set(doc_a.tags or [])
        tags_b = set(doc_b.tags or [])
        if not tags_a or not tags_b:
            return 0.0
        return len(tags_a & tags_b) / max(len(tags_a | tags_b), 1)


class CodeLinker:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def link_document_to_code(self, doc_id: int, code_refs: List[Dict]) -> List[Dict]:
        links = []
        for ref in code_refs:
            name = ref.get("name", "")
            result = await self.db.execute(
                select(KtDocument).where(
                    KtDocument.title.ilike(f"%{name}%"),
                    KtDocument.deleted_at.is_(None)
                )
            )
            matched = result.scalars().first()
            if matched:
                links.append({
                    "doc_id": doc_id,
                    "linked_doc_id": matched.id,
                    "link_type": ref.get("type", "reference"),
                    "confidence": ref.get("confidence", 0.5),
                })
        return links

    async def get_document_links(self, doc_id: int) -> List[Dict]:
        result = await self.db.execute(
            select(KtDocument).where(
                KtDocument.id == doc_id,
                KtDocument.deleted_at.is_(None)
            )
        )
        doc = result.scalar_one_or_none()
        if not doc:
            return []
        return [{"title": doc.title, "type": doc.doc_type}]


class DriftDetector:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def detect_drift(self, doc_id: int) -> List[Dict]:
        drifts = []
        result = await self.db.execute(
            select(KtDocument).where(
                KtDocument.id == doc_id,
                KtDocument.deleted_at.is_(None)
            )
        )
        doc = result.scalar_one_or_none()
        if not doc:
            return drifts

        if doc.index_status == "failed":
            drifts.append({
                "type": "index_failed",
                "description": f"文档 {doc.title} 索引失败",
                "severity": "high",
            })

        return drifts
