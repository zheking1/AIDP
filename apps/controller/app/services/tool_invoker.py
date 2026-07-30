"""
Tool Invoker Service - Calls tools via local function calls (integrated) or HTTP (legacy)
"""

import os
import json
import httpx
from typing import Optional, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ToolRegistry


class ToolInvoker:
    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
        self._client = None
        self._endpoint_cache = {}

    async def _get_client(self):
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def invoke(self, tool_name: str, capability: str,
                    arguments: dict = None) -> dict:

        # Try local (integrated) call first
        result = await self._invoke_local(tool_name, capability, arguments)
        if result is not None:
            return result

        # Fallback to HTTP for non-integrated tools
        endpoint = await self._get_tool_endpoint(tool_name)
        if not endpoint:
            return {"success": False, "error": f"Tool '{tool_name}' not found"}

        url = f"{endpoint}/tool/invoke"
        payload = {
            "capability": capability,
            "input": arguments or {},
            "trace_id": self._generate_trace_id()
        }

        try:
            client = await self._get_client()
            response = await client.post(
                url, json=payload,
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 200:
                return response.json()
            return {"success": False, "error": f"HTTP {response.status_code}"}
        except httpx.TimeoutException:
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _invoke_local(self, tool_name: str, capability: str, arguments: dict) -> Optional[dict]:
        """Try to invoke tool locally (integrated in Controller process)"""
        try:
            if tool_name == "skill-router" or tool_name == "skillrouter":
                return await self._skill_router_invoke(capability, arguments)
            elif tool_name == "sandbox-tool" and capability.startswith("sandbox."):
                return await self._sandbox_execute(arguments)
            elif tool_name == "quality-tool" and capability.startswith("quality."):
                return await self._quality_check(arguments)
            elif tool_name == "knowledge-tool" and capability.startswith("knowledge."):
                if capability == "knowledge.create_document":
                    return await self._knowledge_create_document(arguments)
                return await self._knowledge_search(arguments)
            elif tool_name == "memory-tool" and capability.startswith("memory."):
                return await self._memory_op(capability, arguments)
        except Exception:
            pass
        return None

    async def _sandbox_execute(self, arguments: dict) -> dict:
        from app.tools.sandbox_tool.services.execution_service import execute_code
        code = arguments.get("code", "")
        language = arguments.get("language", "python")
        result = await execute_code(code, language)
        return {"success": True, "output": result}

    async def _quality_check(self, arguments: dict) -> dict:
        from app.tools.quality_tool.api.check import run_quality_check
        from app.tools.quality_tool.api.check import CheckRequest
        from app.db.database import async_session_factory
        async with async_session_factory() as db:
            req = CheckRequest(
                code=arguments.get("code", ""),
                filename=arguments.get("filename"),
                language=arguments.get("language"),
            )
            result = await run_quality_check(req, user=None, db=db)
            return {"success": True, "output": result}

    async def _knowledge_search(self, arguments: dict) -> dict:
        from app.tools.knowledge_tool.services.search_service import search_documents
        from app.db.database import async_session_factory
        async with async_session_factory() as db:
            results = await search_documents(
                db,
                query=arguments.get("query", ""),
                top_k=arguments.get("top_k", 5),
                base_id=arguments.get("base_id"),
                project_id=arguments.get("project_id"),
            )
            return {"success": True, "output": {"items": results}}

    async def _knowledge_create_document(self, arguments: dict) -> dict:
        from app.tools.knowledge_tool.services.document_service import create_document
        from app.tools.knowledge_tool.services.indexing_service import create_index_job
        from app.tools.knowledge_tool.schemas.document import DocumentCreateRequest
        from app.db.database import async_session_factory
        async with async_session_factory() as db:
            req = DocumentCreateRequest(
                workspace_id=arguments.get("workspace_id", "default"),
                title=arguments.get("title", "untitled"),
                doc_type=arguments.get("doc_type", "markdown"),
                content=arguments.get("content", ""),
                project_id=arguments.get("project_id"),
                source_uri=arguments.get("source_uri", ""),
            )
            doc = await create_document(db, req)
            if doc and doc.id:
                try:
                    await create_index_job(db, doc_id=doc.id, workspace_id=doc.workspace_id)
                except Exception:
                    pass
            return {"success": True, "output": {"id": doc.id, "title": doc.title, "status": "created"}}

    async def _skill_router_invoke(self, capability: str, arguments: dict) -> dict:
        from app.tools.skill_router.services.vector_service import analyze_intent
        from app.tools.skill_router.services.resolve_service import resolve_task
        from app.tools.skill_router.services.skill_service import run_skill

        task = arguments.get("task", "")
        if capability == "analyze_intent":
            result = await analyze_intent(task, arguments.get("chat_history"))
            return {"success": True, "data": result}
        elif capability == "skill_run":
            skills, rules, instructions = await run_skill(
                task=task,
                mode=arguments.get("mode", "auto"),
                hint_tags=arguments.get("hint_tags", []),
                top_k=arguments.get("top_k", 6),
                session_id=arguments.get("session_id"),
            )
            return {"success": True, "data": {"skills": skills, "rules": rules, "instructions": instructions}}
        elif capability == "resolve_task":
            result = await resolve_task(
                task=task,
                mode=arguments.get("mode", "auto"),
                top_k=arguments.get("top_k", 3),
                api_key=arguments.get("api_key", ""),
            )
            return {"success": True, "data": result}
        return {"success": False, "error": f"Unknown skill-router capability: {capability}"}

    async def _memory_op(self, capability: str, arguments: dict) -> dict:
        from app.tools.memory_tool.services.memory_service import create_memory, search_memory

        if "search" in capability:
            results = await search_memory(
                project=arguments.get("project", ""),
                query=arguments.get("query", ""),
                category=arguments.get("category"),
                limit=arguments.get("limit", 10),
            )
            return {"success": True, "output": {"results": results}}
        elif "create" in capability:
            entry = await create_memory(
                project=arguments.get("project", ""),
                title=arguments.get("title", ""),
                content=arguments.get("content", ""),
                category=arguments.get("category", "other"),
                tags=arguments.get("tags", ""),
            )
            return {"success": True, "output": entry}
        return {"success": False, "error": f"Unknown memory capability: {capability}"}
    
    async def _get_tool_endpoint(self, tool_name: str) -> Optional[str]:
        """Get tool endpoint from registry or cache"""
        
        # Check cache first
        if tool_name in self._endpoint_cache:
            return self._endpoint_cache[tool_name]
        
        # Look up in database
        if self.db:
            result = await self.db.execute(
                select(ToolRegistry).where(
                    ToolRegistry.name == tool_name,
                    ToolRegistry.status == "healthy"
                )
            )
            tool = result.scalar_one_or_none()
            if tool:
                self._endpoint_cache[tool_name] = tool.endpoint
                return tool.endpoint
        
        # Fallback to environment/config
        endpoints = {
            "skill-router": os.getenv("SKILLROUTER_URL", "http://localhost:8883"),
            "knowledge-tool": os.getenv("KNOWLEDGE_URL", "http://localhost:18081"),
            "memory-tool": os.getenv("MEMORY_URL", "http://localhost:18085"),
            "asset-tool": os.getenv("ASSET_URL", "http://localhost:18082"),
            "sandbox-tool": os.getenv("SANDBOX_URL", "http://localhost:18083"),
            "quality-tool": os.getenv("QUALITY_URL", "http://localhost:18084"),
        }
        
        endpoint = endpoints.get(tool_name)
        if endpoint:
            self._endpoint_cache[tool_name] = endpoint
            
        return endpoint
    
    def _generate_trace_id(self) -> str:
        """Generate a short trace ID"""
        import uuid
        return str(uuid.uuid4())[:8]
    
    async def close(self):
        """Close HTTP client"""
        await self._client.aclose()


# Singleton instance
_tool_invoker: Optional[ToolInvoker] = None


def get_tool_invoker(db: Optional[AsyncSession] = None) -> ToolInvoker:
    """Get or create tool invoker singleton"""
    global _tool_invoker
    if _tool_invoker is None:
        _tool_invoker = ToolInvoker(db)
    return _tool_invoker


async def invoke_tool(tool_name: str, capability: str, arguments: dict = None, user_id: Optional[int] = None) -> dict:
    """Standalone wrapper to invoke a tool"""
    import uuid
    from datetime import datetime, timezone
    from app.db.database import async_session_factory
    from app.db.models import ToolInvocation

    async with async_session_factory() as db:
        invoker = get_tool_invoker(db)
        result = await invoker.invoke(tool_name, capability, arguments)

    try:
        async with async_session_factory() as db:
            record = ToolInvocation(
                id=str(uuid.uuid4()),
                tool_name=tool_name,
                capability=capability,
                arguments=json.dumps(arguments or {}),
                result=json.dumps(result),
                success=result.get("success", False),
                user_id=user_id,
                duration_ms=None,
                created_at=datetime.now(timezone.utc)
            )
            db.add(record)
            await db.commit()
    except Exception:
        pass

    return result


async def get_invocation_history(tool_name: Optional[str] = None, limit: int = 20) -> list:
    """Get invocation history"""
    from app.db.database import async_session_factory
    from app.db.models import ToolInvocation

    try:
        async with async_session_factory() as db:
            from sqlalchemy import select, desc
            query = select(ToolInvocation)
            if tool_name:
                query = query.where(ToolInvocation.tool_name == tool_name)
            query = query.order_by(desc(ToolInvocation.created_at)).limit(limit)
            result = await db.execute(query)
            records = result.scalars().all()
            return [r.to_dict() if hasattr(r, 'to_dict') else {"id": r.id, "tool_name": r.tool_name, "capability": r.capability, "success": r.success, "created_at": r.created_at.isoformat() if r.created_at else None} for r in records]
    except Exception:
        return []
