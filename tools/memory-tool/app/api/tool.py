import time
import uuid
from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.config import settings
from app.services.memory_service import create_memory, search_memory, get_memory, update_memory, delete_memory, get_context_package, hybrid_search
from app.services.semantic_contradiction import SemanticContradictionDetector, ContradictionHandler
from app.services.memory_consolidation import MemoryConsolidator

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
            "displayName": "Memory Tool",
            "version": settings.APP_VERSION,
            "description": "Project memory management with search and context packages.",
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
                "name": "memory.create",
                "description": "Create a memory entry.",
                "endpoint": "POST /api/memory",
                "timeoutMs": 3000,
                "permission": "memory:write",
            },
            {
                "name": "memory.search",
                "description": "Search memory entries.",
                "endpoint": "GET /api/memory/search",
                "timeoutMs": 3000,
                "permission": "memory:read",
            },
            {
                "name": "memory.search.hybrid",
                "description": "Hybrid search (BM25 + TF-IDF + Vector) for memory entries.",
                "endpoint": "POST /api/memory/search/hybrid",
                "timeoutMs": 5000,
                "permission": "memory:read",
            },
            {
                "name": "memory.contradiction.check",
                "description": "Check for contradictions before creating a memory.",
                "endpoint": "POST /api/memory/check-contradictions",
                "timeoutMs": 5000,
                "permission": "memory:write",
            },
            {
                "name": "memory.consolidate",
                "description": "Consolidate similar memories.",
                "endpoint": "POST /api/memory/consolidate",
                "timeoutMs": 10000,
                "permission": "memory:write",
            },
            {
                "name": "memory.context",
                "description": "Get context package for a project and query.",
                "endpoint": "GET /api/memory/context",
                "timeoutMs": 3000,
                "permission": "memory:read",
            },
            {
                "name": "memory.update",
                "description": "Update a memory entry.",
                "endpoint": "PUT /api/memory/{id}",
                "timeoutMs": 3000,
                "permission": "memory:write",
            },
            {
                "name": "memory.delete",
                "description": "Delete a memory entry.",
                "endpoint": "DELETE /api/memory/{id}",
                "timeoutMs": 3000,
                "permission": "memory:delete",
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
                "name": "memory.create",
                "description": "Create a memory entry.",
                "permission": "memory:write",
                "endpoint": "POST /api/memory",
                "timeout_ms": 3000,
                "input_schema": {
                    "type": "object",
                    "required": ["project", "category", "title", "content"],
                    "properties": {
                        "project": {"type": "string"},
                        "category": {"type": "string"},
                        "title": {"type": "string"},
                        "content": {"type": "string"},
                        "tags": {"type": "string"},
                        "pinned": {"type": "boolean"},
                    },
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "project": {"type": "string"},
                        "title": {"type": "string"},
                    },
                },
            },
            {
                "name": "memory.search",
                "description": "Search memory entries.",
                "permission": "memory:read",
                "endpoint": "GET /api/memory/search",
                "timeout_ms": 3000,
                "input_schema": {
                    "type": "object",
                    "required": ["project"],
                    "properties": {
                        "project": {"type": "string"},
                        "query": {"type": "string"},
                        "category": {"type": "string"},
                        "limit": {"type": "integer", "default": 50},
                    },
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "items": {"type": "array"},
                        "count": {"type": "integer"},
                    },
                },
            },
            {
                "name": "memory.search.hybrid",
                "description": "Hybrid search (BM25 + TF-IDF + Vector) for memory entries.",
                "permission": "memory:read",
                "endpoint": "POST /api/memory/search/hybrid",
                "timeout_ms": 5000,
                "input_schema": {
                    "type": "object",
                    "required": ["project", "query"],
                    "properties": {
                        "project": {"type": "string"},
                        "query": {"type": "string"},
                        "top_k": {"type": "integer", "default": 10},
                        "weights": {
                            "type": "object",
                            "properties": {
                                "vector": {"type": "number"},
                                "tfidf": {"type": "number"},
                                "bm25": {"type": "number"},
                            },
                        },
                    },
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "items": {"type": "array"},
                        "total": {"type": "integer"},
                        "search_type": {"type": "string"},
                    },
                },
            },
            {
                "name": "memory.contradiction.check",
                "description": "Check for contradictions before creating a memory.",
                "permission": "memory:write",
                "endpoint": "POST /api/memory/check-contradictions",
                "timeout_ms": 5000,
                "input_schema": {
                    "type": "object",
                    "required": ["project", "title", "content"],
                    "properties": {
                        "project": {"type": "string"},
                        "title": {"type": "string"},
                        "content": {"type": "string"},
                    },
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "has_contradictions": {"type": "boolean"},
                        "contradictions": {"type": "array"},
                    },
                },
            },
            {
                "name": "memory.context",
                "description": "Get context package for a project and query.",
                "permission": "memory:read",
                "endpoint": "GET /api/memory/context",
                "timeout_ms": 3000,
                "input_schema": {
                    "type": "object",
                    "required": ["project", "query"],
                    "properties": {
                        "project": {"type": "string"},
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "default": 10},
                    },
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "project": {"type": "string"},
                        "memories": {"type": "array"},
                        "count": {"type": "integer"},
                    },
                },
            },
            {
                "name": "memory.update",
                "description": "Update a memory entry.",
                "permission": "memory:write",
                "endpoint": "PUT /api/memory/{id}",
                "timeout_ms": 3000,
                "input_schema": {
                    "type": "object",
                    "required": ["memoryId"],
                    "properties": {
                        "memoryId": {"type": "integer"},
                        "category": {"type": "string"},
                        "title": {"type": "string"},
                        "content": {"type": "string"},
                        "tags": {"type": "string"},
                        "pinned": {"type": "boolean"},
                    },
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "title": {"type": "string"},
                    },
                },
            },
            {
                "name": "memory.delete",
                "description": "Delete a memory entry.",
                "permission": "memory:delete",
                "endpoint": "DELETE /api/memory/{id}",
                "timeout_ms": 3000,
                "input_schema": {
                    "type": "object",
                    "required": ["memoryId"],
                    "properties": {
                        "memoryId": {"type": "integer"},
                    },
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "deleted": {"type": "boolean"},
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

        if req.capability == "memory.create":
            output = await create_memory(
                project=inp.get("project", ""),
                category=inp.get("category", ""),
                title=inp.get("title", ""),
                content=inp.get("content", ""),
                tags=inp.get("tags"),
                pinned=inp.get("pinned", False),
                user_id=req.context.get("user_id"),
            )
        elif req.capability == "memory.search":
            output = await search_memory(
                project=inp.get("project", ""),
                query=inp.get("query"),
                category=inp.get("category"),
                limit=inp.get("limit", 50),
                user_id=req.context.get("user_id"),
            )
        elif req.capability == "memory.search.hybrid":
            weights = inp.get("weights", {})
            output = await hybrid_search(
                project=inp.get("project", ""),
                query=inp.get("query", ""),
                vector_weight=weights.get("vector", 0.5),
                text_weight=weights.get("tfidf", 0.3),
                bm25_weight=weights.get("bm25", 0.2),
                top_k=inp.get("top_k", 10),
                user_id=req.context.get("user_id"),
            )
        elif req.capability == "memory.contradiction.check":
            from app.db.models import MemoryEntry, async_session as mem_async_session
            async with mem_async_session() as session:
                q = select(MemoryEntry).where(MemoryEntry.project == inp.get("project", ""))
                existing = await session.execute(q.limit(100))
                existing_list = existing.scalars().all()
            detector = SemanticContradictionDetector()
            contradictions = detector.detect(
                {"title": inp.get("title", ""), "content": inp.get("content", "")},
                [{"id": e.id, "title": e.title, "content": e.content, "createdAt": str(e.created_at)} for e in existing_list]
            )
            handler = ContradictionHandler()
            results = []
            for c in contradictions:
                action = handler.handle(
                    {"title": inp.get("title", ""), "content": inp.get("content", "")},
                    c["existing_memory"],
                    c["contradiction_type"],
                    c["confidence"],
                )
                results.append({"contradiction": c, "action": action})
            output = {"has_contradictions": len(results) > 0, "contradictions": results}
        elif req.capability == "memory.consolidate":
            consolidator = MemoryConsolidator()
            output = await consolidator.consolidate(
                project=inp.get("project", ""),
                similarity_threshold=inp.get("similarity_threshold", 0.85),
            )
        elif req.capability == "memory.context":
            output = await get_context_package(
                project=inp.get("project", ""),
                query=inp.get("query", ""),
                limit=inp.get("limit", 10),
            )
        elif req.capability == "memory.update":
            memory_id = inp.get("memoryId")
            if not memory_id:
                return ToolInvokeResponse(
                    trace_id=trace_id,
                    tool=settings.APP_NAME,
                    capability=req.capability,
                    success=False,
                    error={"code": "VALIDATION_ERROR", "message": "memoryId is required"},
                    elapsed_ms=int((time.time() - start) * 1000),
                )
            output = await update_memory(
                memory_id,
                **{k: v for k, v in inp.items() if k != "memoryId" and v is not None},
            )
            if output is None:
                return ToolInvokeResponse(
                    trace_id=trace_id,
                    tool=settings.APP_NAME,
                    capability=req.capability,
                    success=False,
                    error={"code": "NOT_FOUND", "message": "Memory entry not found"},
                    elapsed_ms=int((time.time() - start) * 1000),
                )
        elif req.capability == "memory.delete":
            memory_id = inp.get("memoryId")
            if not memory_id:
                return ToolInvokeResponse(
                    trace_id=trace_id,
                    tool=settings.APP_NAME,
                    capability=req.capability,
                    success=False,
                    error={"code": "VALIDATION_ERROR", "message": "memoryId is required"},
                    elapsed_ms=int((time.time() - start) * 1000),
                )
            deleted = await delete_memory(memory_id)
            output = {"deleted": deleted}
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
