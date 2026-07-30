"""Doc Index Tool API - Standard tool protocol endpoints"""

import time
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.doc_index.db.database import get_db
from app.tools.doc_index.services.search_service import SearchService

router = APIRouter()


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


CAPABILITIES = [
    {
        "name": "doc.create",
        "description": "Create a documentation page.",
        "permission": "doc:write",
        "endpoint": "POST /tool/invoke",
        "timeout_ms": 10000,
        "input_schema": {
            "type": "object",
            "required": ["title", "content"],
            "properties": {
                "title": {"type": "string"},
                "content": {"type": "string"},
                "url": {"type": "string"},
                "source": {"type": "string", "default": "manual"},
                "language": {"type": "string"},
                "framework": {"type": "string"},
            },
        },
    },
    {
        "name": "doc.search",
        "description": "Search documentation pages.",
        "permission": "doc:read",
        "endpoint": "POST /tool/invoke",
        "timeout_ms": 5000,
        "input_schema": {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 20},
            },
        },
    },
    {
        "name": "doc.get",
        "description": "Get a documentation page by ID.",
        "permission": "doc:read",
        "endpoint": "POST /tool/invoke",
        "timeout_ms": 3000,
        "input_schema": {
            "type": "object",
            "required": ["doc_id"],
            "properties": {"doc_id": {"type": "integer"}},
        },
    },
    {
        "name": "doc.list",
        "description": "List all documentation pages.",
        "permission": "doc:read",
        "endpoint": "POST /tool/invoke",
        "timeout_ms": 5000,
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "doc.wiki",
        "description": "Generate wiki with optional language/framework filters.",
        "permission": "doc:read",
        "endpoint": "POST /tool/invoke",
        "timeout_ms": 10000,
        "input_schema": {
            "type": "object",
            "properties": {
                "language": {"type": "string"},
                "framework": {"type": "string"},
            },
        },
    },
]


@router.get("/tool/manifest")
async def get_manifest():
    return {
        "apiVersion": "aidp.dev/v1",
        "kind": "Tool",
        "metadata": {"name": "doc-index", "displayName": "Doc Index", "version": "0.1.0"},
        "runtime": {"modes": ["standalone"], "docker": {"image": "aidp/doc-index:0.1.0", "port": 18087}},
        "capabilities": [
            {"name": c["name"], "description": c["description"], "endpoint": c["endpoint"], "timeoutMs": c["timeout_ms"], "permission": c["permission"]}
            for c in CAPABILITIES
        ],
    }


@router.get("/tool/capabilities")
async def get_capabilities():
    return {"tool": "doc-index", "version": "0.1.0", "capabilities": CAPABILITIES}


@router.post("/tool/invoke", response_model=ToolInvokeResponse)
async def invoke_tool(req: ToolInvokeRequest, db: AsyncSession = Depends(get_db)):
    start = time.time()
    trace_id = req.trace_id or f"tr_{uuid.uuid4().hex[:12]}"
    inp = req.input

    try:
        output = None
        if req.capability == "doc.create":
            from app.tools.doc_index.services.parser import DocParser
            from app.tools.doc_index.db.models import DocPage
            title = inp.get("title", "")
            content = inp.get("content", "")
            url = inp.get("url")
            source = inp.get("source", "manual")
            language = inp.get("language")
            framework = inp.get("framework")
            if not title or not content:
                return ToolInvokeResponse(trace_id=trace_id, tool="doc-index", capability=req.capability, success=False, error={"code": "INVALID_INPUT", "message": "title and content required"}, elapsed_ms=int((time.time() - start) * 1000))
            parser = DocParser()
            parsed = parser.parse_markdown(content, url)
            doc = DocPage(title=parsed["title"] or title, url=url or None, content=content, summary=parsed["summary"], word_count=parsed["word_count"], source=source, language=language or None, framework=framework or None)
            db.add(doc)
            await db.commit()
            await db.refresh(doc)
            output = {"id": doc.id, "title": doc.title, "language": doc.language, "framework": doc.framework}

        elif req.capability == "doc.search":
            svc = SearchService(db)
            results = await svc.search(query=inp.get("query", ""), limit=inp.get("limit", 20))
            output = results

        elif req.capability == "doc.get":
            svc = SearchService(db)
            doc = await svc.get_page(inp.get("doc_id", 0))
            if not doc:
                return ToolInvokeResponse(trace_id=trace_id, tool="doc-index", capability=req.capability, success=False, error={"code": "NOT_FOUND", "message": "Doc not found"}, elapsed_ms=int((time.time() - start) * 1000))
            output = doc

        elif req.capability == "doc.list":
            svc = SearchService(db)
            output = await svc.get_all_pages()

        elif req.capability == "doc.wiki":
            from app.tools.doc_index.services.wiki_generator import WikiGenerator
            generator = WikiGenerator(db)
            output = await generator.generate_wiki(language=inp.get("language"), framework=inp.get("framework"))

        else:
            return ToolInvokeResponse(trace_id=trace_id, tool="doc-index", capability=req.capability, success=False, error={"code": "NOT_FOUND", "message": f"Capability '{req.capability}' not found"}, elapsed_ms=int((time.time() - start) * 1000))

        return ToolInvokeResponse(trace_id=trace_id, tool="doc-index", capability=req.capability, success=True, output=output, elapsed_ms=int((time.time() - start) * 1000))

    except Exception as e:
        return ToolInvokeResponse(trace_id=trace_id, tool="doc-index", capability=req.capability, success=False, error={"code": "INTERNAL_ERROR", "message": str(e)}, elapsed_ms=int((time.time() - start) * 1000))