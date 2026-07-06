from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from app.services.tool_registry import (
    register_tool, list_tools, get_tool, health_check_tool,
    health_check_all, sync_capabilities, disable_tool, enable_tool, delete_tool,
)
from app.services.tool_invoker import invoke_tool, get_invocation_history

router = APIRouter(prefix="/api/tools")


class ToolRegisterRequest(BaseModel):
    name: str
    endpoint: str
    displayName: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None


class ToolInvokeRequest(BaseModel):
    capability: str
    arguments: dict = {}
    userId: Optional[int] = None


@router.post("")
async def register(req: ToolRegisterRequest):
    return await register_tool(
        name=req.name,
        endpoint=req.endpoint,
        display_name=req.displayName,
        description=req.description,
        version=req.version,
    )


@router.get("")
async def list_all(status: Optional[str] = Query(None)):
    return await list_tools(status=status)


@router.get("/health/all")
async def health_all():
    return await health_check_all()


@router.get("/{tool_name}")
async def get_one(tool_name: str):
    return await get_tool(tool_name)


@router.post("/{tool_name}/health")
async def health_one(tool_name: str):
    return await health_check_tool(tool_name)


@router.post("/{tool_name}/sync")
async def sync(tool_name: str):
    return await sync_capabilities(tool_name)


@router.post("/{tool_name}/disable")
async def disable(tool_name: str):
    return await disable_tool(tool_name)


@router.post("/{tool_name}/enable")
async def enable(tool_name: str):
    return await enable_tool(tool_name)


@router.delete("/{tool_name}")
async def delete(tool_name: str):
    return await delete_tool(tool_name)


@router.post("/{tool_name}/invoke")
async def invoke(tool_name: str, req: ToolInvokeRequest):
    return await invoke_tool(
        tool_name=tool_name,
        capability=req.capability,
        arguments=req.arguments,
        user_id=req.userId,
    )


@router.get("/invocations/history")
async def invocations(tool_name: Optional[str] = Query(None), limit: int = Query(20)):
    return await get_invocation_history(tool_name=tool_name, limit=limit)


@router.get("/dashboard/stats")
async def dashboard_stats():
    """Get dashboard statistics."""
    tools = await list_tools()
    invocations = await get_invocation_history(limit=1000)
    
    # Count today's invocations
    today = datetime.now().date()
    today_calls = 0
    for inv in invocations:
        if isinstance(inv, dict) and 'created_at' in inv:
            try:
                inv_date = datetime.fromisoformat(inv['created_at'].replace('Z', '+00:00')).date()
                if inv_date == today:
                    today_calls += 1
            except:
                pass
    
    return {
        "total_tools": len(tools),
        "healthy_tools": len([t for t in tools if t.get('status') == 'healthy']),
        "today_calls": today_calls,
        "recent_invocations": invocations[:10]
    }
