import time
import logging
from typing import Optional
from datetime import datetime

import httpx
from sqlalchemy import select
from app.db.models import ToolRegistry
from app.db.database import async_session_factory as async_session
from app.config import settings

logger = logging.getLogger(__name__)


async def register_tool(
    name: str,
    endpoint: str,
    display_name: Optional[str] = None,
    description: Optional[str] = None,
    version: Optional[str] = None,
) -> dict:
    async with async_session() as session:
        existing = await session.execute(select(ToolRegistry).where(ToolRegistry.name == name))
        existing = existing.scalar_one_or_none()

        if existing:
            existing.endpoint = endpoint
            if display_name:
                existing.display_name = display_name
            if description:
                existing.description = description
            if version:
                existing.version = version
            existing.updated_at = datetime.utcnow()
            tool = existing
        else:
            tool = ToolRegistry(
                name=name,
                display_name=display_name or name,
                description=description,
                version=version,
                endpoint=endpoint,
                status="registered",
            )
            session.add(tool)

        await session.commit()
        await session.refresh(tool)
        return _to_dict(tool)


async def list_tools(status: Optional[str] = None) -> list:
    async with async_session() as session:
        q = select(ToolRegistry)
        if status:
            q = q.where(ToolRegistry.status == status)
        q = q.order_by(ToolRegistry.name)
        result = await session.execute(q)
        return [_to_dict(r) for r in result.scalars().all()]


async def get_tool(tool_name: str) -> Optional[dict]:
    async with async_session() as session:
        result = await session.execute(select(ToolRegistry).where(ToolRegistry.name == tool_name))
        tool = result.scalar_one_or_none()
        return _to_dict(tool) if tool else None


async def health_check_tool(tool_name: str) -> dict:
    tool = await get_tool(tool_name)
    if not tool:
        return {"error": f"Tool not found: {tool_name}"}

    endpoint = tool["endpoint"]
    health_url = f"{endpoint.rstrip('/')}/health"

    try:
        start = time.time()
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(health_url)
        duration_ms = int((time.time() - start) * 1000)

        if resp.status_code == 200:
            status = "healthy"
        else:
            status = "unhealthy"

        async with async_session() as session:
            result = await session.execute(select(ToolRegistry).where(ToolRegistry.name == tool_name))
            t = result.scalar_one_or_none()
            if t:
                t.status = status
                t.last_health_check = datetime.utcnow()
                await session.commit()

        return {"tool": tool_name, "status": status, "durationMs": duration_ms}
    except Exception as e:
        async with async_session() as session:
            result = await session.execute(select(ToolRegistry).where(ToolRegistry.name == tool_name))
            t = result.scalar_one_or_none()
            if t:
                t.status = "unreachable"
                t.last_health_check = datetime.utcnow()
                await session.commit()

        return {"tool": tool_name, "status": "unreachable", "error": str(e)}


async def health_check_all() -> list:
    tools = await list_tools()
    results = []
    for tool in tools:
        result = await health_check_tool(tool["name"])
        results.append(result)
    return results


async def sync_capabilities(tool_name: str) -> dict:
    tool = await get_tool(tool_name)
    if not tool:
        return {"error": f"Tool not found: {tool_name}"}

    endpoint = tool["endpoint"]
    caps_url = f"{endpoint.rstrip('/')}/tool/capabilities"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(caps_url)
        if resp.status_code == 200:
            data = resp.json()
            caps = data.get("capabilities", [])
            async with async_session() as session:
                result = await session.execute(select(ToolRegistry).where(ToolRegistry.name == tool_name))
                t = result.scalar_one_or_none()
                if t:
                    t.capabilities = caps
                    await session.commit()
            return {"tool": tool_name, "capabilities": caps}
        return {"tool": tool_name, "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"tool": tool_name, "error": str(e)}


async def disable_tool(tool_name: str) -> Optional[dict]:
    async with async_session() as session:
        result = await session.execute(select(ToolRegistry).where(ToolRegistry.name == tool_name))
        tool = result.scalar_one_or_none()
        if not tool:
            return None
        tool.status = "disabled"
        await session.commit()
        await session.refresh(tool)
        return _to_dict(tool)


async def enable_tool(tool_name: str) -> Optional[dict]:
    async with async_session() as session:
        result = await session.execute(select(ToolRegistry).where(ToolRegistry.name == tool_name))
        tool = result.scalar_one_or_none()
        if not tool:
            return None
        tool.status = "registered"
        await session.commit()
        await session.refresh(tool)
        return _to_dict(tool)


async def delete_tool(tool_name: str) -> dict:
    async with async_session() as session:
        result = await session.execute(select(ToolRegistry).where(ToolRegistry.name == tool_name))
        tool = result.scalar_one_or_none()
        if not tool:
            return {"error": f"Tool not found: {tool_name}"}
        await session.delete(tool)
        await session.commit()
        return {"deleted": tool_name}


def _to_dict(tool: ToolRegistry) -> dict:
    return {
        "id": tool.id,
        "name": tool.name,
        "displayName": tool.display_name,
        "description": tool.description,
        "version": tool.version,
        "endpoint": tool.endpoint,
        "status": tool.status,
        "lastHealthCheck": tool.last_health_check.isoformat() if tool.last_health_check else None,
        "capabilities": tool.capabilities,
        "createdAt": tool.created_at.isoformat() if tool.created_at else None,
        "updatedAt": tool.updated_at.isoformat() if tool.updated_at else None,
    }
