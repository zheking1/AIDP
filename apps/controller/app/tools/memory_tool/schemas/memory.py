"""Memory API Schemas.

Pydantic models for request/response validation.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


# ============================================================================
# Base Schemas
# ============================================================================

class MemoryBase(BaseModel):
    """Base memory schema."""
    project: Optional[str] = Field(None, max_length=100)
    category: str = Field(..., description="architecture|decision|pattern|issue|bug|other")
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)


class MemoryCreateRequest(BaseModel):
    """Request to create a memory."""
    project: Optional[str] = Field(None, max_length=100)
    category: str = Field(..., description="architecture|decision|pattern|issue|bug|other")
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    memory_tier: str = Field(default="semantic", description="episodic|semantic|procedural")
    parent_id: Optional[UUID] = None
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    source_type: str = Field(default="manual", description="manual|auto|imported|ai")
    source_uri: Optional[str] = Field(None, max_length=500)
    tags: List[str] = Field(default_factory=list)


class MemoryUpdateRequest(BaseModel):
    """Request to update a memory."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = None
    category: Optional[str] = None
    memory_tier: Optional[str] = None
    parent_id: Optional[UUID] = None
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    tags: Optional[List[str]] = None


class MemoryResponse(BaseModel):
    """Memory response."""
    id: UUID
    project: Optional[str]
    user_id: Optional[str]
    category: str
    title: str
    content_preview: str
    memory_tier: str
    parent_id: Optional[UUID]
    confidence_score: float
    ai_suggested: bool
    ai_review_status: str
    access_count: int
    source_type: str
    has_embedding: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MemoryDetailResponse(MemoryResponse):
    """Memory detail with full content and relations."""
    content: str
    parent: Optional[MemoryResponse] = None
    children: List[MemoryResponse] = Field(default_factory=list)
    outgoing_relations: List[Dict[str, Any]] = Field(default_factory=list)
    incoming_relations: List[Dict[str, Any]] = Field(default_factory=list)


class MemoryListResponse(BaseModel):
    """Paginated memory list."""
    items: List[MemoryResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ============================================================================
# Search Schemas
# ============================================================================

class VectorSearchRequest(BaseModel):
    """Vector similarity search request."""
    query: str = Field(..., min_length=1, description="Search query text")
    project: Optional[str] = None
    category: Optional[str] = None
    memory_tier: Optional[str] = None
    top_k: int = Field(default=10, ge=1, le=50)
    min_similarity: float = Field(default=0.7, ge=0.0, le=1.0)


class VectorSearchResult(BaseModel):
    """Single vector search result."""
    memory: MemoryResponse
    similarity: float


class VectorSearchResponse(BaseModel):
    """Vector search response."""
    query: str
    results: List[VectorSearchResult]
    total: int


class HybridSearchRequest(VectorSearchRequest):
    """Hybrid search request."""
    vector_weight: float = Field(default=0.7, ge=0.0, le=1.0)
    text_weight: float = Field(default=0.3, ge=0.0, le=1.0)


class HybridSearchResponse(VectorSearchResponse):
    """Hybrid search response."""
    pass


# ============================================================================
# Graph Schemas
# ============================================================================

class GraphNode(BaseModel):
    """D3.js graph node."""
    id: str
    title: str
    category: str
    memory_tier: str
    confidence_score: float
    access_count: int
    radius: float = Field(default=5.0, description="Node radius for visualization")
    color: str = Field(default="#3b82f6", description="Node color")


class GraphLink(BaseModel):
    """D3.js graph link."""
    source: str
    target: str
    relation_type: str
    strength: float
    color: str = Field(default="#94a3b8")


class GraphDataResponse(BaseModel):
    """Graph data for D3.js."""
    nodes: List[GraphNode]
    links: List[GraphLink]
    total_nodes: int
    total_links: int


class NeighborResponse(BaseModel):
    """Neighbor memories response."""
    center: MemoryResponse
    neighbors: List[Dict[str, Any]]


# ============================================================================
# Relation Schemas
# ============================================================================

class RelationCreateRequest(BaseModel):
    """Create relation request."""
    source_id: UUID
    target_id: UUID
    relation_type: str = Field(..., description="similar|parent_child|reference|sequence|related")
    strength: float = Field(default=0.5, ge=0.0, le=1.0)


class RelationResponse(BaseModel):
    """Relation response."""
    id: UUID
    source_id: UUID
    target_id: UUID
    relation_type: str
    strength: float
    created_at: datetime


class AutoGenerateRelationsRequest(BaseModel):
    """Auto-generate relations request."""
    project: Optional[str] = None
    similarity_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    max_relations_per_memory: int = Field(default=5, ge=1, le=20)


class AutoGenerateRelationsResponse(BaseModel):
    """Auto-generate response."""
    created_count: int
    scanned_memories: int


# ============================================================================
# Context Package Schemas
# ============================================================================

class ContextPackageCreateRequest(BaseModel):
    """Create context package."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    project: Optional[str] = None
    memory_ids: List[UUID] = Field(default_factory=list)
    is_template: bool = False


class GenerateContextRequest(BaseModel):
    """Generate context from memories."""
    memory_ids: List[UUID] = Field(..., min_length=1)
    max_tokens: int = Field(default=2000, ge=100, le=8000)
    include_summaries: bool = True
    format: str = Field(default="markdown", description="markdown|json|xml")


class GeneratedContextResponse(BaseModel):
    """Generated context response."""
    context: str
    total_tokens: int
    memory_count: int
    memories_used: List[UUID]


class ContextPackageResponse(BaseModel):
    """Context package response."""
    id: UUID
    name: str
    description: Optional[str]
    project: Optional[str]
    total_tokens: int
    memory_count: int
    is_template: bool
    usage_count: int
    created_at: datetime


class ContextPackageDetailResponse(ContextPackageResponse):
    """Context package with full details."""
    memory_ids: List[UUID]
    generated_context: Optional[str]


class ContextPackageListResponse(BaseModel):
    """List context packages."""
    items: List[ContextPackageResponse]
    total: int


# ============================================================================
# Review Queue Schemas
# ============================================================================

class ReviewRequest(BaseModel):
    """Review memory request."""
    status: str = Field(..., description="approved|rejected")
    comment: Optional[str] = None


class ReviewQueueResponse(BaseModel):
    """Review queue response."""
    items: List[MemoryResponse]
    total: int
    pending_count: int
    approved_count: int
    rejected_count: int


# ============================================================================
# Statistics Schemas
# ============================================================================

class StatsOverviewResponse(BaseModel):
    """Stats overview."""
    total_memories: int
    by_tier: Dict[str, int]
    by_category: Dict[str, int]
    ai_suggested_count: int
    pending_review_count: int
    total_relations: int


class CategoryStatsItem(BaseModel):
    """Category stats item."""
    name: str
    count: int
    percentage: float


class CategoryStatsResponse(BaseModel):
    """Category stats."""
    categories: List[CategoryStatsItem]


# ============================================================================
# Common Response
# ============================================================================

class ApiResponse(BaseModel):
    """Standard API response wrapper."""
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None
