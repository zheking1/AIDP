from fastapi import APIRouter, Request, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/audit", tags=["audit"])


async def _get_current_user(request: Request):
    session_token = request.cookies.get("aidp_session")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = await AuthService.validate_session(session_token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid session")
    return user


@router.get("/")
async def list_audits(request: Request, db: AsyncSession = Depends(get_db)):
    user = await _get_current_user(request)
    result = await db.execute(text(
        "SELECT id, user_id, action, resource_id, new_values AS details, created_at FROM audit_logs ORDER BY created_at DESC LIMIT 100"
    ))
    rows = result.fetchall()
    audits = []
    for r in rows:
        audits.append({
            "id": str(r.id), "user_id": str(r.user_id), "action": r.action or "",
            "resource": r.resource_id or "", "details": r.details or "",
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return JSONResponse(content={"audits": audits})


@router.get("/logs")
async def list_audit_logs(
    request: Request,
    limit: int = Query(50, ge=1, le=1000),
    action: str = Query(None),
    db: AsyncSession = Depends(get_db)
):
    user = await _get_current_user(request)
    sql = "SELECT id, user_id, action, 'audit' AS resource_type, resource_id, new_values AS detail, created_at FROM audit_logs"
    params = {}
    if action:
        sql += " WHERE action = :action"
        params["action"] = action
    sql += " ORDER BY created_at DESC LIMIT :limit"
    params["limit"] = limit

    result = await db.execute(text(sql), params)
    rows = result.fetchall()
    items = []
    for r in rows:
        items.append({
            "id": str(r.id),
            "user_id": str(r.user_id),
            "action": r.action or "",
            "resource_type": r.resource_type or "",
            "resource_id": str(r.resource_id) if r.resource_id else "",
            "detail": r.detail,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return JSONResponse(content={"items": items})


@router.post("/")
async def log_audit(request: Request, db: AsyncSession = Depends(get_db)):
    user = await _get_current_user(request)
    body = await request.json()
    user_id = body.get("user_id", user.id)
    action = body.get("action", "")
    resource = body.get("resource", "")
    details = body.get("details", "")

    await db.execute(text(
        "INSERT INTO audit_logs (user_id, action, resource, details) VALUES (:uid, :action, :res, :det)"
    ), {"uid": user_id, "action": action, "res": resource, "det": details})
    await db.commit()
    return JSONResponse(content={"success": True})
