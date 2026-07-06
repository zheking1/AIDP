from pathlib import Path
p = Path('/home/docker/AI-Code/controller/app/api/auth.py')
s = p.read_text()

# Add tool endpoints before User Management API
old = '''# ============================================================================
# User Management API (Admin only)
# ============================================================================'''

new = '''# ============================================================================
# Tool Management
# ============================================================================

@router.get("/tools")
async def api_list_tools(request: Request):
    """List all registered tools"""
    session_token = request.cookies.get("aidp_session")
    current_user = await AuthService.validate_session(session_token)
    if not current_user or not PermissionService.is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    from sqlalchemy import text
    from app.db.database import async_session_factory

    async with async_session_factory() as session:
        result = await session.execute(text("SELECT id, name, display_name, description, version, endpoint, status, last_health_check, capabilities, created_at, updated_at FROM tool_registry ORDER BY name"))
        rows = result.fetchall()

    items = []
    for r in rows:
        items.append({
            "id": r[0], "name": r[1], "display_name": r[2], "description": r[3],
            "version": r[4], "endpoint": r[5], "status": r[6],
            "last_health_check": r[7].isoformat() if r[7] else None,
            "capabilities": r[8], "created_at": r[9].isoformat() if r[9] else None,
            "updated_at": r[10].isoformat() if r[10] else None,
        })
    return {"items": items}


@router.post("/tools/{tool_id}/health-check")
async def api_tool_health_check(request: Request, tool_id: int):
    """Check tool health"""
    session_token = request.cookies.get("aidp_session")
    current_user = await AuthService.validate_session(session_token)
    if not current_user or not PermissionService.is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    from sqlalchemy import text
    from app.db.database import async_session_factory
    import httpx

    async with async_session_factory() as session:
        result = await session.execute(text("SELECT endpoint FROM tool_registry WHERE id=:id"), {"id": tool_id})
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Tool not found")
        endpoint = row[0]

    status = "unhealthy"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{endpoint}/health")
            if resp.status_code == 200:
                status = "healthy"
    except Exception:
        pass

    async with async_session_factory() as session:
        await session.execute(text("UPDATE tool_registry SET status=:status, last_health_check=NOW(), updated_at=NOW() WHERE id=:id"), {"status": status, "id": tool_id})
        await session.commit()

    return {"success": True, "status": status}


# ============================================================================
# User Management API (Admin only)
# ============================================================================'''

s = s.replace(old, new)

p.write_text(s)
print('OK')
