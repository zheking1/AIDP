import time
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.knowledge_tool.tools.knowledge-tool.db.database import get_db
from app.tools.knowledge_tool.tools.knowledge-tool.config import settings
from app.tools.knowledge_tool.tools.knowledge-tool.services.search_service import SearchService
from app.tools.knowledge_tool.tools.knowledge-tool.services import indexing_service
from app.tools.knowledge_tool.tools.knowledge-tool.schemas.search import SearchRequest

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
            "displayName": "Knowledge Tool",
            "version": settings.APP_VERSION,
            "description": "Document ingestion, indexing and retrieval.",
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
                "name": "knowledge.search",
                "description": "Search indexed document chunks.",
                "endpoint": "POST /api/knowledge/search",
                "timeoutMs": 3000,
                "permission": "knowledge:search",
            },
            {
                "name": "document.index",
                "description": "Create index job for a document.",
                "endpoint": "POST /api/documents/{id}/index",
                "timeoutMs": 10000,
                "permission": "knowledge:index",
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
                "name": "knowledge.search",
                "description": "Search indexed document chunks with metadata filtering.",
                "permission": "knowledge:search",
                "endpoint": "POST /api/knowledge/search",
                "timeout_ms": 3000,
                "input_schema": {
                    "type": "object",
                    "required": ["query"],
                    "properties": {
                        "query": {"type": "string"},
                        "top_k": {"type": "integer", "default": 8},
                        "search_mode": {"type": "string", "default": "hybrid"},
                    },
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "items": {"type": "array"},
                        "degraded": {"type": "boolean"},
                        "matched_kb_ids": {"type": "array"},
                    },
                },
            },
            {
                "name": "knowledge.create_document",
                "description": "Create and index a knowledge document.",
                "permission": "knowledge:write",
                "endpoint": "POST /api/documents",
                "timeout_ms": 15000,
                "input_schema": {
                    "type": "object",
                    "required": ["title", "content"],
                    "properties": {
                        "title": {"type": "string"},
                        "content": {"type": "string"},
                        "doc_type": {"type": "string", "default": "markdown"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "knowledge_base_id": {"type": "string"},
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
        if req.capability == "knowledge.search":
            workspace_id = req.context.get("workspace_id", "")
            project_id = req.context.get("project_id")
            knowledge_base_ids = req.context.get("knowledge_base_ids")
            task_domains = req.context.get("task_domains")

            svc = SearchService(db)
            result = await svc.search(
                query=req.input.get("query", ""),
                workspace_id=workspace_id or None,
                project_id=project_id,
                knowledge_base_ids=knowledge_base_ids,
                task_domains=task_domains,
                top_k=req.input.get("top_k", 8),
                min_score=req.input.get("min_score", 0.1),
            )
            output = result
        elif req.capability == "knowledge.create_document":
            from app.tools.knowledge_tool.tools.knowledge-tool.schemas.document import DocumentCreateRequest
            from app.tools.knowledge_tool.tools.knowledge-tool.services.document_service import create_document
            inp = req.input
            doc_req = DocumentCreateRequest(
                workspace_id=req.context.get("workspace_id", "default"),
                title=inp.get("title", ""),
                content=inp.get("content", ""),
                doc_type=inp.get("doc_type", "markdown"),
                tags=inp.get("tags") or [],
                knowledge_base_id=inp.get("knowledge_base_id"),
            )
            doc = await create_document(db, doc_req)
            if doc and doc.id:
                try:
                    await indexing_service.create_index_job(db, doc_id=doc.id, workspace_id=doc.workspace_id)
                except Exception:
                    pass
                output = {"id": doc.id, "title": doc.title, "status": "created"}
            else:
                output = {"error": "create failed"}
        elif req.capability == "document.index":
            from app.tools.knowledge_tool.tools.knowledge-tool.schemas.document import IndexJobRequest
            doc_id = req.input.get("document_id")
            if not doc_id:
                return ToolInvokeResponse(
                    trace_id=trace_id,
                    tool=settings.APP_NAME,
                    capability=req.capability,
                    success=False,
                    error={"code": "VALIDATION_ERROR", "message": "document_id is required"},
                    elapsed_ms=int((time.time() - start) * 1000),
                )
            job = await indexing_service.create_index_job(
                db,
                document_id=doc_id,
                workspace_id=req.context.get("workspace_id", ""),
                project_id=req.context.get("project_id"),
            )
            job_result = await indexing_service.run_index_job(db, job.id)
            output = job_result.model_dump()
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