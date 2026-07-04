from typing import Any, Optional
from pydantic import BaseModel


class AssetCreateRequest(BaseModel):
    workspace_id: str
    project_id: Optional[str] = None
    title: str
    asset_type: str
    language: Optional[str] = None
    format: Optional[str] = None
    visibility: str = "project"
    content: str
    description: Optional[str] = None
    tags: list[str] = []
    variables: dict = {}
    metadata: dict = {}


class AssetUpdateRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[list[str]] = None
    variables: Optional[dict] = None


class AssetInfo(BaseModel):
    id: str
    workspace_id: str
    project_id: Optional[str] = None
    title: str
    asset_type: str
    language: Optional[str] = None
    format: Optional[str] = None
    visibility: str
    content: str
    description: Optional[str] = None
    tags: list[str] = []
    variables: dict = {}
    created_at: str
    updated_at: str


class AssetSearchRequest(BaseModel):
    workspace_id: str
    project_id: Optional[str] = None
    query: str
    asset_type: Optional[str] = None
    language: Optional[str] = None
    tags: list[str] = []
    search_mode: str = "keyword"
    top_k: int = 8


class AssetSearchItem(BaseModel):
    id: str
    title: str
    asset_type: str
    language: Optional[str] = None
    content: str
    tags: list[str] = []
    score: float = 0.0


class AssetSearchResult(BaseModel):
    items: list[AssetSearchItem]
    total: int


class AssetRenderRequest(BaseModel):
    id: str
    variables: dict = {}


class AssetRenderResult(BaseModel):
    rendered: str
