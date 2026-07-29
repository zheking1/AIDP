from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.search_service import SearchService
from app.services.code_explore import CodeExploreService
from app.services.call_tracer import CallTracer
from app.services.indexer import Indexer

router = APIRouter(tags=["tool"])


class ToolInvokeRequest(BaseModel):
    trace_id: Optional[str] = None
    capability: str
    context: dict = {}
    input: dict = {}


class ToolInvokeResponse(BaseModel):
    trace_id: str
    tool: str
    capability: str
    success: bool
    output: Any = None
    error: Optional[dict] = None
    elapsed_ms: int = 0


@router.get("/tool/manifest")
async def get_manifest():
    return {
        "apiVersion": "aidp.dev/v1",
        "kind": "Tool",
        "metadata": {"name": "code-index", "displayName": "Code Index", "version": "0.1.0"},
        "runtime": {"modes": ["standalone"], "docker": {"image": "aidp/code-index:0.1.0", "port": 18086}},
        "capabilities": [
            {"name": "code.search", "endpoint": "POST /api/symbols/search", "timeoutMs": 3000, "permission": "code:read"},
            {"name": "code.search.semantic", "endpoint": "POST /api/search/semantic", "timeoutMs": 5000, "permission": "code:read"},
            {"name": "code.explore", "endpoint": "POST /api/explore", "timeoutMs": 3000, "permission": "code:read"},
            {"name": "code.calls", "endpoint": "POST /api/code/calls", "timeoutMs": 3000, "permission": "code:read"},
            {"name": "code.index_files", "endpoint": "POST /tool/invoke", "timeoutMs": 30000, "permission": "code:write"},
            {"name": "code.create_project", "endpoint": "POST /tool/invoke", "timeoutMs": 5000, "permission": "code:write"},
        ],
    }


@router.get("/tool/capabilities")
async def get_capabilities():
    return {
        "tool": "code-index",
        "version": "0.1.0",
        "capabilities": [
            {"name": "code.search", "description": "Search code symbols.", "permission": "code:read", "endpoint": "POST /api/symbols/search", "timeout_ms": 3000, "input_schema": {"type": "object", "properties": {"query": {"type": "string"}, "top_k": {"type": "integer", "default": 8}}}},
            {"name": "code.search.semantic", "description": "Semantic search with vector+exact+fuzzy fusion.", "permission": "code:read", "endpoint": "POST /api/search/semantic", "timeout_ms": 5000, "input_schema": {"type": "object", "properties": {"project_id": {"type": "integer"}, "query": {"type": "string"}, "top_k": {"type": "integer", "default": 10}}}},
            {"name": "code.explore", "description": "Explore code structure. Valid actions: symbols, file, calls, dependents, structure, summary, callers, callees, impact.", "permission": "code:read", "endpoint": "POST /api/explore", "timeout_ms": 3000, "input_schema": {"type": "object", "properties": {"action": {"type": "string", "enum": ["symbols", "file", "calls", "dependents", "structure", "summary", "callers", "callees", "impact"]}, "query": {"type": "string"}}}},
            {"name": "code.calls", "description": "Trace function calls.", "permission": "code:read", "endpoint": "POST /api/code/calls", "timeout_ms": 3000, "input_schema": {"type": "object", "properties": {"function": {"type": "string"}, "depth": {"type": "integer", "default": 3}}}},
            {"name": "code.index_files", "description": "Batch index files with content (for local code scanning).", "permission": "code:write", "endpoint": "POST /tool/invoke", "timeout_ms": 30000, "input_schema": {"type": "object", "properties": {"project_id": {"type": "integer"}, "files": {"type": "array", "items": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}, "language": {"type": "string"}}}}}}},
            {"name": "code.create_project", "description": "Create a project in code-index.", "permission": "code:write", "endpoint": "POST /tool/invoke", "timeout_ms": 5000, "input_schema": {"type": "object", "properties": {"name": {"type": "string"}, "path": {"type": "string"}}}},
        ],
    }


@router.post("/tool/invoke", response_model=ToolInvokeResponse)
async def invoke_tool(req: ToolInvokeRequest, db: AsyncSession = Depends(get_db)):
    import time, uuid

    start = time.time()
    trace_id = req.trace_id or f"tr_{uuid.uuid4().hex[:12]}"
    inp = req.input

    try:
        if req.capability == "code.search":
            svc = SearchService(db)
            results = await svc.search_symbols(
                project_id=inp.get("project_id", 0),
                query=inp.get("query", ""),
                node_type=inp.get("node_type"),
                limit=inp.get("top_k", 8),
            )
            return ToolInvokeResponse(trace_id=trace_id, tool="code-index", capability=req.capability, success=True, output=results, elapsed_ms=int((time.time() - start) * 1000))

        elif req.capability == "code.search.semantic":
            svc = SearchService(db)
            results = await svc.semantic_search(
                project_id=inp.get("project_id", 0),
                query=inp.get("query", ""),
                top_k=inp.get("top_k", 10),
                node_type=inp.get("node_type"),
            )
            return ToolInvokeResponse(trace_id=trace_id, tool="code-index", capability=req.capability, success=True, output=results, elapsed_ms=int((time.time() - start) * 1000))

        elif req.capability == "code.explore":
            svc = CodeExploreService(db)
            results = await svc.explore(
                project_id=inp.get("project_id", 0),
                action=inp.get("action", "symbols"),
                params={"query": inp.get("query", ""), "limit": inp.get("limit", 50)},
            )
            return ToolInvokeResponse(trace_id=trace_id, tool="code-index", capability=req.capability, success=True, output=results, elapsed_ms=int((time.time() - start) * 1000))

        elif req.capability == "code.create_project":
            indexer = Indexer(db)
            project = await indexer.create_project(
                name=inp.get("name", ""),
                path=inp.get("path", ""),
            )
            return ToolInvokeResponse(trace_id=trace_id, tool="code-index", capability=req.capability, success=True, output={"project_id": project.id, "name": project.name, "path": project.path}, elapsed_ms=int((time.time() - start) * 1000))

        elif req.capability == "code.index_files":
            files = inp.get("files", [])
            project_id = inp.get("project_id")
            if not project_id or not files:
                return ToolInvokeResponse(trace_id=trace_id, tool="code-index", capability=req.capability, success=False, error={"code": "VALIDATION_ERROR", "message": "project_id and files required"}, elapsed_ms=int((time.time() - start) * 1000))
            indexer = Indexer(db)
            result = await indexer.index_files(project_id, files)
            return ToolInvokeResponse(trace_id=trace_id, tool="code-index", capability=req.capability, success=True, output=result, elapsed_ms=int((time.time() - start) * 1000))

        elif req.capability == "code.calls":
            tracer = CallTracer(db)
            node_id = inp.get("node_id")
            project_id = inp.get("project_id", 0)
            depth = inp.get("depth", 3)
            callers = await tracer.get_callers(node_id, project_id, depth)
            callees = await tracer.get_callees(node_id, project_id, depth)
            return ToolInvokeResponse(trace_id=trace_id, tool="code-index", capability=req.capability, success=True, output={"callers": callers, "callees": callees}, elapsed_ms=int((time.time() - start) * 1000))

        return ToolInvokeResponse(trace_id=trace_id, tool="code-index", capability=req.capability, success=False, error={"code": "NOT_FOUND", "message": f"Capability '{req.capability}' not found"}, elapsed_ms=int((time.time() - start) * 1000))

    except Exception as e:
        return ToolInvokeResponse(trace_id=trace_id, tool="code-index", capability=req.capability, success=False, error={"code": "INTERNAL_ERROR", "message": str(e)}, elapsed_ms=int((time.time() - start) * 1000))