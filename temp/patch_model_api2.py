from pathlib import Path
p = Path('/home/docker/AI-Code/controller/app/api/auth.py')
s = p.read_text()

# Find the User Management API section and add model endpoints before it
old = '''# User Management API (Admin only)
# ============================================================================'''

new = '''# ============================================================================
# AI Model Management
# ============================================================================

@router.get("/ai-models")
async def api_list_ai_models(request: Request):
    """List all AI models (admin only)"""
    session_token = request.cookies.get("aidp_session")
    current_user = await AuthService.validate_session(session_token)
    if not current_user or not PermissionService.is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    from sqlalchemy import text
    from app.db.database import async_session_factory

    async with async_session_factory() as session:
        result = await session.execute(text("SELECT id, name, display_name, provider, model_id, api_key, base_url, max_tokens, temperature, timeout_secs, is_active, is_default, extra_config, created_at, updated_at FROM ai_models ORDER BY is_default DESC, provider, name"))
        rows = result.fetchall()

    items = []
    for r in rows:
        items.append({
            "id": str(r[0]), "name": r[1], "display_name": r[2], "provider": r[3],
            "model_id": r[4], "api_key": r[5], "base_url": r[6], "max_tokens": r[7],
            "temperature": r[8], "timeout_secs": r[9], "is_active": r[10], "is_default": r[11],
            "extra_config": r[12], "created_at": r[13].isoformat() if r[13] else None,
            "updated_at": r[14].isoformat() if r[14] else None,
        })
    return {"items": items}


@router.post("/ai-models")
async def api_create_ai_model(request: Request, data: AIModelRequest):
    """Create AI model (admin only)"""
    session_token = request.cookies.get("aidp_session")
    current_user = await AuthService.validate_session(session_token)
    if not current_user or not PermissionService.is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    from sqlalchemy import text
    from app.db.database import async_session_factory

    async with async_session_factory() as session:
        await session.execute(text(
            "INSERT INTO ai_models (name, display_name, provider, model_id, api_key, base_url, max_tokens, temperature, timeout_secs, is_active, is_default, extra_config, created_by) VALUES (:name, :display_name, :provider, :model_id, :api_key, :base_url, :max_tokens, :temperature, :timeout_secs, :is_active, :is_default, :extra_config, :created_by)"
        ), {"name": data.name, "display_name": data.display_name, "provider": data.provider, "model_id": data.model_id, "api_key": data.api_key, "base_url": data.base_url, "max_tokens": data.max_tokens, "temperature": data.temperature, "timeout_secs": data.timeout_secs, "is_active": data.is_active, "is_default": data.is_default, "extra_config": data.extra_config or {}, "created_by": str(current_user.id)})
        await session.commit()
    return {"success": True}


@router.put("/ai-models/{model_id}")
async def api_update_ai_model(request: Request, model_id: str, data: AIModelRequest):
    """Update AI model (admin only)"""
    session_token = request.cookies.get("aidp_session")
    current_user = await AuthService.validate_session(session_token)
    if not current_user or not PermissionService.is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    from sqlalchemy import text
    from app.db.database import async_session_factory

    async with async_session_factory() as session:
        await session.execute(text(
            "UPDATE ai_models SET name=:name, display_name=:display_name, provider=:provider, model_id=:model_id, api_key=:api_key, base_url=:base_url, max_tokens=:max_tokens, temperature=:temperature, timeout_secs=:timeout_secs, is_active=:is_active, is_default=:is_default, extra_config=:extra_config, updated_at=NOW() WHERE id=:id"
        ), {"id": model_id, "name": data.name, "display_name": data.display_name, "provider": data.provider, "model_id": data.model_id, "api_key": data.api_key, "base_url": data.base_url, "max_tokens": data.max_tokens, "temperature": data.temperature, "timeout_secs": data.timeout_secs, "is_active": data.is_active, "is_default": data.is_default, "extra_config": data.extra_config or {}})
        await session.commit()
    return {"success": True}


@router.delete("/ai-models/{model_id}")
async def api_delete_ai_model(request: Request, model_id: str):
    """Delete AI model (admin only)"""
    session_token = request.cookies.get("aidp_session")
    current_user = await AuthService.validate_session(session_token)
    if not current_user or not PermissionService.is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    from sqlalchemy import text
    from app.db.database import async_session_factory

    async with async_session_factory() as session:
        await session.execute(text("DELETE FROM ai_models WHERE id=:id"), {"id": model_id})
        await session.commit()
    return {"success": True}


# ============================================================================
# User Management API (Admin only)
# ============================================================================'''

s = s.replace(old, new)

p.write_text(s)
print('OK')
