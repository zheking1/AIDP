"""Context Package API Routes.

Context package management and generation.
"""
import json
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.memory_tool.db.database import get_db
from app.tools.memory_tool.db.models import MemoryEntry, ContextPackage
from app.tools.memory_tool.schemas.memory import (
    ContextPackageCreateRequest,
    ContextPackageResponse,
    ContextPackageDetailResponse,
    ContextPackageListResponse,
    GenerateContextRequest,
    GeneratedContextResponse,
    ApiResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/context-packages", tags=["context-packages"])


def estimate_tokens(text: str) -> int:
    """Estimate token count for text.
    
    Simple estimation: ~4 chars per token for English, ~2 chars for Chinese.
    """
    import re
    
    # Count Chinese characters
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    # Count other characters
    other_chars = len(text) - chinese_chars
    
    # Estimate tokens
    tokens = chinese_chars * 2 + (other_chars // 4)
    
    return max(1, tokens)


def generate_context_from_memories(
    memories: List[MemoryEntry],
    max_tokens: int,
    include_summaries: bool,
    format: str
) -> tuple[str, int]:
    """Generate context string from memories.
    
    Returns:
        Tuple of (context_string, actual_token_count)
    """
    sections = []
    current_tokens = 0
    used_memories = []
    
    # Header
    header = "# Context\n\n"
    header_tokens = estimate_tokens(header)
    
    if current_tokens + header_tokens > max_tokens:
        return "", 0
    
    sections.append(header)
    current_tokens += header_tokens
    
    # Project info
    projects = set(m.project for m in memories if m.project)
    if projects:
        project_section = f"## Projects\n{', '.join(projects)}\n\n"
        project_tokens = estimate_tokens(project_section)
        if current_tokens + project_tokens <= max_tokens:
            sections.append(project_section)
            current_tokens += project_tokens
    
    # Memory summaries
    sections.append("## Relevant Memories\n\n")
    current_tokens += estimate_tokens("## Relevant Memories\n\n")
    
    for memory in memories:
        if format == "markdown":
            # Format as markdown
            memory_text = f"### {memory.title}\n"
            if include_summaries:
                content = memory.content[:500] + "..." if len(memory.content) > 500 else memory.content
                memory_text += f"**Category:** {memory.category} | **Tier:** {memory.memory_tier}\n\n"
                memory_text += f"{content}\n\n"
            else:
                memory_text += f"*{memory.category}*\n\n"
        elif format == "json":
            memory_text = json.dumps({
                "id": str(memory.id),
                "title": memory.title,
                "category": memory.category,
                "content": memory.content[:300] if include_summaries else "",
            }, ensure_ascii=False) + "\n\n"
        else:
            # XML format
            memory_text = f"<memory id=\"{memory.id}\">\n"
            memory_text += f"  <title>{memory.title}</title>\n"
            memory_text += f"  <category>{memory.category}</category>\n"
            if include_summaries:
                content = memory.content[:300].replace("<", "&lt;").replace(">", "&gt;")
                memory_text += f"  <content>{content}</content>\n"
            memory_text += "</memory>\n\n"
        
        memory_tokens = estimate_tokens(memory_text)
        
        if current_tokens + memory_tokens > max_tokens:
            break
        
        sections.append(memory_text)
        current_tokens += memory_tokens
        used_memories.append(memory.id)
    
    # Footer
    footer = f"\n---\n*Context generated from {len(used_memories)} memories*"
    footer_tokens = estimate_tokens(footer)
    
    if current_tokens + footer_tokens <= max_tokens:
        sections.append(footer)
        current_tokens += footer_tokens
    
    return "".join(sections), current_tokens


# ============================================================================
# Context Package CRUD
# ============================================================================

@router.get("", response_model=ApiResponse)
async def list_context_packages(
    project: Optional[str] = Query(None),
    is_template: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List saved context packages."""
    try:
        query = select(ContextPackage)
        
        if project:
            query = query.where(ContextPackage.project == project)
        if is_template is not None:
            query = query.where(ContextPackage.is_template == is_template)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query)
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.order_by(desc(ContextPackage.created_at))
        query = query.offset(offset).limit(page_size)
        
        result = await db.execute(query)
        packages = result.scalars().all()
        
        return ApiResponse(data={
            "items": [pkg.to_dict() for pkg in packages],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size,
        })
    
    except Exception as e:
        logger.error(f"Error listing context packages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=ApiResponse, status_code=201)
async def create_context_package(
    request: ContextPackageCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new context package."""
    try:
        # Convert memory_ids to JSON string
        memory_ids_json = json.dumps([str(id) for id in request.memory_ids])
        
        # Calculate tokens if memories provided
        total_tokens = 0
        if request.memory_ids:
            memories_result = await db.execute(
                select(MemoryEntry).where(
                    MemoryEntry.id.in_(request.memory_ids),
                    MemoryEntry.deleted_at.is_(None)
                )
            )
            memories = memories_result.scalars().all()
            
            context_text, total_tokens = generate_context_from_memories(
                memories, 8000, True, "markdown"
            )
        else:
            context_text = None
        
        package = ContextPackage(
            name=request.name,
            description=request.description,
            project=request.project,
            memory_ids=memory_ids_json,
            generated_context=context_text,
            total_tokens=total_tokens,
            is_template=request.is_template,
        )
        
        db.add(package)
        await db.commit()
        await db.refresh(package)
        
        logger.info(f"Created context package: {package.id}")
        
        return ApiResponse(
            message="Context package created successfully",
            data=package.to_dict(include_context=True)
        )
    
    except Exception as e:
        logger.error(f"Error creating context package: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{package_id}", response_model=ApiResponse)
async def get_context_package(
    package_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get context package details."""
    try:
        result = await db.execute(
            select(ContextPackage).where(ContextPackage.id == package_id)
        )
        package = result.scalar_one_or_none()
        
        if not package:
            raise HTTPException(status_code=404, detail="Context package not found")
        
        # Increment usage count
        package.usage_count = (package.usage_count or 0) + 1
        await db.commit()
        
        return ApiResponse(data=package.to_dict(include_context=True))
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting context package: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{package_id}", response_model=ApiResponse)
async def update_context_package(
    package_id: UUID,
    request: ContextPackageCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update a context package."""
    try:
        result = await db.execute(
            select(ContextPackage).where(ContextPackage.id == package_id)
        )
        package = result.scalar_one_or_none()
        
        if not package:
            raise HTTPException(status_code=404, detail="Context package not found")
        
        package.name = request.name
        package.description = request.description
        package.project = request.project
        package.memory_ids = json.dumps([str(id) for id in request.memory_ids])
        package.is_template = request.is_template
        
        # Regenerate context if memories changed
        if request.memory_ids:
            memories_result = await db.execute(
                select(MemoryEntry).where(
                    MemoryEntry.id.in_(request.memory_ids),
                    MemoryEntry.deleted_at.is_(None)
                )
            )
            memories = memories_result.scalars().all()
            
            context_text, total_tokens = generate_context_from_memories(
                memories, 8000, True, "markdown"
            )
            package.generated_context = context_text
            package.total_tokens = total_tokens
        
        await db.commit()
        await db.refresh(package)
        
        return ApiResponse(
            message="Context package updated successfully",
            data=package.to_dict(include_context=True)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating context package: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{package_id}", response_model=ApiResponse)
async def delete_context_package(
    package_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a context package."""
    try:
        result = await db.execute(
            select(ContextPackage).where(ContextPackage.id == package_id)
        )
        package = result.scalar_one_or_none()
        
        if not package:
            raise HTTPException(status_code=404, detail="Context package not found")
        
        await db.delete(package)
        await db.commit()
        
        return ApiResponse(message="Context package deleted successfully")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting context package: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Context Generation
# ============================================================================

@router.post("/generate", response_model=ApiResponse)
async def generate_context(
    request: GenerateContextRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate context string from selected memories."""
    try:
        # Fetch memories
        memories_result = await db.execute(
            select(MemoryEntry).where(
                MemoryEntry.id.in_(request.memory_ids),
                MemoryEntry.deleted_at.is_(None)
            )
        )
        memories = memories_result.scalars().all()
        
        if not memories:
            raise HTTPException(status_code=404, detail="No memories found")
        
        # Update access count for used memories
        for memory in memories:
            memory.access_count = (memory.access_count or 0) + 1
        
        await db.commit()
        
        # Generate context
        context_text, total_tokens = generate_context_from_memories(
            memories,
            request.max_tokens,
            request.include_summaries,
            request.format
        )
        
        return ApiResponse(data={
            "context": context_text,
            "total_tokens": total_tokens,
            "memory_count": len(memories),
            "memories_used": [str(m.id) for m in memories],
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preview", response_model=ApiResponse)
async def preview_context(
    request: GenerateContextRequest,
    db: AsyncSession = Depends(get_db),
):
    """Preview context generation without saving."""
    # Same as generate but don't update access counts
    try:
        memories_result = await db.execute(
            select(MemoryEntry).where(
                MemoryEntry.id.in_(request.memory_ids),
                MemoryEntry.deleted_at.is_(None)
            )
        )
        memories = memories_result.scalars().all()
        
        if not memories:
            raise HTTPException(status_code=404, detail="No memories found")
        
        context_text, total_tokens = generate_context_from_memories(
            memories,
            request.max_tokens,
            request.include_summaries,
            request.format
        )
        
        return ApiResponse(data={
            "context": context_text,
            "total_tokens": total_tokens,
            "memory_count": len(memories),
            "memories_used": [str(m.id) for m in memories],
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing context: {e}")
        raise HTTPException(status_code=500, detail=str(e))
