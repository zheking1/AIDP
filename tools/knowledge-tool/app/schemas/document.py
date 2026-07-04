from typing import Any, Optional
from pydantic import BaseModel


class DocumentCreateRequest(BaseModel):
    workspace_id: str
    project_id: Optional[str] = None
    title: str
    doc_type: str
    visibility: str = "project"
    version: str = "v1"
    tags: list[str] = []
    source_uri: Optional[str] = None
    content: Optional[str] = None
    metadata: dict = {}


class DocumentInfo(BaseModel):
    id: str
    workspace_id: str
    project_id: Optional[str] = None
    title: str
    doc_type: str
    visibility: str
    version: str
    index_status: str
    tags: list[str] = []
    checksum: Optional[str] = None
    created_at: str
    updated_at: str


class IndexJobRequest(BaseModel):
    workspace_id: str
    project_id: Optional[str] = None
    force: bool = False
    chunk_size: int = 800
    overlap: int = 120
    embedding_model: str = "mock-embedding-v1"


class IndexJobInfo(BaseModel):
    id: str
    document_id: str
    status: str
    chunk_count: Optional[int] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
