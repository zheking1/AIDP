from typing import Any, Optional
from pydantic import BaseModel


class ToolInstallRequest(BaseModel):
    source: str
    install_mode: str = "managed"
    base_url: Optional[str] = None
    config: dict = {}


class ToolInfo(BaseModel):
    id: str
    name: str
    display_name: str
    version: str
    description: Optional[str] = None
    status: str
    install_mode: str
    base_url: Optional[str] = None
    manifest: dict = {}
    config: dict = {}
    last_health_status: Optional[str] = None
    installed_at: str
    updated_at: str


class ToolCapabilityInfo(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    endpoint: str
    permission: Optional[str] = None
    input_schema: dict = {}
    output_schema: dict = {}
    timeout_ms: int = 3000
    risk_level: str = "low"
    enabled: bool = True


class ToolInvokeRequest(BaseModel):
    trace_id: Optional[str] = None
    workspace_id: Optional[str] = None
    project_id: Optional[str] = None
    session_id: Optional[str] = None
    capability: str
    input: dict = {}


class ToolInvokeResponse(BaseModel):
    trace_id: str
    tool: str
    capability: str
    success: bool
    output: Any = None
    error: Optional[dict] = None
    elapsed_ms: int = 0
