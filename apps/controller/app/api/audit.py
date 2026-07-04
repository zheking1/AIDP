from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("/")
async def list_audits(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await db.execute(text(
        "SELECT id, user_id, action, resource_id, details, created_at FROM audit_logs ORDER BY created_at DESC LIMIT 100"
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


@router.post("/")
async def log_audit(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    user_id = body.get("user_id")
    action = body.get("action", "")
    resource = body.get("resource", "")
    details = body.get("details", "")

    await db.execute(text(
        "INSERT INTO audit_logs (user_id, action, resource, details) VALUES (:uid, :action, :res, :det)"
    ), {"uid": user_id, "action": action, "res": resource, "det": details})
    await db.commit()
    return JSONResponse(content={"success": True})
