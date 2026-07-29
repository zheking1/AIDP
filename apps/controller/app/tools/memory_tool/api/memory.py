from fastapi import APIRouter, Query, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.tools.memory_tool.db.database import get_db
from app.tools.memory_tool.services.consolidation_service import MemoryConsolidationService

router = APIRouter(prefix="/api/memory")


class MemoryCreateRequest(BaseModel):
    project: str
    category: str
    title: str
    content: str
    tags: Optional[str] = None
    pinned: bool = False
    user_id: Optional[int] = None
    source_type: str = "manual"
    source_ref: Optional[str] = None
    memory_tier: str = "episodic"


@router.post("")
async def create(req: MemoryCreateRequest, db: AsyncSession = Depends(get_db)):
    svc = MemoryConsolidationService(db)
    result = await svc.create_memory(
        title=req.title,
        content=req.content,
        project=req.project,
        user_id=req.user_id,
        category=req.category,
        source_type=req.source_type,
        source_ref=req.source_ref,
        memory_tier=req.memory_tier,
    )
    return JSONResponse(content=result)


@router.get("")
async def list(project: str = None, tier: str = None, user_id: int = None,
               limit: int = 50, db: AsyncSession = Depends(get_db)):
    svc = MemoryConsolidationService(db)
    memories = await svc.get_memories(project=project, tier=tier, user_id=user_id, limit=limit)
    return JSONResponse(content={"memories": memories, "total": len(memories)})


@router.get("/search")
async def search_memories(project: str = Query(None), query: str = Query(""), limit: int = Query(5), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import or_
    from app.tools.memory_tool.db.models import MemoryEntry
    stmt = select(MemoryEntry).where(MemoryEntry.deleted_at.is_(None))
    if project:
        stmt = stmt.where(MemoryEntry.project == project)
    if query:
        pattern = f"%{query}%"
        stmt = stmt.where(or_(MemoryEntry.title.ilike(pattern), MemoryEntry.content.ilike(pattern)))
    stmt = stmt.limit(limit).order_by(MemoryEntry.created_at.desc())
    result = await db.execute(stmt)
    entries = result.scalars().all()
    return JSONResponse(content=[e.to_dict() for e in entries])


@router.get("/{memory_id}")
async def get(memory_id: int, db: AsyncSession = Depends(get_db)):
    svc = MemoryConsolidationService(db)
    await svc.increment_access(memory_id)
    result = await db.execute(
        db.query.__class__.__bases__[0] if False else __import__("sqlalchemy", fromlist=["select"]).select(
            __import__("app.db.models", fromlist=["MemoryEntry"]).MemoryEntry
        ).where(__import__("app.db.models", fromlist=["MemoryEntry"]).MemoryEntry.id == memory_id)
    )
    from app.tools.memory_tool.db.models import MemoryEntry
    result = await db.execute(
        __import__("sqlalchemy", fromlist=["select"]).select(MemoryEntry).where(MemoryEntry.id == memory_id)
    )
    entry = result.scalar_one_or_none()
    if not entry or entry.deleted_at:
        raise HTTPException(status_code=404, detail="Memory not found")
    return JSONResponse(content={
        "id": entry.id,
        "title": entry.title,
        "content": entry.content,
        "project": entry.project,
        "category": entry.category,
        "tier": entry.memory_tier,
        "source_type": entry.source_type,
        "source_ref": entry.source_ref,
        "confidence": entry.confidence,
        "access_count": entry.access_count or 0,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    })


@router.post("/{memory_id}/promote")
async def promote(memory_id: int, req: dict, db: AsyncSession = Depends(get_db)):
    body = await req if hasattr(req, "json") else JSONResponse(content=req).body
    import json
    new_tier = json.loads(body.decode()).get("tier", "semantic")
    svc = MemoryConsolidationService(db)
    result = await svc.promote_tier(memory_id, new_tier)
    if not result:
        raise HTTPException(status_code=400, detail="Cannot promote to lower tier")
    return JSONResponse(content=result)


@router.delete("/{memory_id}")
async def delete(memory_id: int, db: AsyncSession = Depends(get_db)):
    svc = MemoryConsolidationService(db)
    await svc.delete_memory(memory_id)
    return JSONResponse(content={"success": True})
