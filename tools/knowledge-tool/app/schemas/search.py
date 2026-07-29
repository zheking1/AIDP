from typing import Any, Optional
from pydantic import BaseModel


class SearchRequest(BaseModel):
    workspace_id: Optional[str] = None
    project_id: Optional[str] = None
    knowledge_base_ids: Optional[list[str]] = None
    task_domains: Optional[list[str]] = None
    tech_keywords: Optional[list[str]] = None
    query: str
    doc_types: list[str] = []
    tags: list[str] = []
    visibility: list[str] = ["project", "workspace"]
    top_k: int = 8
    search_mode: str = "hybrid"
    min_score: float = 0.0
    include_content: bool = True
    enable_rerank: bool = False


class SearchItem(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    content: str
    score: float
    keyword_score: float = 0.0
    vector_score: float = 0.0
    version: str
    citation_id: str
    source_uri: Optional[str] = None
    heading_path: list[str] = []
    source_start_line: Optional[int] = None
    source_end_line: Optional[int] = None
    knowledge_base_id: Optional[str] = None
    kb_name: Optional[str] = None
    kb_level: Optional[str] = None
    metadata: dict = {}


class SearchResult(BaseModel):
    items: list[SearchItem]
    total: int
    degraded: bool = False
    degrade_reason: Optional[str] = None
    matched_kb_ids: list[str] = []
    reranked: bool = False
