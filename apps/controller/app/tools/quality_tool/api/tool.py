import time
import uuid
from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.tools.quality_tool.config import settings
from app.tools.quality_tool.services.quality_service import run_check

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
            "displayName": "Quality Tool",
            "version": settings.APP_VERSION,
            "description": "Code quality checks: linting and security scanning.",
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
                "name": "quality.lint",
                "description": "Run lint checks on code.",
                "endpoint": "POST /api/check",
                "timeoutMs": 5000,
                "permission": "quality:lint",
            },
            {
                "name": "quality.security",
                "description": "Run security scan on code.",
                "endpoint": "POST /api/check",
                "timeoutMs": 5000,
                "permission": "quality:security",
            },
            {
                "name": "quality.check",
                "description": "Run all quality checks (lint + security).",
                "endpoint": "POST /api/check",
                "timeoutMs": 5000,
                "permission": "quality:check",
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
                "name": "quality.lint",
                "description": "Run lint checks on code.",
                "permission": "quality:lint",
                "endpoint": "POST /api/check",
                "timeout_ms": 5000,
                "input_schema": {
                    "type": "object",
                    "required": ["code"],
                    "properties": {
                        "code": {"type": "string"},
                        "filename": {"type": "string"},
                        "language": {"type": "string"},
                    },
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "issues": {"type": "array"},
                        "issueCount": {"type": "integer"},
                    },
                },
            },
            {
                "name": "quality.security",
                "description": "Run security scan on code.",
                "permission": "quality:security",
                "endpoint": "POST /api/check",
                "timeout_ms": 5000,
                "input_schema": {
                    "type": "object",
                    "required": ["code"],
                    "properties": {
                        "code": {"type": "string"},
                        "filename": {"type": "string"},
                    },
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "issues": {"type": "array"},
                        "issueCount": {"type": "integer"},
                    },
                },
            },
            {
                "name": "quality.check",
                "description": "Run all quality checks (lint + security).",
                "permission": "quality:check",
                "endpoint": "POST /api/check",
                "timeout_ms": 5000,
                "input_schema": {
                    "type": "object",
                    "required": ["code"],
                    "properties": {
                        "code": {"type": "string"},
                        "filename": {"type": "string"},
                        "language": {"type": "string"},
                    },
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "issues": {"type": "array"},
                        "issueCount": {"type": "integer"},
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

        if req.capability in ("quality.lint", "quality.security", "quality.check"):
            check_type = "all"
            if req.capability == "quality.lint":
                check_type = "lint"
            elif req.capability == "quality.security":
                check_type = "security"
            output = await run_check(
                code=inp.get("code", ""),
                check_type=check_type,
                filename=inp.get("filename"),
                language=inp.get("language"),
                user_id=req.context.get("user_id"),
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
