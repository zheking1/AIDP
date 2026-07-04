import time
import uuid
from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings
from app.services.execution_service import execute_code, get_history

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
        "metadata": {
            "name": settings.APP_NAME,
            "displayName": "Sandbox Tool",
            "version": settings.APP_VERSION,
            "description": "Code execution sandbox for Python/Bash.",
        },
        "runtime": {
            "modes": ["standalone", "managed"],
            "docker": {
                "image": f"aidp/{settings.APP_NAME}:{settings.APP_VERSION}",
                "port": settings.PORT,
            },
        },
        "capabilities": [
            {
                "name": "sandbox.execute",
                "description": "Execute code in a sandboxed environment.",
                "endpoint": "POST /api/execute",
                "timeoutMs": 35000,
                "permission": "sandbox:execute",
            },
            {
                "name": "sandbox.history",
                "description": "Get execution history.",
                "endpoint": "GET /api/execute/history",
                "timeoutMs": 3000,
                "permission": "sandbox:read",
            },
        ],
    }


@router.get("/tool/capabilities")
async def get_capabilities():
    return {
        "tool": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "capabilities": [
            {
                "name": "sandbox.execute",
                "description": "Execute code in a sandboxed environment.",
                "permission": "sandbox:execute",
                "endpoint": "POST /api/execute",
                "timeout_ms": 35000,
                "input_schema": {
                    "type": "object",
                    "required": ["code"],
                    "properties": {
                        "code": {"type": "string"},
                        "language": {"type": "string", "enum": ["python", "bash", "sh"], "default": "python"},
                        "stdin": {"type": "string"},
                    },
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "stdout": {"type": "string"},
                        "stderr": {"type": "string"},
                        "exitCode": {"type": "integer"},
                        "timedOut": {"type": "boolean"},
                    },
                },
            },
            {
                "name": "sandbox.history",
                "description": "Get execution history.",
                "permission": "sandbox:read",
                "endpoint": "GET /api/execute/history",
                "timeout_ms": 3000,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "default": 20},
                    },
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "items": {"type": "array"},
                    },
                },
            },
        ],
    }


@router.post("/tool/invoke", response_model=ToolInvokeResponse)
async def invoke_tool(req: ToolInvokeRequest):
    start = time.time()
    trace_id = req.trace_id or f"tr_{uuid.uuid4().hex[:12]}"

    try:
        inp = req.input

        if req.capability == "sandbox.execute":
            output = await execute_code(
                code=inp.get("code", ""),
                language=inp.get("language", "python"),
                stdin=inp.get("stdin"),
                user_id=req.context.get("user_id"),
            )
        elif req.capability == "sandbox.history":
            output = await get_history(
                user_id=req.context.get("user_id"),
                limit=inp.get("limit", 20),
            )
        else:
            return ToolInvokeResponse(
                trace_id=trace_id,
                tool=settings.APP_NAME,
                capability=req.capability,
                success=False,
                error={"code": "NOT_FOUND", "message": f"Capability '{req.capability}' not found"},
                elapsed_ms=int((time.time() - start) * 1000),
            )

        return ToolInvokeResponse(
            trace_id=trace_id,
            tool=settings.APP_NAME,
            capability=req.capability,
            success=True,
            output=output,
            elapsed_ms=int((time.time() - start) * 1000),
        )

    except Exception as e:
        return ToolInvokeResponse(
            trace_id=trace_id,
            tool=settings.APP_NAME,
            capability=req.capability,
            success=False,
            error={"code": "INTERNAL_ERROR", "message": str(e)},
            elapsed_ms=int((time.time() - start) * 1000),
        )
