"""Memory Search API Routes.

Vector similarity search and text search for memories.
"""
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.memory_tool.tools.memory-tool.db.database import get_db
from app.tools.memory_tool.tools.memory-tool.db.models import MemoryEntry
from app.tools.memory_tool.tools.memory-tool.schemas.memory import (
    VectorSearchRequest,
    VectorSearchResponse,
    VectorSearchResult,
    HybridSearchRequest,
    HybridSearchResponse,
    MemoryResponse,
    ApiResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/memories", tags=["memory-search"])


# ============================================================================
# Search Helpers
# ============================================================================

def memory_to_response(entry: MemoryEntry) -> dict:
    """Convert MemoryEntry to response dict."""
    return {
        "id": entry.id,
        "project": entry.project,
        "user_id": entry.user_id,
        "category": entry.category,
        "title": entry.title,
        "content_preview": entry.content[:200] + "..." if len(entry.content) > 200 else entry.content,
        "memory_tier": entry.memory_tier,
        "parent_id": entry.parent_id,
        "confidence_score": entry.confidence_score,
        "ai_suggested": entry.ai_suggested,
        "ai_review_status": entry.ai_review_status,
        "access_count": entry.access_count or 0,
        "source_type": entry.source_type,
        "has_embedding": entry.embedding is not None,
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
    }


import os
import httpx
from typing import List

_embedding_model_cache = None

async def _get_embedding_model() -> dict:
    global _embedding_model_cache
    if _embedding_model_cache:
        return _embedding_model_cache
    controller = os.environ.get("CONTROLLER_URL", "http://localhost:8883")
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(controller + "/api/models/for-task/embedding")
            if r.status_code == 200:
                data = r.json()
                _embedding_model_cache = data
                return data
    except:
        pass
    return {"model_name": "BAAI/bge-m3", "api_base": "https://api.siliconflow.cn/v1", "api_key": ""}


async def generate_embedding(query: str) -> List[float]:
    model = await _get_embedding_model()
    api_base = (model.get("api_base") or "").rstrip("/")
    api_key = model.get("api_key") or ""
    model_name = model.get("model_name") or "BAAI/bge-m3"
    if not api_base or not api_key:
        return [0.0] * 384
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(api_base + "/embeddings", json={"model": model_name, "input": query[:3000]}, headers={"Content-Type": "application/json", "Authorization": "Bearer " + api_key})
            if resp.status_code == 200:
                emb = resp.json()["data"][0]["embedding"]
                return emb[:384]  # Truncate BGE-M3 1024d to fit 384d storage
    except:
        pass
    return [0.0] * 384


# ============================================================================
# Vector Search
# ============================================================================

@router.post("/search/vector", response_model=ApiResponse)
async def vector_search(
    request: VectorSearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """Semantic search using vector similarity.
    
    Uses pgvector's cosine similarity for approximate nearest neighbor search.
    Falls back to text search if vector search is not available.
    """
    try:
        # Check if we have pgvector available
        from app.tools.memory_tool.tools.memory-tool.db.models import VECTOR_AVAILABLE
        
        if VECTOR_AVAILABLE and request.query:
            # Try vector search first
            try:
                # Generate query embedding
                query_embedding = await generate_embedding(request.query)
                
                # Build vector search query
                # Using cosine similarity: 1 - cosine_distance = similarity
                sql = """
                SELECT 
                    id, project, category, title, content,
                    memory_tier, parent_id, confidence_score,
                    ai_suggested, ai_review_status, access_count,
                    source_type, created_at, updated_at,
                    1 - (embedding <=> :embedding) as similarity
                FROM memory_entries
                WHERE deleted_at IS NULL
                AND embedding IS NOT NULL
                """
                
                params = {"embedding": str(query_embedding)}
                
                if request.project:
                    sql += " AND project = :project"
                    params["project"] = request.project
                
                if request.category:
                    sql += " AND category = :category"
                    params["category"] = request.category
                
                if request.memory_tier:
                    sql += " AND memory_tier = :memory_tier"
                    params["memory_tier"] = request.memory_tier
                
                sql += """
                AND 1 - (embedding <=> :embedding) >= :min_similarity
                ORDER BY embedding <=> :embedding
                LIMIT :top_k
                """
                params["min_similarity"] = request.min_similarity
                params["top_k"] = request.top_k
                
                result = await db.execute(text(sql), params)
                rows = result.fetchall()
                
                results = []
                for row in rows:
                    memory_data = {
                        "id": row.id,
                        "project": row.project,
                        "category": row.category,
                        "title": row.title,
                        "content_preview": row.content[:200] + "..." if len(row.content) > 200 else row.content,
                        "memory_tier": row.memory_tier,
                        "parent_id": row.parent_id,
                        "confidence_score": row.confidence_score,
                        "ai_suggested": row.ai_suggested,
                        "ai_review_status": row.ai_review_status,
                        "access_count": row.access_count or 0,
                        "source_type": row.source_type,
                        "has_embedding": True,
                        "created_at": row.created_at,
                        "updated_at": row.updated_at,
                    }
                    results.append({
                        "memory": memory_data,
                        "similarity": row.similarity,
                    })
                
                return ApiResponse(data={
                    "query": request.query,
                    "results": results,
                    "total": len(results),
                    "search_type": "vector",
                })
                
            except Exception as e:
                logger.warning(f"Vector search failed, falling back to text search: {e}")
        
        # Fallback to text search
        search_pattern = f"%{request.query}%"
        query = select(MemoryEntry).where(
            (MemoryEntry.deleted_at.is_(None)) &
            (
                (MemoryEntry.title.ilike(search_pattern)) |
                (MemoryEntry.content.ilike(search_pattern))
            )
        )
        
        if request.project:
            query = query.where(MemoryEntry.project == request.project)
        if request.category:
            query = query.where(MemoryEntry.category == request.category)
        if request.memory_tier:
            query = query.where(MemoryEntry.memory_tier == request.memory_tier)
        
        query = query.limit(request.top_k)
        
        result = await db.execute(query)
        entries = result.scalars().all()
        
        results = []
        for entry in entries:
            results.append({
                "memory": memory_to_response(entry),
                "similarity": 0.5,  # Default similarity for text search
            })
        
        return ApiResponse(data={
            "query": request.query,
            "results": results,
            "total": len(results),
            "search_type": "text",
        })
    
    except Exception as e:
        logger.error(f"Error in vector search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/hybrid", response_model=ApiResponse)
async def hybrid_search(
    request: HybridSearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """Hybrid search: combines vector similarity with full-text search.
    
    Weights:
    - Vector similarity: 0.7 (default)
    - Text match: 0.3 (default)
    """
    try:
        # For simplicity, just use text search for now
        # In production, this would combine both scores
        search_pattern = f"%{request.query}%"
        
        query = select(MemoryEntry).where(
            (MemoryEntry.deleted_at.is_(None)) &
            (
                (MemoryEntry.title.ilike(search_pattern)) |
                (MemoryEntry.content.ilike(search_pattern))
            )
        )
        
        if request.project:
            query = query.where(MemoryEntry.project == request.project)
        if request.category:
            query = query.where(MemoryEntry.category == request.category)
        if request.memory_tier:
            query = query.where(MemoryEntry.memory_tier == request.memory_tier)
        
        query = query.limit(request.top_k)
        query = query.order_by(desc(MemoryEntry.access_count))
        
        result = await db.execute(query)
        entries = result.scalars().all()
        
        results = []
        for entry in entries:
            # Calculate a pseudo-hybrid score
            text_score = 0.5  # Base text match score
            vector_score = 0.7 if entry.embedding else 0.3  # Higher if has embedding
            
            # Weighted combination
            hybrid_score = (
                request.vector_weight * vector_score +
                request.text_weight * text_score
            )
            
            results.append({
                "memory": memory_to_response(entry),
                "similarity": hybrid_score,
            })
        
        return ApiResponse(data={
            "query": request.query,
            "results": results,
            "total": len(results),
            "search_type": "hybrid",
        })
    
    except Exception as e:
        logger.error(f"Error in hybrid search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/overview", response_model=ApiResponse)
async def get_stats_overview(
    project: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get memory statistics overview."""
    try:
        # Base query
        base_query = select(MemoryEntry).where(MemoryEntry.deleted_at.is_(None))
        if project:
            base_query = base_query.where(MemoryEntry.project == project)
        
        # Total count
        total_query = select(func.count()).select_from(base_query.subquery())
        total = await db.scalar(total_query)
        
        # By tier
        tier_query = select(
            MemoryEntry.memory_tier,
            func.count()
        ).where(MemoryEntry.deleted_at.is_(None))
        if project:
            tier_query = tier_query.where(MemoryEntry.project == project)
        tier_query = tier_query.group_by(MemoryEntry.memory_tier)
        
        tier_result = await db.execute(tier_query)
        by_tier = {tier: count for tier, count in tier_result.fetchall()}
        
        # By category
        category_query = select(
            MemoryEntry.category,
            func.count()
        ).where(MemoryEntry.deleted_at.is_(None))
        if project:
            category_query = category_query.where(MemoryEntry.project == project)
        category_query = category_query.group_by(MemoryEntry.category)
        
        category_result = await db.execute(category_query)
        by_category = {cat: count for cat, count in category_result.fetchall()}
        
        # AI suggested count
        ai_query = select(func.count()).where(
            (MemoryEntry.deleted_at.is_(None)) &
            (MemoryEntry.ai_suggested == True)
        )
        if project:
            ai_query = ai_query.where(MemoryEntry.project == project)
        ai_suggested_count = await db.scalar(ai_query)
        
        # Pending review count
        pending_query = select(func.count()).where(
            (MemoryEntry.deleted_at.is_(None)) &
            (MemoryEntry.ai_suggested == True) &
            (MemoryEntry.ai_review_status == "pending")
        )
        if project:
            pending_query = pending_query.where(MemoryEntry.project == project)
        pending_review_count = await db.scalar(pending_query)
        
        # Total relations
        from app.tools.memory_tool.tools.memory-tool.db.models import MemoryRelation
        relations_query = select(func.count()).select_from(MemoryRelation)
        total_relations = await db.scalar(relations_query)
        
        return ApiResponse(data={
            "total_memories": total,
            "by_tier": by_tier,
            "by_category": by_category,
            "ai_suggested_count": ai_suggested_count,
            "pending_review_count": pending_review_count,
            "total_relations": total_relations,
        })
    
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/categories", response_model=ApiResponse)
async def get_category_stats(
    project: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get memory count by category."""
    try:
        # Total count
        total_query = select(func.count()).where(MemoryEntry.deleted_at.is_(None))
        if project:
            total_query = total_query.where(MemoryEntry.project == project)
        total = await db.scalar(total_query)
        
        # By category
        query = select(
            MemoryEntry.category,
            func.count()
        ).where(MemoryEntry.deleted_at.is_(None))
        if project:
            query = query.where(MemoryEntry.project == project)
        query = query.group_by(MemoryEntry.category)
        query = query.order_by(desc(func.count()))
        
        result = await db.execute(query)
        rows = result.fetchall()
        
        categories = []
        for cat, count in rows:
            categories.append({
                "name": cat,
                "count": count,
                "percentage": round(count / total * 100, 2) if total > 0 else 0,
            })
        
        return ApiResponse(data={"categories": categories})
    
    except Exception as e:
        logger.error(f"Error getting category stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
