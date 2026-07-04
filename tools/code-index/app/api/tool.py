from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Optional

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
            {"name": "code.explore", "endpoint": "POST /api/code/explore", "timeoutMs": 3000, "permission": "code:read"},
            {"name": "code.calls", "endpoint": "POST /api/code/calls", "timeoutMs": 3000, "permission": "code:read"},
        ],
    }


@router.get("/tool/capabilities")
async def get_capabilities():
    return {
        "tool": "code-index",
        "version": "0.1.0",
        "capabilities": [
            {"name": "code.search", "description": "Search code symbols.", "permission": "code:read", "endpoint": "POST /api/symbols/search", "timeout_ms": 3000, "input_schema": {"type": "object", "properties": {"query": {"type": "string"}, "top_k": {"type": "integer", "default": 8}}}},
            {"name": "code.explore", "description": "Explore code structure.", "permission": "code:read", "endpoint": "POST /api/code/explore", "timeout_ms": 3000, "input_schema": {"type": "object", "properties": {"action": {"type": "string"}, "query": {"type": "string"}}}},
            {"name": "code.calls", "description": "Trace function calls.", "permission": "code:read", "endpoint": "POST /api/code/calls", "timeout_ms": 3000, "input_schema": {"type": "object", "properties": {"function": {"type": "string"}, "depth": {"type": "integer", "default": 3}}}},
        ],
    }


@router.post("/tool/invoke", response_model=ToolInvokeResponse)
async def invoke_tool(req: ToolInvokeRequest):
    import time, uuid

    start = time.time()
    trace_id = req.trace_id or f"tr_{uuid.uuid4().hex[:12]}"
    inp = req.input

    try:
        if req.capability == "code.search":
            from app.services.search_service import search_symbols
            results = await search_symbols(query=inp.get("query", ""), limit=inp.get("top_k", 8))
            return ToolInvokeResponse(trace_id=trace_id, tool="code-index", capability=req.capability, success=True, output=results, elapsed_ms=int((time.time() - start) * 1000))

        elif req.capability == "code.explore":
            from app.services.code_explore import explore_code
            results = await explore_code(action=inp.get("action", "symbols"), query=inp.get("query", ""))
            return ToolInvokeResponse(trace_id=trace_id, tool="code-index", capability=req.capability, success=True, output=results, elapsed_ms=int((time.time() - start) * 1000))

        elif req.capability == "code.calls":
            from app.services.call_tracer import trace_calls
            results = await trace_calls(function_name=inp.get("function", ""), depth=inp.get("depth", 3))
            return ToolInvokeResponse(trace_id=trace_id, tool="code-index", capability=req.capability, success=True, output=results, elapsed_ms=int((time.time() - start) * 1000))

        return ToolInvokeResponse(trace_id=trace_id, tool="code-index", capability=req.capability, success=False, error={"code": "NOT_FOUND", "message": f"Capability '{req.capability}' not found"}, elapsed_ms=int((time.time() - start) * 1000))

    except Exception as e:
        return ToolInvokeResponse(trace_id=trace_id, tool="code-index", capability=req.capability, success=False, error={"code": "INTERNAL_ERROR", "message": str(e)}, elapsed_ms=int((time.time() - start) * 1000))