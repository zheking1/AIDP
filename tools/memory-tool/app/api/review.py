"""Review Queue API Routes.

AI-suggested memory review management.
"""
import logging
from typing import Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import MemoryEntry
from app.schemas.memory import (
    ReviewRequest,
    ReviewQueueResponse,
    MemoryResponse,
    ApiResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/memories/review", tags=["review-queue"])


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
        "ai_review_comment": entry.ai_review_comment,
        "access_count": entry.access_count or 0,
        "source_type": entry.source_type,
        "has_embedding": entry.embedding is not None,
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
    }


@router.get("/queue", response_model=ApiResponse)
async def get_review_queue(
    status: str = Query("pending", description="Filter by status: pending|approved|rejected|all"),
    project: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get AI-suggested memories pending review.
    
    Returns memories where ai_suggested=True and optionally filtered by review status.
    """
    try:
        # Build base query
        query = select(MemoryEntry).where(
            (MemoryEntry.ai_suggested == True) &
            (MemoryEntry.deleted_at.is_(None))
        )
        
        # Filter by status
        if status != "all":
            query = query.where(MemoryEntry.ai_review_status == status)
        
        # Additional filters
        if project:
            query = query.where(MemoryEntry.project == project)
        if category:
            query = query.where(MemoryEntry.category == category)
        
        # Get counts by status
        counts_query = select(
            MemoryEntry.ai_review_status,
            func.count()
        ).where(
            (MemoryEntry.ai_suggested == True) &
            (MemoryEntry.deleted_at.is_(None))
        ).group_by(MemoryEntry.ai_review_status)
        
        counts_result = await db.execute(counts_query)
        counts = {status: count for status, count in counts_result.fetchall()}
        
        # Get total for pagination
        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query)
        
        # Apply pagination and sorting (oldest first for review)
        offset = (page - 1) * page_size
        query = query.order_by(asc(MemoryEntry.created_at))
        query = query.offset(offset).limit(page_size)
        
        result = await db.execute(query)
        memories = result.scalars().all()
        
        return ApiResponse(data={
            "items": [memory_to_response(m) for m in memories],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size,
            "pending_count": counts.get("pending", 0),
            "approved_count": counts.get("approved", 0),
            "rejected_count": counts.get("rejected", 0),
        })
    
    except Exception as e:
        logger.error(f"Error getting review queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{memory_id}", response_model=ApiResponse)
async def review_memory(
    memory_id: UUID,
    request: ReviewRequest,
    reviewer_id: Optional[str] = Query(None, description="ID of the reviewer"),
    db: AsyncSession = Depends(get_db),
):
    """Approve or reject AI-suggested memory.
    
    Status can be:
    - approved: Memory is accepted and will be used
    - rejected: Memory is rejected and should be reviewed or deleted
    """
    try:
        # Validate status
        if request.status not in ["approved", "rejected"]:
            raise HTTPException(
                status_code=400,
                detail="Status must be 'approved' or 'rejected'"
            )
        
        # Get memory
        result = await db.execute(
            select(MemoryEntry).where(
                (MemoryEntry.id == memory_id) &
                (MemoryEntry.deleted_at.is_(None))
            )
        )
        memory = result.scalar_one_or_none()
        
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        if not memory.ai_suggested:
            raise HTTPException(
                status_code=400,
                detail="Only AI-suggested memories can be reviewed"
            )
        
        # Update review status
        memory.ai_review_status = request.status
        memory.ai_review_comment = request.comment
        # Store reviewer info in source_uri or another field if needed
        
        await db.commit()
        await db.refresh(memory)
        
        logger.info(f"Memory {memory_id} reviewed: {request.status}")
        
        # If rejected, optionally soft delete or mark specially
        if request.status == "rejected":
            # Option: Soft delete rejected memories
            # memory.deleted_at = datetime.utcnow()
            # await db.commit()
            pass
        
        return ApiResponse(
            message=f"Memory {request.status} successfully",
            data=memory_to_response(memory)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reviewing memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{memory_id}/reset", response_model=ApiResponse)
async def reset_review(
    memory_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Reset memory review status to pending.
    
    Useful for re-reviewing previously approved/rejected memories.
    """
    try:
        result = await db.execute(
            select(MemoryEntry).where(
                (MemoryEntry.id == memory_id) &
                (MemoryEntry.deleted_at.is_(None))
            )
        )
        memory = result.scalar_one_or_none()
        
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        if not memory.ai_suggested:
            raise HTTPException(
                status_code=400,
                detail="Only AI-suggested memories can be reset"
            )
        
        memory.ai_review_status = "pending"
        memory.ai_review_comment = None
        
        await db.commit()
        await db.refresh(memory)
        
        return ApiResponse(
            message="Memory review status reset to pending",
            data=memory_to_response(memory)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", response_model=ApiResponse)
async def batch_review(
    memory_ids: list[UUID],
    request: ReviewRequest,
    reviewer_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Batch approve or reject multiple memories.
    
    Useful for bulk operations on the review queue.
    """
    try:
        if request.status not in ["approved", "rejected"]:
            raise HTTPException(
                status_code=400,
                detail="Status must be 'approved' or 'rejected'"
            )
        
        updated_count = 0
        
        for memory_id in memory_ids:
            result = await db.execute(
                select(MemoryEntry).where(
                    (MemoryEntry.id == memory_id) &
                    (MemoryEntry.deleted_at.is_(None)) &
                    (MemoryEntry.ai_suggested == True)
                )
            )
            memory = result.scalar_one_or_none()
            
            if memory:
                memory.ai_review_status = request.status
                memory.ai_review_comment = request.comment
                updated_count += 1
        
        await db.commit()
        
        logger.info(f"Batch reviewed {updated_count} memories: {request.status}")
        
        return ApiResponse(
            message=f"{updated_count} memories {request.status} successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=ApiResponse)
async def get_review_stats(
    project: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get review queue statistics.
    
    Returns counts and trends for the review queue.
    """
    try:
        # Base query for AI-suggested memories
        base_query = select(MemoryEntry).where(
            (MemoryEntry.ai_suggested == True) &
            (MemoryEntry.deleted_at.is_(None))
        )
        
        if project:
            base_query = base_query.where(MemoryEntry.project == project)
        
        # Count by status
        status_query = select(
            MemoryEntry.ai_review_status,
            func.count()
        ).where(
            (MemoryEntry.ai_suggested == True) &
            (MemoryEntry.deleted_at.is_(None))
        )
        
        if project:
            status_query = status_query.where(MemoryEntry.project == project)
        
        status_query = status_query.group_by(MemoryEntry.ai_review_status)
        
        status_result = await db.execute(status_query)
        status_counts = {status: count for status, count in status_result.fetchall()}
        
        # Recent activity (last 7 days)
        from datetime import timedelta
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        recent_query = select(func.count()).where(
            (MemoryEntry.ai_suggested == True) &
            (MemoryEntry.created_at >= week_ago) &
            (MemoryEntry.deleted_at.is_(None))
        )
        
        if project:
            recent_query = recent_query.where(MemoryEntry.project == project)
        
        recent_count = await db.scalar(recent_query)
        
        # Total AI-suggested
        total_query = select(func.count()).where(
            (MemoryEntry.ai_suggested == True) &
            (MemoryEntry.deleted_at.is_(None))
        )
        
        if project:
            total_query = total_query.where(MemoryEntry.project == project)
        
        total = await db.scalar(total_query)
        
        return ApiResponse(data={
            "total": total,
            "pending": status_counts.get("pending", 0),
            "approved": status_counts.get("approved", 0),
            "rejected": status_counts.get("rejected", 0),
            "recent_7_days": recent_count,
            "approval_rate": (
                status_counts.get("approved", 0) / total * 100
                if total > 0 else 0
            ),
        })
    
    except Exception as e:
        logger.error(f"Error getting review stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
