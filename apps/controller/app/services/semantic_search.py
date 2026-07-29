"""
知识库语义搜索服务
使用 Controller ModelService 的 embedding 模型进行向量相似度搜索
"""

import json
import logging
import math
from typing import List, Dict, Any, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge.models import KnowledgeDocument
from app.services.model_service import ModelService

logger = logging.getLogger(__name__)


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


async def get_embedding(text: str) -> Optional[List[float]]:
    model = await ModelService.get_best_for_task("embedding")
    if not model:
        logger.warning("No embedding model available")
        return None

    api_base = model.get("api_base", "").rstrip("/")
    model_name = model.get("model_name", "")
    api_key = model.get("api_key", "")

    if not api_base or not api_key or not model_name:
        logger.warning(f"Incomplete embedding model config")
        return None

    import httpx
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "model": model_name,
        "input": text[:3000],
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{api_base}/embeddings", json=payload, headers=headers)
            if resp.status_code != 200:
                logger.warning(f"Embedding API error {resp.status_code}")
                return None
            data = resp.json()
            return data["data"][0]["embedding"]
    except Exception as e:
        logger.warning(f"Embedding call failed: {e}")
        return None


async def get_or_generate_embedding(doc: KnowledgeDocument, model_name: str) -> Optional[List[float]]:
    if doc.embedding:
        try:
            return json.loads(doc.embedding)
        except (json.JSONDecodeError, TypeError):
            pass

    text_for_embed = f"{doc.title or ''} {doc.summary or ''} {(doc.content or '')[:2000]}"
    emb = await get_embedding(text_for_embed)
    if emb:
        doc.embedding = json.dumps(emb)
        doc.embedding_model = model_name
    return emb


async def semantic_search(
    db: AsyncSession,
    query: str,
    top_k: int = 10,
    base_id: Optional[str] = None,
    project_id: Optional[int] = None,
    user_id: Optional[str] = None,
) -> List[Dict]:
    # 1. Get query embedding
    query_emb = await get_embedding(query)
    if not query_emb:
        return []

    # 2. Get embedding model name for matching
    model = await ModelService.get_best_for_task("embedding")
    model_name = model.get("model_name", "") if model else ""

    # 3. Get candidate docs (no keyword filter - scan all for semantic accuracy)
    conditions = [KnowledgeDocument.deleted_at.is_(None)]
    if base_id:
        conditions.append(KnowledgeDocument.base_id == base_id)
    if project_id:
        conditions.append(KnowledgeDocument.project_id == project_id)

    stmt = select(KnowledgeDocument).where(and_(*conditions)).limit(300)
    result = await db.execute(stmt)
    docs = result.scalars().all()

    # 4. Compute similarities
    scored = []
    for doc in docs:
        doc_emb = await get_or_generate_embedding(doc, model_name)
        if doc_emb:
            score = cosine_similarity(query_emb, doc_emb)
            scored.append((score, doc))

    # Flush any embedding updates
    try:
        await db.commit()
    except Exception:
        await db.rollback()

    # 5. Rank and return
    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    for score, doc in scored[:top_k]:
        d = doc.to_dict(include_content=False)
        d["score"] = round(score, 4)
        d["search_mode"] = "semantic"
        results.append(d)

    return results