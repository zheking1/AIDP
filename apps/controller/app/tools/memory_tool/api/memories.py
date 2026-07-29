"""Memory API Routes.

CRUD operations and advanced features for memory management.
"""
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc, asc, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.memory_tool.db.database import get_db
from app.tools.memory_tool.db.models import MemoryEntry, MemoryRelation, ContextPackage
from app.tools.memory_tool.schemas.memory import (
    MemoryCreateRequest,
    MemoryUpdateRequest,
    MemoryResponse,
    MemoryDetailResponse,
    MemoryListResponse,
    ApiResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/memories", tags=["memories"])


# ============================================================================
# Helper Functions
# ============================================================================

def memory_to_response(entry: MemoryEntry, include_content: bool = False) -> dict:
    """Convert MemoryEntry to response dict."""
    data = {
        "id": entry.id,
        "project": entry.project,
        "user_id": entry.user_id,
        "category": entry.category,
        "title": entry.title,
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
    
    if include_content:
        data["content"] = entry.content
        data["content_preview"] = entry.content[:500] + "..." if len(entry.content) > 500 else entry.content
    else:
        data["content_preview"] = entry.content[:200] + "..." if len(entry.content) > 200 else entry.content
    
    return data


# ============================================================================
# CRUD Operations
# ============================================================================

@router.get("", response_model=ApiResponse)
async def list_memories(
    project: Optional[str] = Query(None, description="Filter by project"),
    category: Optional[str] = Query(None, description="Filter by category"),
    memory_tier: Optional[str] = Query(None, description="Filter by tier: episodic|semantic|procedural"),
    search: Optional[str] = Query(None, description="Text search in title/content"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order: asc|desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List memories with filtering and pagination."""
    try:
        # Build query
        query = select(MemoryEntry).where(MemoryEntry.deleted_at.is_(None))
        
        if project:
            query = query.where(MemoryEntry.project == project)
        if category:
            query = query.where(MemoryEntry.category == category)
        if memory_tier:
            query = query.where(MemoryEntry.memory_tier == memory_tier)
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                (MemoryEntry.title.ilike(search_pattern)) |
                (MemoryEntry.content.ilike(search_pattern))
            )
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query)
        
        # Apply sorting
        sort_column = getattr(MemoryEntry, sort_by, MemoryEntry.created_at)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        # Execute query
        result = await db.execute(query)
        entries = result.scalars().all()
        
        # Convert to response
        items = [memory_to_response(entry) for entry in entries]
        pages = (total + page_size - 1) // page_size
        
        return ApiResponse(
            data={
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": pages,
            }
        )
    
    except Exception as e:
        logger.error(f"Error listing memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=ApiResponse, status_code=201)
async def create_memory(
    request: MemoryCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new memory entry."""
    try:
        # Validate category
        valid_categories = ["architecture", "decision", "pattern", "issue", "bug", "other"]
        if request.category not in valid_categories:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category. Must be one of: {valid_categories}"
            )
        
        # Validate memory_tier
        valid_tiers = ["episodic", "semantic", "procedural"]
        if request.memory_tier not in valid_tiers:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid memory_tier. Must be one of: {valid_tiers}"
            )
        
        # Create entry
        entry = MemoryEntry(
            project=request.project,
            category=request.category,
            title=request.title,
            content=request.content,
            memory_tier=request.memory_tier,
            parent_id=request.parent_id,
            confidence_score=request.confidence_score,
            source_type=request.source_type,
            source_uri=request.source_uri,
        )
        
        db.add(entry)
        await db.commit()
        await db.refresh(entry)
        
        logger.info(f"Created memory entry: {entry.id}")
        
        return ApiResponse(
            message="Memory created successfully",
            data=memory_to_response(entry, include_content=True)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{memory_id}", response_model=ApiResponse)
async def get_memory(
    memory_id: UUID,
    include_relations: bool = Query(True, description="Include related memories"),
    db: AsyncSession = Depends(get_db),
):
    """Get memory details by ID."""
    try:
        # Get memory entry
        result = await db.execute(
            select(MemoryEntry).where(
                (MemoryEntry.id == memory_id) &
                (MemoryEntry.deleted_at.is_(None))
            )
        )
        entry = result.scalar_one_or_none()
        
        if not entry:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        # Update access count
        entry.access_count = (entry.access_count or 0) + 1
        await db.commit()
        
        # Build response
        data = memory_to_response(entry, include_content=True)
        
        if include_relations:
            # Get parent
            if entry.parent_id:
                parent_result = await db.execute(
                    select(MemoryEntry).where(MemoryEntry.id == entry.parent_id)
                )
                parent = parent_result.scalar_one_or_none()
                if parent:
                    data["parent"] = memory_to_response(parent)
            
            # Get children
            children_result = await db.execute(
                select(MemoryEntry).where(
                    (MemoryEntry.parent_id == memory_id) &
                    (MemoryEntry.deleted_at.is_(None))
                )
            )
            children = children_result.scalars().all()
            data["children"] = [memory_to_response(child) for child in children]
            
            # Get outgoing relations
            outgoing_result = await db.execute(
                select(MemoryRelation, MemoryEntry).join(
                    MemoryEntry, MemoryRelation.target_id == MemoryEntry.id
                ).where(MemoryRelation.source_id == memory_id)
            )
            outgoing = outgoing_result.all()
            data["outgoing_relations"] = [
                {
                    "relation": {"id": r.id, "type": r.relation_type, "strength": r.strength},
                    "memory": memory_to_response(m)
                }
                for r, m in outgoing
            ]
            
            # Get incoming relations
            incoming_result = await db.execute(
                select(MemoryRelation, MemoryEntry).join(
                    MemoryEntry, MemoryRelation.source_id == MemoryEntry.id
                ).where(MemoryRelation.target_id == memory_id)
            )
            incoming = incoming_result.all()
            data["incoming_relations"] = [
                {
                    "relation": {"id": r.id, "type": r.relation_type, "strength": r.strength},
                    "memory": memory_to_response(m)
                }
                for r, m in incoming
            ]
        
        return ApiResponse(data=data)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{memory_id}", response_model=ApiResponse)
async def update_memory(
    memory_id: UUID,
    request: MemoryUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update memory by ID."""
    try:
        # Get memory entry
        result = await db.execute(
            select(MemoryEntry).where(
                (MemoryEntry.id == memory_id) &
                (MemoryEntry.deleted_at.is_(None))
            )
        )
        entry = result.scalar_one_or_none()
        
        if not entry:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        # Update fields
        if request.title is not None:
            entry.title = request.title
        if request.content is not None:
            entry.content = request.content
        if request.category is not None:
            entry.category = request.category
        if request.memory_tier is not None:
            entry.memory_tier = request.memory_tier
        if request.parent_id is not None:
            entry.parent_id = request.parent_id
        if request.confidence_score is not None:
            entry.confidence_score = request.confidence_score
        
        await db.commit()
        await db.refresh(entry)
        
        logger.info(f"Updated memory entry: {entry.id}")
        
        return ApiResponse(
            message="Memory updated successfully",
            data=memory_to_response(entry, include_content=True)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{memory_id}", response_model=ApiResponse)
async def delete_memory(
    memory_id: UUID,
    hard_delete: bool = Query(False, description="Permanently delete"),
    db: AsyncSession = Depends(get_db),
):
    """Delete memory by ID (soft delete by default)."""
    try:
        # Get memory entry
        result = await db.execute(
            select(MemoryEntry).where(
                (MemoryEntry.id == memory_id) &
                (MemoryEntry.deleted_at.is_(None))
            )
        )
        entry = result.scalar_one_or_none()
        
        if not entry:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        if hard_delete:
            # Hard delete
            await db.delete(entry)
            message = "Memory permanently deleted"
        else:
            # Soft delete
            from datetime import datetime
            entry.deleted_at = datetime.utcnow()
            message = "Memory deleted (soft)"
        
        await db.commit()
        
        logger.info(f"Deleted memory entry: {memory_id}")
        
        return ApiResponse(message=message)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))
