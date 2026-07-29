import json
import logging
import math
import re
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.knowledge_tool.db.models import KtDocument, KtDocumentChunk, KnowledgeBase, ProjectKnowledgeBinding

logger = logging.getLogger(__name__)


def _cosine_similarity(a: list, b: list) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class SearchService:
    """元数据过滤 + 两层检索 (摘要索引 → chunk搜索)"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _resolve_kb_ids(
        self,
        workspace_id: str = None,
        project_id: str = None,
        knowledge_base_ids: list = None,
    ) -> List[str]:
        """解析需要搜索的知识库ID列表"""
        kb_ids = set()

        if knowledge_base_ids:
            kb_ids.update(knowledge_base_ids)

        if project_id:
            result = await self.db.execute(
                select(ProjectKnowledgeBinding.knowledge_base_id).where(
                    ProjectKnowledgeBinding.project_id == project_id,
                )
            )
            for row in result.all():
                kb_ids.add(row[0])

            bindings_result = await self.db.execute(
                select(ProjectKnowledgeBinding, KnowledgeBase)
                .join(KnowledgeBase, ProjectKnowledgeBinding.knowledge_base_id == KnowledgeBase.id)
                .where(
                    ProjectKnowledgeBinding.project_id == project_id,
                    KnowledgeBase.deleted_at.is_(None),
                )
            )
            for _, kb in bindings_result.all():
                kb_ids.add(kb.id)
                if kb.parent_id:
                    _ids = await self._collect_ancestor_ids(kb.parent_id)
                    kb_ids.update(_ids)

        if not kb_ids and workspace_id:
            result = await self.db.execute(
                select(KnowledgeBase.id).where(
                    KnowledgeBase.deleted_at.is_(None),
                )
            )
            for row in result.all():
                kb_ids.add(row[0])

        return list(kb_ids)

    async def _collect_ancestor_ids(self, parent_id: str) -> set:
        ids = set()
        current = parent_id
        visited = set()
        while current and current not in visited:
            visited.add(current)
            result = await self.db.execute(
                select(KnowledgeBase).where(
                    KnowledgeBase.id == current,
                    KnowledgeBase.deleted_at.is_(None),
                )
            )
            kb = result.scalar()
            if kb:
                ids.add(kb.id)
                current = kb.parent_id
            else:
                break
        return ids

    async def _load_kb_map(self, kb_ids: List[str]) -> Dict[str, dict]:
        if not kb_ids:
            return {}
        result = await self.db.execute(
            select(KnowledgeBase).where(KnowledgeBase.id.in_(kb_ids))
        )
        kbs = result.scalars().all()
        return {
            kb.id: {
                "name": kb.name,
                "slug": kb.slug,
                "kb_level": kb.kb_level,
                "domains": json.loads(kb.domains) if isinstance(kb.domains, str) else (kb.domains or []),
            }
            for kb in kbs
        }

    def _match_domains(self, kb_domains: list, task_domains: list) -> bool:
        if not task_domains or not kb_domains:
            return True
        kb_set = {d.lower() for d in kb_domains}
        task_set = {d.lower() for d in task_domains}
        return bool(kb_set & task_set)

    def _compute_text_score(self, query: str, text: str) -> float:
        if not query or not text:
            return 0.0
        ql = query.lower()
        tl = text.lower()
        if ql in tl:
            return 0.6 + 0.3 * min(1.0, len(query) / max(1, len(text)))
        q_words = set(ql.split())
        t_words = set(tl.split())
        if not q_words:
            return 0.0
        overlap = q_words & t_words
        jaccard = len(overlap) / len(q_words | t_words) if (q_words | t_words) else 0.0
        contain = len(overlap) / len(q_words) if q_words else 0.0
        return 0.3 * jaccard + 0.7 * contain

    async def search(
        self,
        query: str,
        workspace_id: str = None,
        project_id: str = None,
        knowledge_base_ids: list = None,
        task_domains: list = None,
        top_k: int = 8,
        min_score: float = 0.15,
        **kwargs,
    ) -> dict:
        kb_ids = await self._resolve_kb_ids(
            workspace_id=workspace_id,
            project_id=project_id,
            knowledge_base_ids=knowledge_base_ids,
        )
        kb_map = await self._load_kb_map(kb_ids)

        if not kb_ids:
            return {"items": [], "total": 0, "matched_kb_ids": [], "reranked": False}

        domain_filtered_kb_ids = set()
        if task_domains:
            for kb_id in kb_ids:
                kb_info = kb_map.get(kb_id, {})
                kb_domains = kb_info.get("domains", [])
                if self._match_domains(kb_domains, task_domains):
                    domain_filtered_kb_ids.add(kb_id)
            if domain_filtered_kb_ids:
                kb_ids = list(domain_filtered_kb_ids)

        doc_ids = await self._search_summary_level(query, kb_ids, max(15, top_k * 2))
        if not doc_ids:
            return {"items": [], "total": 0, "matched_kb_ids": kb_ids, "reranked": False}

        scored_chunks = await self._search_chunk_level(query, doc_ids, kb_ids, kb_map)
        scored_chunks.sort(key=lambda x: x["score"], reverse=True)
        scored_chunks = [c for c in scored_chunks if c["score"] >= min_score]

        scored_chunks = self._deduplicate_by_topic(scored_chunks, kb_map)

        items = scored_chunks[:top_k]
        for item in items:
            item["citation_id"] = f"{item['document_id']}:{item['chunk_index']}"

        return {
            "items": items,
            "total": len(items),
            "matched_kb_ids": kb_ids,
            "reranked": False,
        }

    async def semantic_search(
        self,
        query: str,
        workspace_id: str = None,
        project_id: str = None,
        knowledge_base_ids: list = None,
        task_domains: list = None,
        top_k: int = 8,
        search_mode: str = "hybrid",
        **kwargs,
    ) -> dict:
        kb_ids = await self._resolve_kb_ids(
            workspace_id=workspace_id,
            project_id=project_id,
            knowledge_base_ids=knowledge_base_ids,
        )
        kb_map = await self._load_kb_map(kb_ids)

        if not kb_ids:
            return {"items": [], "total": 0, "matched_kb_ids": [], "search_mode": search_mode, "latency_ms": 0}

        if task_domains:
            domain_filtered = set()
            for kb_id in kb_ids:
                kb_info = kb_map.get(kb_id, {})
                if self._match_domains(kb_info.get("domains", []), task_domains):
                    domain_filtered.add(kb_id)
            if domain_filtered:
                kb_ids = list(domain_filtered)

        doc_ids = await self._search_summary_level(query, kb_ids, max(30, top_k * 3))
        if not doc_ids:
            return {"items": [], "total": 0, "matched_kb_ids": kb_ids, "search_mode": search_mode, "latency_ms": 0}

        chunks = await self._load_chunks(doc_ids, kb_ids, kb_map, limit=300)
        if not chunks:
            return {"items": [], "total": 0, "matched_kb_ids": kb_ids, "search_mode": search_mode, "latency_ms": 0}

        fused = {}
        for idx, chunk in enumerate(chunks):
            content = chunk.get("content", "")
            title = chunk.get("title", "")

            exact_score = self._score_exact(query, content, title) if search_mode in ("hybrid", "exact") else 0.0
            vector_score = self._score_vector(query, chunk) if search_mode in ("hybrid", "vector") else 0.0
            text_score = self._score_bm25(query, content) if search_mode in ("hybrid", "bm25") else 0.0

            score = exact_score * 0.35 + vector_score * 0.40 + text_score * 0.25
            chunk["score"] = round(score, 4)
            chunk["score_breakdown"] = {
                "exact": round(exact_score, 4),
                "vector": round(vector_score, 4),
                "text": round(text_score, 4),
            }
            fused[idx] = chunk

        sorted_items = sorted(fused.values(), key=lambda x: x["score"], reverse=True)
        sorted_items = self._deduplicate_by_topic(sorted_items, kb_map)

        items = sorted_items[:top_k]
        for item in items:
            item["citation_id"] = f"{item['document_id']}:{item['chunk_index']}"

        return {
            "items": items,
            "total": len(items),
            "matched_kb_ids": kb_ids,
            "search_mode": search_mode,
            "latency_ms": 0,
        }

    async def _load_chunks(self, doc_ids: list, kb_ids: list, kb_map: dict, limit: int = 300) -> list:
        chunks_result = await self.db.execute(
            select(KtDocumentChunk, KtDocument.title, KtDocument.knowledge_base_id, KtDocument.doc_type)
            .join(KtDocument, KtDocumentChunk.document_id == KtDocument.id)
            .where(
                KtDocumentChunk.document_id.in_(doc_ids),
                KtDocumentChunk.deleted_at.is_(None),
            )
            .limit(limit)
        )
        rows = chunks_result.all()

        chunks = []
        for chunk, doc_title, kb_id, doc_type in rows:
            kb_info = kb_map.get(kb_id, {})
            heading_path = (
                json.loads(chunk.heading_path) if isinstance(chunk.heading_path, str)
                else (chunk.heading_path or [])
            )
            embedding = None
            if chunk.embedding:
                try:
                    embedding = json.loads(chunk.embedding) if isinstance(chunk.embedding, str) else chunk.embedding
                except (json.JSONDecodeError, TypeError):
                    pass

            chunks.append({
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "title": doc_title or chunk.id,
                "content": chunk.content or "",
                "score": 0.0,
                "keyword_score": 0.0,
                "vector_score": 0.0,
                "version": "v1",
                "source_uri": None,
                "heading_path": heading_path,
                "source_start_line": chunk.source_start_line,
                "source_end_line": chunk.source_end_line,
                "knowledge_base_id": kb_id,
                "kb_name": kb_info.get("name", ""),
                "kb_level": kb_info.get("kb_level", ""),
                "metadata": {},
                "_embedding": embedding,
                "_doc_type": doc_type,
            })

        return chunks

    def _score_exact(self, query: str, content: str, title: str) -> float:
        if not query:
            return 0.0
        query_lower = query.lower().strip()
        title_lower = (title or "").lower()

        exact_patterns = [
            (rf'\b{re.escape(query_lower)}\b', 1.0),
            (rf'{re.escape(query_lower)}', 0.9),
            (r'(?:def|class|function|const|var|let)\s+' + re.escape(query_lower), 0.8),
        ]

        for pattern, weight in exact_patterns:
            if re.search(pattern, title_lower):
                return weight
            if re.search(pattern, (content or "").lower()):
                return weight * 0.8

        words = query_lower.split()
        if len(words) >= 2:
            title_match_count = sum(1 for w in words if w in title_lower)
            if title_match_count >= len(words) * 0.8:
                return 0.6
            content_lower = (content or "").lower()
            content_match_count = sum(1 for w in words if w in content_lower)
            if content_match_count >= len(words) * 0.8:
                return 0.5

        return 0.0

    def _score_vector(self, query: str, chunk: dict) -> float:
        chunk_embedding = chunk.get("_embedding")
        if not chunk_embedding:
            return 0.0
        try:
            provider = self._get_query_embedding_provider(dimension=len(chunk_embedding))
            query_emb = provider.embed(query)
            return _cosine_similarity(query_emb.values, chunk_embedding)
        except Exception:
            return 0.0

    @staticmethod
    def _get_query_embedding_provider(dimension: int = 384):
        from app.tools.knowledge_tool.config import settings
        provider_name = settings.EMBEDDING_PROVIDER
        if provider_name == "openai":
            from app.tools.knowledge_tool.embedding.openai_provider import OpenAIEmbeddingProvider
            return OpenAIEmbeddingProvider(
                model=settings.OPENAI_EMBEDDING_MODEL,
                api_key=settings.OPENAI_API_KEY or None,
                base_url=settings.OPENAI_BASE_URL or None,
            )
        elif provider_name == "local":
            from app.tools.knowledge_tool.embedding.local_provider import LocalEmbeddingProvider
            return LocalEmbeddingProvider(model_name=settings.LOCAL_EMBEDDING_MODEL)
        else:
            from app.tools.knowledge_tool.embedding.mock_provider import MockEmbeddingProvider
            return MockEmbeddingProvider(dimension=dimension)

    def _score_bm25(self, query: str, content: str) -> float:
        if not query or not content:
            return 0.0

        k1 = 1.5
        b = 0.75
        avg_doc_length = 200

        query_words = query.lower().split()
        content_words = content.lower().split()
        doc_len = len(content_words)

        score = 0.0
        for word in query_words:
            tf = content_words.count(word)
            if tf == 0:
                continue
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * doc_len / avg_doc_length)
            score += numerator / denominator

        max_score = len(query_words) * (k1 + 1) / (1 + k1 * b)
        normalized = score / max_score if max_score > 0 else 0.0
        return min(normalized, 1.0)

    async def _search_summary_level(self, query: str, kb_ids: list, limit: int) -> list:
        docs_result = await self.db.execute(
            select(KtDocument).where(
                KtDocument.knowledge_base_id.in_(kb_ids),
                KtDocument.deleted_at.is_(None),
            )
        )
        docs = docs_result.scalars().all()

        scored = []
        for doc in docs:
            title_score = self._compute_text_score(query, doc.title or "")
            summary_text = doc.summary or doc.title or ""
            summary_score = self._compute_text_score(query, summary_text)
            tags = json.loads(doc.tags) if isinstance(doc.tags, str) else (doc.tags or [])
            tag_score = sum(self._compute_text_score(query, t) for t in tags) * 0.3

            total = title_score * 0.5 + summary_score * 0.3 + min(tag_score, 0.2)
            if total > 0.1:
                scored.append((doc.id, total))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [doc_id for doc_id, _ in scored[:limit]]

    async def _search_chunk_level(
        self, query: str, doc_ids: list, kb_ids: list, kb_map: dict
    ) -> list:
        if not doc_ids:
            return []

        chunks_result = await self.db.execute(
            select(KtDocumentChunk, KtDocument.title, KtDocument.knowledge_base_id, KtDocument.doc_type)
            .join(KtDocument, KtDocumentChunk.document_id == KtDocument.id)
            .where(
                KtDocumentChunk.document_id.in_(doc_ids),
                KtDocumentChunk.deleted_at.is_(None),
            )
            .limit(200)
        )
        rows = chunks_result.all()

        scored = []
        for chunk, doc_title, kb_id, doc_type in rows:
            score = self._compute_text_score(query, chunk.content or "")

            kb_info = kb_map.get(kb_id, {})
            kb_level = kb_info.get("kb_level", "")

            heading_path = (
                json.loads(chunk.heading_path) if isinstance(chunk.heading_path, str)
                else (chunk.heading_path or [])
            )

            if score > 0.05:
                scored.append({
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "title": doc_title or chunk.id,
                    "content": chunk.content or "",
                    "score": round(score, 4),
                    "keyword_score": 0.0,
                    "vector_score": 0.0,
                    "version": "v1",
                    "source_uri": None,
                    "heading_path": heading_path,
                    "source_start_line": chunk.source_start_line,
                    "source_end_line": chunk.source_end_line,
                    "knowledge_base_id": kb_id,
                    "kb_name": kb_info.get("name", ""),
                    "kb_level": kb_level,
                    "metadata": {},
                })

        return scored

    def _deduplicate_by_topic(self, items: list, kb_map: dict) -> list:
        """跨层去重: 同主题保留最高层级的"""
        level_priority = {"project": 3, "template": 2, "framework": 1}

        topic_map = {}
        for item in items:
            topic = self._extract_topic(item.get("content", ""), item.get("title", ""))
            lp = level_priority.get(item.get("kb_level", ""), 0)
            if topic not in topic_map:
                topic_map[topic] = item
            else:
                existing_lp = level_priority.get(topic_map[topic].get("kb_level", ""), 0)
                if lp > existing_lp:
                    topic_map[topic] = item

        return list(topic_map.values())

    def _extract_topic(self, content: str, title: str) -> str:
        """从内容中提取核心主题 (简单版: 取前5个核心名词)"""
        text = f"{title} {content[:200]}" if content else title
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "can", "shall", "to", "of", "in", "for",
            "on", "with", "at", "by", "from", "as", "into", "through", "during",
            "before", "after", "above", "below", "between", "and", "or", "not",
            "this", "that", "these", "those", "it", "its", "的", "是", "在",
            "了", "和", "与", "或", "不", "这", "那", "中", "等", "为",
            "上", "下", "也", "就", "都", "而", "及", "个", "有",
            "一", "二", "三", "大", "小", "多", "少", "很", "更", "最",
        }
        words = [w for w in text.lower().split() if w not in stop_words and len(w) > 2]
        return " ".join(words[:5])


search_service = SearchService


# ── Legacy search classes for backward compat ────────────

import hashlib
import re


class FTS5SearchService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search(self, query: str, workspace_id: str, limit: int = 20):
        from app.tools.knowledge_tool.db.models import KtDocument
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

    async def search(self, query: str, workspace_id: str, limit: int = 10):
        from app.tools.knowledge_tool.db.models import KtDocument
        result = await self.db.execute(
            select(KtDocument).where(
                KtDocument.workspace_id == workspace_id,
                KtDocument.deleted_at.is_(None)
            ).limit(limit * 3)
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