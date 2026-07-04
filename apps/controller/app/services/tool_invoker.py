import time
import uuid
import logging
from typing import Optional

import httpx
from sqlalchemy import select
from app.db.models import ToolRegistry, ToolInvocation
from app.db.database import async_session_factory as async_session
from app.config import settings

logger = logging.getLogger(__name__)


async def invoke_tool(
    tool_name: str,
    capability: str,
    arguments: dict,
    user_id: Optional[int] = None,
) -> dict:
    tool_result = await _find_tool(tool_name)
    if "error" in tool_result:
        return tool_result

    tool = tool_result["tool"]
    endpoint = tool.endpoint
    invoke_url = f"{endpoint.rstrip('/')}/tool/invoke"
    trace_id = f"tr_{uuid.uuid4().hex[:12]}"

    start = time.time()
    status = "success"
    result = None
    error = None

    try:
        payload = {
            "trace_id": trace_id,
            "capability": capability,
            "context": {"user_id": user_id},
            "input": arguments if isinstance(arguments, dict) else {},
        }
        async with httpx.AsyncClient(timeout=settings.INVOCATION_TIMEOUT) as client:
            resp = await client.post(invoke_url, json=payload)

        if resp.status_code == 200:
            result = resp.json()
        else:
            status = "error"
            error = f"HTTP {resp.status_code}: {resp.text[:500]}"
    except httpx.TimeoutException:
        status = "error"
        error = "Timeout"
    except Exception as e:
        status = "error"
        error = str(e)

    duration_ms = int((time.time() - start) * 1000)

    async with async_session() as session:
        record = ToolInvocation(
            tool_name=tool_name,
            capability=capability,
            arguments=arguments,
            result=result,
            status=status,
            duration_ms=duration_ms,
            error=error,
            user_id=user_id,
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)

    return {
        "id": record.id,
        "toolName": tool_name,
        "capability": capability,
        "status": status,
        "result": result,
        "error": error,
        "durationMs": duration_ms,
    }


async def get_invocation_history(tool_name: Optional[str] = None, limit: int = 20) -> list:
    async with async_session() as session:
        q = select(ToolInvocation)
        if tool_name:
            q = q.where(ToolInvocation.tool_name == tool_name)
        q = q.order_by(ToolInvocation.id.desc()).limit(limit)
        result = await session.execute(q)
        return [
            {
                "id": r.id,
                "toolName": r.tool_name,
                "capability": r.capability,
                "status": r.status,
                "durationMs": r.duration_ms,
                "error": r.error,
                "createdAt": r.created_at.isoformat() if r.created_at else None,
            }
            for r in result.scalars().all()
        ]


async def _find_tool(tool_name: str) -> dict:
    async with async_session() as session:
        result = await session.execute(select(ToolRegistry).where(ToolRegistry.name == tool_name))
        tool = result.scalar_one_or_none()

        if not tool:
            return {"error": f"Tool not found: {tool_name}"}

        if tool.status == "disabled":
            return {"error": f"Tool is disabled: {tool_name}"}

        if tool.status == "unreachable":
            return {"error": f"Tool is unreachable: {tool_name}"}

        return {"tool": tool}
