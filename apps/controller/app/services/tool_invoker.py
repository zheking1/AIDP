"""
Tool Invoker Service - Calls external tools via HTTP API
"""

import os
import json
import httpx
from typing import Optional, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ToolRegistry


class ToolInvoker:
    """Invokes tool capabilities via HTTP"""
    
    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
        self._client = httpx.AsyncClient(timeout=30.0)
        self._endpoint_cache = {}
    
    async def invoke(self, tool_name: str, capability: str, 
                    arguments: dict = None) -> dict:
        """Invoke a tool capability"""
        
        # Get tool endpoint
        endpoint = await self._get_tool_endpoint(tool_name)
        if not endpoint:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found or not registered"
            }
        
        # Build request
        url = f"{endpoint}/tool/invoke"
        payload = {
            "capability": capability,
            "input": arguments or {},
            "trace_id": self._generate_trace_id()
        }
        
        try:
            response = await self._client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "Request timeout"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
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
            "skill-router": os.getenv("SKILLROUTER_URL", "http://localhost:8788"),
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
