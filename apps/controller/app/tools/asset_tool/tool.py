import time
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.asset_tool.tools.asset-tool.db.database import get_db
from app.tools.asset_tool.tools.asset-tool.config import settings
from app.tools.asset_tool.tools.asset-tool.services import asset_service
from app.tools.asset_tool.tools.asset-tool.schemas.asset import AssetSearchRequest

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
            "displayName": "Asset Tool",
            "version": settings.APP_VERSION,
            "description": "Code asset and template management.",
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
                "name": "asset.search",
                "description": "Search code assets.",
                "endpoint": "POST /api/assets/search",
                "timeoutMs": 3000,
                "permission": "asset:search",
            },
            {
                "name": "asset.render",
                "description": "Render asset template.",
                "endpoint": "POST /api/assets/render",
                "timeoutMs": 1000,
                "permission": "asset:read",
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
                "name": "asset.search",
                "description": "Search code assets.",
                "permission": "asset:search",
                "endpoint": "POST /api/assets/search",
                "timeout_ms": 3000,
                "input_schema": {
                    "type": "object",
                    "required": ["query"],
                    "properties": {
                        "query": {"type": "string"},
                        "asset_type": {"type": "string"},
                        "top_k": {"type": "integer", "default": 8},
                    },
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "items": {"type": "array"},
                        "total": {"type": "integer"},
                    },
                },
            },
            {
                "name": "asset.render",
                "description": "Render asset template.",
                "permission": "asset:read",
                "endpoint": "POST /api/assets/render",
                "timeout_ms": 1000,
                "input_schema": {
                    "type": "object",
                    "required": ["id"],
                    "properties": {
                        "id": {"type": "string"},
                        "variables": {"type": "object"},
                    },
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "rendered": {"type": "string"},
                    },
                },
            },
        ],
    }


@router.post("/tool/invoke", response_model=ToolInvokeResponse)
async def invoke_tool(req: ToolInvokeRequest, db: AsyncSession = Depends(get_db)):
    start = time.time()
    trace_id = req.trace_id or f"tr_{uuid.uuid4().hex[:12]}"

    try:
        if req.capability == "asset.search":
            search_req = AssetSearchRequest(
                workspace_id=req.context.get("workspace_id", ""),
                project_id=req.context.get("project_id"),
                query=req.input.get("query", ""),
                asset_type=req.input.get("asset_type"),
                language=req.input.get("language"),
                top_k=req.input.get("top_k", 8),
            )
            result = await asset_service.search_assets(db, search_req)
            output = result.model_dump()
        elif req.capability == "asset.render":
            asset_id = req.input.get("id")
            if not asset_id:
                return ToolInvokeResponse(
                    trace_id=trace_id,
                    tool=settings.APP_NAME,
                    capability=req.capability,
                    success=False,
                    error={"code": "VALIDATION_ERROR", "message": "id is required"},
                    elapsed_ms=int((time.time() - start) * 1000),
                )
            rendered = await asset_service.render_asset(
                db,
                asset_id=asset_id,
                workspace_id=req.context.get("workspace_id", ""),
                variables=req.input.get("variables", {}),
            )
            if rendered is None:
                return ToolInvokeResponse(
                    trace_id=trace_id,
                    tool=settings.APP_NAME,
                    capability=req.capability,
                    success=False,
                    error={"code": "NOT_FOUND", "message": "Asset not found"},
                    elapsed_ms=int((time.time() - start) * 1000),
                )
            output = {"rendered": rendered}
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
