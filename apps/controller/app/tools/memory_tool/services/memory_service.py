from typing import Optional
from sqlalchemy import select, func
from app.tools.memory_tool.db.models import MemoryEntry
from app.tools.memory_tool.config import settings


def _get_session():
    from app.tools.memory_tool.db.models import async_session
    return async_session()


async def create_memory(
    project: str,
    category: str,
    title: str,
    content: str,
    tags: Optional[str] = None,
    pinned: bool = False,
    user_id: Optional[int] = None,
    check_contradictions: bool = False,
) -> dict:
    async with _get_session() as session:
        if check_contradictions:
            from app.tools.memory_tool.services.semantic_contradiction import SemanticContradictionDetector, ContradictionHandler
            q = select(MemoryEntry).where(MemoryEntry.project == project)
            if user_id:
                q = q.where(MemoryEntry.user_id == user_id)
            existing = await session.execute(q.limit(100))
            existing_list = existing.scalars().all()

            detector = SemanticContradictionDetector()
            contradictions = detector.detect(
                {"title": title, "content": content},
                [{"id": e.id, "title": e.title, "content": e.content, "createdAt": str(e.created_at)} for e in existing_list]
            )

            if contradictions:
                handler = ContradictionHandler()
                actions = []
                for c in contradictions:
                    action = handler.handle(
                        {"title": title, "content": content},
                        c["existing_memory"],
                        c["contradiction_type"],
                        c["confidence"],
                    )
                    actions.append({"contradiction": c, "action": action})

                if any(a["action"]["action"] == "flag_for_review" for a in actions):
                    return {
                        "status": "warning",
                        "message": "检测到矛盾记忆，已标记为待审核",
                        "contradictions": actions,
                    }

        entry = MemoryEntry(
            project=project, user_id=user_id, category=category,
            title=title, content=content,
        )
        session.add(entry)
        await session.commit()
        await session.refresh(entry)
        return _to_dict(entry)


async def search_memory(
    project: str,
    query: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    user_id: Optional[int] = None,
) -> list:
    async with _get_session() as session:
        q = select(MemoryEntry).where(MemoryEntry.project == project)

        if category:
            q = q.where(MemoryEntry.category == category)
        if user_id:
            q = q.where(MemoryEntry.user_id == user_id)
        if query:
            q = q.where(
                MemoryEntry.title.ilike(f"%{query}%") |
                MemoryEntry.content.ilike(f"%{query}%")
            )

        q = q.order_by(MemoryEntry.id.desc()).limit(min(limit, settings.MEMORY_MAX_LIMIT))
        result = await session.execute(q)
        return [_to_dict(r) for r in result.scalars().all()]


async def get_memory(memory_id: int) -> Optional[dict]:
    async with _get_session() as session:
        result = await session.execute(select(MemoryEntry).where(MemoryEntry.id == memory_id))
        entry = result.scalar_one_or_none()
        return _to_dict(entry) if entry else None


async def update_memory(memory_id: int, **kwargs) -> Optional[dict]:
    async with _get_session() as session:
        result = await session.execute(select(MemoryEntry).where(MemoryEntry.id == memory_id))
        entry = result.scalar_one_or_none()
        if not entry:
            return None
        for key, value in kwargs.items():
            if hasattr(entry, key) and value is not None:
                setattr(entry, key, value)
        await session.commit()
        await session.refresh(entry)
        return _to_dict(entry)


async def delete_memory(memory_id: int) -> bool:
    async with _get_session() as session:
        result = await session.execute(select(MemoryEntry).where(MemoryEntry.id == memory_id))
        entry = result.scalar_one_or_none()
        if not entry:
            return False
        await session.delete(entry)
        await session.commit()
        return True


async def get_context_package(project: str, query: str, limit: int = 10) -> dict:
    memories = await search_memory(project, query=query, limit=limit)
    return {
        "project": project,
        "query": query,
        "memories": memories,
        "count": len(memories),
    }


def _to_dict(entry: MemoryEntry) -> dict:
    return {
        "id": entry.id,
        "project": entry.project,
        "userId": entry.user_id,
        "category": entry.category,
        "title": entry.title,
        "content": entry.content,
        "createdAt": entry.created_at.isoformat() if entry.created_at else None,
        "updatedAt": entry.updated_at.isoformat() if entry.updated_at else None,
    }


async def hybrid_search(
    project: str,
    query: str,
    vector_weight: float = 0.5,
    text_weight: float = 0.3,
    bm25_weight: float = 0.2,
    top_k: int = 10,
    user_id: Optional[int] = None,
) -> dict:
    from app.tools.memory_tool.services.bm25_search import BM25Search
    from app.tools.memory_tool.services.tfidf_search import TFIDFSearch

    async with _get_session() as session:
        q = select(MemoryEntry).where(MemoryEntry.project == project)
        if user_id:
            q = q.where(MemoryEntry.user_id == user_id)
        q = q.order_by(MemoryEntry.id.desc()).limit(settings.MEMORY_MAX_LIMIT)
        result = await session.execute(q)
        all_memories = result.scalars().all()

    if not all_memories:
        return {"items": [], "total": 0, "search_type": "hybrid"}

    all_dicts = [_to_dict(m) for m in all_memories]

    bm25 = BM25Search()
    bm25.index(all_dicts)
    bm25_results = {idx: score for idx, score in bm25.search(query, all_dicts, top_k=top_k * 2)}

    tfidf = TFIDFSearch()
    tfidf.index(all_dicts)
    tfidf_results = {idx: score for idx, score in tfidf.search(query, all_dicts, top_k=top_k * 2)}

    vector_results: dict = {}
    all_indices = set()
    all_indices.update(bm25_results.keys())
    all_indices.update(tfidf_results.keys())

    fused_scores = {}
    for idx in all_indices:
        bm_score = bm25_results.get(idx, 0.0)
        tf_score = tfidf_results.get(idx, 0.0)
        vec_score = vector_results.get(idx, 0.0)
        total = bm_score * bm25_weight + tf_score * text_weight + vec_score * vector_weight
        fused_scores[idx] = total

    sorted_indices = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

    items = []
    for idx, score in sorted_indices:
        mem = all_dicts[idx]
        items.append({
            "memory": mem,
            "score": round(score, 4),
            "score_breakdown": {
                "bm25": round(bm25_results.get(idx, 0.0), 4),
                "tfidf": round(tfidf_results.get(idx, 0.0), 4),
                "vector": round(vector_results.get(idx, 0.0), 4),
            },
        })

    return {"items": items, "total": len(items), "search_type": "hybrid"}
