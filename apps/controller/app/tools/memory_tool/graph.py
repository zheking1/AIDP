"""Memory Graph API Routes.

Graph visualization and relationship management.
"""
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.memory_tool.tools.memory-tool.db.database import get_db
from app.tools.memory_tool.tools.memory-tool.db.models import MemoryEntry, MemoryRelation
from app.tools.memory_tool.tools.memory-tool.schemas.memory import (
    GraphDataResponse,
    GraphNode,
    GraphLink,
    RelationCreateRequest,
    RelationResponse,
    AutoGenerateRelationsRequest,
    AutoGenerateRelationsResponse,
    NeighborResponse,
    ApiResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/memories", tags=["memory-graph"])


# ============================================================================
# Graph Data
# ============================================================================

@router.get("/graph/data", response_model=ApiResponse)
async def get_graph_data(
    project: Optional[str] = Query(None, description="Filter by project"),
    category: Optional[str] = Query(None, description="Filter by category"),
    max_nodes: int = Query(100, ge=10, le=500, description="Maximum nodes to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get graph data for D3.js visualization."""
    try:
        # Build query for nodes
        query = select(MemoryEntry).where(MemoryEntry.deleted_at.is_(None))
        
        if project:
            query = query.where(MemoryEntry.project == project)
        if category:
            query = query.where(MemoryEntry.category == category)
        
        # Order by access count to get most relevant memories
        query = query.order_by(desc(MemoryEntry.access_count))
        query = query.limit(max_nodes)
        
        result = await db.execute(query)
        entries = result.scalars().all()
        
        # Convert to graph nodes
        nodes = []
        node_ids = set()
        for entry in entries:
            node_ids.add(str(entry.id))
            nodes.append(GraphNode(
                id=str(entry.id),
                title=entry.title,
                category=entry.category,
                memory_tier=entry.memory_tier,
                confidence_score=entry.confidence_score,
                access_count=entry.access_count or 0,
            ))
        
        # Get relations between these nodes
        if node_ids:
            # Convert string IDs back to UUIDs for the query
            from uuid import UUID
            uuid_ids = [UUID(id_str) for id_str in node_ids]
            
            links_result = await db.execute(
                select(MemoryRelation).where(
                    (MemoryRelation.source_id.in_(uuid_ids)) |
                    (MemoryRelation.target_id.in_(uuid_ids))
                )
            )
            relations = links_result.scalars().all()
            
            # Convert to graph links (only include if both nodes are in the set)
            links = []
            for relation in relations:
                source_id = str(relation.source_id)
                target_id = str(relation.target_id)
                if source_id in node_ids and target_id in node_ids:
                    links.append(GraphLink(
                        source=source_id,
                        target=target_id,
                        relation_type=relation.relation_type,
                        strength=relation.strength,
                    ))
        else:
            links = []
        
        return ApiResponse(data={
            "nodes": [node.dict() for node in nodes],
            "links": [link.dict() for link in links],
            "total_nodes": len(nodes),
            "total_links": len(links),
        })
    
    except Exception as e:
        logger.error(f"Error getting graph data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/neighbors/{memory_id}", response_model=ApiResponse)
async def get_neighbors(
    memory_id: UUID,
    depth: int = Query(1, ge=1, le=3, description="Hop depth"),
    db: AsyncSession = Depends(get_db),
):
    """Get neighboring memories for expansion."""
    try:
        # Get center memory
        result = await db.execute(
            select(MemoryEntry).where(
                (MemoryEntry.id == memory_id) &
                (MemoryEntry.deleted_at.is_(None))
            )
        )
        center = result.scalar_one_or_none()
        
        if not center:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        # Get neighbors (for now just depth 1)
        neighbors_result = await db.execute(
            select(MemoryRelation, MemoryEntry).join(
                MemoryEntry,
                (MemoryRelation.target_id == MemoryEntry.id) |
                (MemoryRelation.source_id == MemoryEntry.id)
            ).where(
                ((MemoryRelation.source_id == memory_id) |
                 (MemoryRelation.target_id == memory_id)) &
                (MemoryEntry.id != memory_id) &
                (MemoryEntry.deleted_at.is_(None))
            )
        )
        
        neighbors = neighbors_result.all()
        
        neighbor_list = []
        for relation, memory in neighbors:
            neighbor_list.append({
                "relation": {
                    "id": str(relation.id),
                    "type": relation.relation_type,
                    "strength": relation.strength,
                },
                "memory": {
                    "id": str(memory.id),
                    "title": memory.title,
                    "category": memory.category,
                    "memory_tier": memory.memory_tier,
                }
            })
        
        return ApiResponse(data={
            "center": {
                "id": str(center.id),
                "title": center.title,
                "category": center.category,
                "memory_tier": center.memory_tier,
            },
            "neighbors": neighbor_list,
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting neighbors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Relations Management
# ============================================================================

@router.post("/relations", response_model=ApiResponse, status_code=201)
async def create_relation(
    request: RelationCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a relationship between two memories."""
    try:
        # Validate relation type
        valid_types = ["similar", "parent_child", "reference", "sequence", "related"]
        if request.relation_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid relation_type. Must be one of: {valid_types}"
            )
        
        # Check if memories exist
        source_result = await db.execute(
            select(MemoryEntry).where(
                (MemoryEntry.id == request.source_id) &
                (MemoryEntry.deleted_at.is_(None))
            )
        )
        source = source_result.scalar_one_or_none()
        if not source:
            raise HTTPException(status_code=404, detail="Source memory not found")
        
        target_result = await db.execute(
            select(MemoryEntry).where(
                (MemoryEntry.id == request.target_id) &
                (MemoryEntry.deleted_at.is_(None))
            )
        )
        target = target_result.scalar_one_or_none()
        if not target:
            raise HTTPException(status_code=404, detail="Target memory not found")
        
        # Check if relation already exists
        existing_result = await db.execute(
            select(MemoryRelation).where(
                (MemoryRelation.source_id == request.source_id) &
                (MemoryRelation.target_id == request.target_id) &
                (MemoryRelation.relation_type == request.relation_type)
            )
        )
        if existing_result.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Relation already exists")
        
        # Create relation
        relation = MemoryRelation(
            source_id=request.source_id,
            target_id=request.target_id,
            relation_type=request.relation_type,
            strength=request.strength,
        )
        
        db.add(relation)
        await db.commit()
        await db.refresh(relation)
        
        logger.info(f"Created relation: {relation.id}")
        
        return ApiResponse(
            message="Relation created successfully",
            data={
                "id": str(relation.id),
                "source_id": str(relation.source_id),
                "target_id": str(relation.target_id),
                "relation_type": relation.relation_type,
                "strength": relation.strength,
                "created_at": relation.created_at,
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating relation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/relations/{relation_id}", response_model=ApiResponse)
async def delete_relation(
    relation_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a relationship."""
    try:
        result = await db.execute(
            select(MemoryRelation).where(MemoryRelation.id == relation_id)
        )
        relation = result.scalar_one_or_none()
        
        if not relation:
            raise HTTPException(status_code=404, detail="Relation not found")
        
        await db.delete(relation)
        await db.commit()
        
        logger.info(f"Deleted relation: {relation_id}")
        
        return ApiResponse(message="Relation deleted successfully")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting relation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/relations/auto-generate", response_model=ApiResponse)
async def auto_generate_relations(
    request: AutoGenerateRelationsRequest,
    db: AsyncSession = Depends(get_db),
):
    """Auto-generate relations based on category similarity."""
    try:
        # Get memories to process
        query = select(MemoryEntry).where(MemoryEntry.deleted_at.is_(None))
        if request.project:
            query = query.where(MemoryEntry.project == request.project)
        
        result = await db.execute(query)
        memories = result.scalars().all()
        
        created_count = 0
        
        # Simple similarity: same category = related
        for i, source in enumerate(memories):
            similar_memories = [
                m for m in memories
                if m.id != source.id and
                m.category == source.category and
                m.id > source.id  # Avoid duplicates
            ][:request.max_relations_per_memory]
            
            for target in similar_memories:
                # Check if relation exists
                existing = await db.execute(
                    select(MemoryRelation).where(
                        (MemoryRelation.source_id == source.id) &
                        (MemoryRelation.target_id == target.id) &
                        (MemoryRelation.relation_type == "related")
                    )
                )
                
                if not existing.scalar_one_or_none():
                    relation = MemoryRelation(
                        source_id=source.id,
                        target_id=target.id,
                        relation_type="related",
                        strength=request.similarity_threshold,
                    )
                    db.add(relation)
                    created_count += 1
        
        await db.commit()
        
        logger.info(f"Auto-generated {created_count} relations")
        
        return ApiResponse(
            message=f"Generated {created_count} relations",
            data={
                "created_count": created_count,
                "scanned_memories": len(memories),
            }
        )
    
    except Exception as e:
        logger.error(f"Error auto-generating relations: {e}")
        raise HTTPException(status_code=500, detail=str(e))
