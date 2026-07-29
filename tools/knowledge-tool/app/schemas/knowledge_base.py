from typing import Optional
from pydantic import BaseModel


class KnowledgeBaseCreate(BaseModel):
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    kb_level: str = "project"
    parent_id: Optional[str] = None
    domains: list[str] = []
    keywords: list[str] = []
    tech_stack: list[str] = []
    visibility: str = "private"
    chunk_size: int = 512
    overlap_size: int = 50
    embedding_model: str = "text-embedding-3-small"


class KnowledgeBaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    domains: Optional[list[str]] = None
    keywords: Optional[list[str]] = None
    tech_stack: Optional[list[str]] = None
    visibility: Optional[str] = None
    chunk_size: Optional[int] = None
    overlap_size: Optional[int] = None
    embedding_model: Optional[str] = None


class KnowledgeBaseInfo(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str] = None
    kb_level: str
    parent_id: Optional[str] = None
    parent_name: Optional[str] = None
    domains: list[str] = []
    keywords: list[str] = []
    tech_stack: list[str] = []
    visibility: str
    chunk_size: int
    embedding_model: str
    document_count: int = 0
    children: list["KnowledgeBaseInfo"] = []
    ancestors: list[dict] = []
    created_at: str
    updated_at: str


class ProjectBindingCreate(BaseModel):
    project_id: str
    knowledge_base_id: str
    binding_type: str = "explicit"
    priority: int = 0


class ProjectBindingInfo(BaseModel):
    id: str
    project_id: str
    knowledge_base_id: str
    kb_name: Optional[str] = None
    kb_slug: Optional[str] = None
    kb_level: Optional[str] = None
    binding_type: str
    priority: int
    created_at: str


class AutoMatchRequest(BaseModel):
    project_id: str
    tech_stack: list[str] = []
    domains: list[str] = []


class AutoMatchResult(BaseModel):
    matched: list[dict]
    total: int