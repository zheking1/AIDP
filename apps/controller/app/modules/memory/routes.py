"""
Memory Module Routes
记忆模块 API 路由
"""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.db.database import async_session_factory
from app.modules.memory.models import MemoryEntry, MemoryRelation, ContextPackage
from app.core.permissions import require_permissions
from app.core.utils import get_current_user_id
from app.api.auth import get_current_user

router = APIRouter()


class MemoryCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    category: str = Field("other")
    memory_tier: str = Field("semantic")
    parent_id: Optional[str] = None
    confidence_score: float = Field(1.0, ge=0.0, le=1.0)
    source_type: str = Field("manual")
    extra_data: Optional[dict] = Field(default_factory=dict)


class MemoryUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = None
    category: Optional[str] = None
    memory_tier: Optional[str] = None
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    extra_data: Optional[dict] = None


class MemoryRelationCreate(BaseModel):
    target_id: str = Field(...)
    relation_type: str = Field(...)
    strength: float = Field(1.0, ge=0.0, le=1.0)
    description: Optional[str] = None


class SearchQuery(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(10, ge=1, le=50)
    category: Optional[str] = None
    memory_tier: Optional[str] = None


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        yield session


@router.get("/memories")
async def list_memories(
    project_id: Optional[int] = Query(None),
    category: Optional[str] = Query(None),
    memory_tier: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(MemoryEntry).where(MemoryEntry.deleted_at.is_(None))
    if project_id:
        query = query.where(MemoryEntry.project_id == project_id)
    if category:
        query = query.where(MemoryEntry.category == category)
    if memory_tier:
        query = query.where(MemoryEntry.memory_tier == memory_tier)
    if search:
        pattern = f"%{search}%"
        query = query.where(or_(MemoryEntry.title.ilike(pattern), MemoryEntry.content.ilike(pattern)))

    query = query.order_by(desc(MemoryEntry.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    memories = result.scalars().all()
    return {"items": [m.to_dict() for m in memories], "total": len(memories)}


@router.post("/memories")
async def create_memory(
    data: MemoryCreate,
    project_id: Optional[int] = Query(None),
    user=require_permissions("memory:write"),
    db: AsyncSession = Depends(get_db)
):
    user_id = get_current_user_id(user)
    memory = MemoryEntry(
        project_id=project_id, user_id=user_id,
        title=data.title, content=data.content,
        category=data.category, memory_tier=data.memory_tier,
        parent_id=data.parent_id, confidence_score=data.confidence_score,
        source_type=data.source_type, extra_data=json.dumps(data.extra_data)
    )
    db.add(memory)
    await db.commit()
    await db.refresh(memory)
    return memory.to_dict()


@router.get("/memories/{memory_id}")
async def get_memory(
    memory_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(MemoryEntry).where(and_(MemoryEntry.id == memory_id, MemoryEntry.deleted_at.is_(None)))
    )
    memory = result.scalar_one_or_none()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    memory.access_count += 1
    memory.last_accessed_at = datetime.now(timezone.utc)
    await db.commit()
    return memory.to_dict(include_content=True)


@router.put("/memories/{memory_id}")
async def update_memory(
    memory_id: str,
    data: MemoryUpdate,
    user=require_permissions("memory:write"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(MemoryEntry).where(and_(MemoryEntry.id == memory_id, MemoryEntry.deleted_at.is_(None)))
    )
    memory = result.scalar_one_or_none()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    if data.title is not None:
        memory.title = data.title
    if data.content is not None:
        memory.content = data.content
    if data.category is not None:
        memory.category = data.category
    if data.memory_tier is not None:
        memory.memory_tier = data.memory_tier
    if data.confidence_score is not None:
        memory.confidence_score = data.confidence_score
    if data.extra_data is not None:
        memory.extra_data = json.dumps(data.extra_data)
    await db.commit()
    await db.refresh(memory)
    return memory.to_dict()


@router.delete("/memories/{memory_id}")
async def delete_memory(
    memory_id: str,
    user=require_permissions("memory:delete"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(MemoryEntry).where(and_(MemoryEntry.id == memory_id, MemoryEntry.deleted_at.is_(None)))
    )
    memory = result.scalar_one_or_none()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    memory.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return {"success": True, "message": "Memory deleted"}


@router.get("/memories/{memory_id}/relations")
async def get_memory_relations(
    memory_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(MemoryEntry).where(and_(MemoryEntry.id == memory_id, MemoryEntry.deleted_at.is_(None)))
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Memory not found")
    outgoing = await db.execute(select(MemoryRelation).where(MemoryRelation.source_id == memory_id))
    incoming = await db.execute(select(MemoryRelation).where(MemoryRelation.target_id == memory_id))
    return {"outgoing": [r.to_dict() for r in outgoing.scalars().all()], "incoming": [r.to_dict() for r in incoming.scalars().all()]}


@router.post("/memories/{memory_id}/relations")
async def create_memory_relation(
    memory_id: str,
    data: MemoryRelationCreate,
    user=require_permissions("memory:write"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(MemoryEntry).where(and_(MemoryEntry.id == memory_id, MemoryEntry.deleted_at.is_(None))))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Source memory not found")
    result = await db.execute(select(MemoryEntry).where(and_(MemoryEntry.id == data.target_id, MemoryEntry.deleted_at.is_(None))))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Target memory not found")
    relation = MemoryRelation(source_id=memory_id, target_id=data.target_id, relation_type=data.relation_type, strength=data.strength, description=data.description)
    db.add(relation)
    await db.commit()
    await db.refresh(relation)
    return relation.to_dict()


@router.delete("/relations/{relation_id}")
async def delete_relation(
    relation_id: str,
    user=require_permissions("memory:write"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(MemoryRelation).where(MemoryRelation.id == relation_id))
    relation = result.scalar_one_or_none()
    if not relation:
        raise HTTPException(status_code=404, detail="Relation not found")
    await db.delete(relation)
    await db.commit()
    return {"success": True, "message": "Relation deleted"}


@router.post("/search")
async def search_memories(
    query: SearchQuery,
    project_id: Optional[int] = Query(None),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    search_pattern = f"%{query.query}%"
    conditions = [MemoryEntry.deleted_at.is_(None), or_(MemoryEntry.title.ilike(search_pattern), MemoryEntry.content.ilike(search_pattern))]
    if project_id:
        conditions.append(MemoryEntry.project_id == project_id)
    if query.category:
        conditions.append(MemoryEntry.category == query.category)
    if query.memory_tier:
        conditions.append(MemoryEntry.memory_tier == query.memory_tier)
    sql_query = select(MemoryEntry).where(and_(*conditions)).limit(query.top_k)
    result = await db.execute(sql_query)
    memories = result.scalars().all()
    return {"query": query.query, "total": len(memories), "results": [{"memory": m.to_dict(), "score": 0.95, "highlights": []} for m in memories]}


@router.get("/graph")
async def get_memory_graph(
    project_id: Optional[int] = Query(None),
    depth: int = Query(2, ge=1, le=3),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(MemoryEntry).where(MemoryEntry.deleted_at.is_(None))
    if project_id:
        query = query.where(MemoryEntry.project_id == project_id)
    query = query.limit(100)
    result = await db.execute(query)
    memories = result.scalars().all()
    nodes = []
    memory_ids = set()
    for m in memories:
        nodes.append({"id": m.id, "label": m.title, "category": m.category, "memory_tier": m.memory_tier, "confidence_score": m.confidence_score, "access_count": m.access_count})
        memory_ids.add(m.id)
    relations_query = select(MemoryRelation).where(and_(MemoryRelation.source_id.in_(memory_ids), MemoryRelation.target_id.in_(memory_ids)))
    result = await db.execute(relations_query)
    links = [{"source": r.source_id, "target": r.target_id, "type": r.relation_type, "strength": r.strength} for r in result.scalars().all()]
    return {"nodes": nodes, "links": links, "total_nodes": len(nodes), "total_links": len(links)}


@router.get("/stats")
async def get_memory_stats(
    project_id: Optional[int] = Query(None),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    conditions = [MemoryEntry.deleted_at.is_(None)]
    if project_id:
        conditions.append(MemoryEntry.project_id == project_id)
    total = await db.execute(select(func.count(MemoryEntry.id)).where(and_(*conditions)))
    by_category = await db.execute(select(MemoryEntry.category, func.count(MemoryEntry.id)).where(and_(*conditions)).group_by(MemoryEntry.category))
    by_tier = await db.execute(select(MemoryEntry.memory_tier, func.count(MemoryEntry.id)).where(and_(*conditions)).group_by(MemoryEntry.memory_tier))
    return {"total": total.scalar() or 0, "by_category": {r[0]: r[1] for r in by_category.all()}, "by_tier": {r[0]: r[1] for r in by_tier.all()}}


class ContextPackageCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    memory_ids: List[str] = Field(default_factory=list)
    is_template: bool = False


class ContextPackageUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    memory_ids: Optional[List[str]] = None
    is_template: Optional[bool] = None


@router.get("/context/list")
async def list_context_packages(
    project_id: Optional[int] = Query(None),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(ContextPackage)
    if project_id:
        query = query.where(ContextPackage.project_id == project_id)
    query = query.order_by(desc(ContextPackage.updated_at))
    result = await db.execute(query)
    return {"items": [p.to_dict() for p in result.scalars().all()]}


@router.post("/context/create")
async def create_context_package(
    data: ContextPackageCreate,
    project_id: Optional[int] = Query(None),
    user=require_permissions("memory:write"),
    db: AsyncSession = Depends(get_db)
):
    user_id = get_current_user_id(user)
    pkg = ContextPackage(
        project_id=project_id, user_id=user_id,
        name=data.name, description=data.description,
        memory_ids=json.dumps(data.memory_ids),
        is_template=data.is_template
    )
    db.add(pkg); await db.commit(); await db.refresh(pkg)
    return pkg.to_dict()


@router.get("/context/{pkg_id}")
async def get_context_package(
    pkg_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(ContextPackage).where(ContextPackage.id == pkg_id))
    pkg = result.scalar_one_or_none()
    if not pkg: raise HTTPException(status_code=404, detail="Context package not found")
    return pkg.to_dict(include_context=True)


@router.put("/context/{pkg_id}")
async def update_context_package(
    pkg_id: str,
    data: ContextPackageUpdate,
    user=require_permissions("memory:write"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(ContextPackage).where(ContextPackage.id == pkg_id))
    pkg = result.scalar_one_or_none()
    if not pkg: raise HTTPException(status_code=404, detail="Context package not found")
    if data.name is not None: pkg.name = data.name
    if data.description is not None: pkg.description = data.description
    if data.memory_ids is not None: pkg.memory_ids = json.dumps(data.memory_ids)
    if data.is_template is not None: pkg.is_template = data.is_template
    await db.commit(); await db.refresh(pkg)
    return pkg.to_dict(include_context=True)


@router.delete("/context/{pkg_id}")
async def delete_context_package(
    pkg_id: str,
    user=require_permissions("memory:write"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(ContextPackage).where(ContextPackage.id == pkg_id))
    pkg = result.scalar_one_or_none()
    if not pkg: raise HTTPException(status_code=404, detail="Context package not found")
    await db.delete(pkg); await db.commit()
    return {"success": True}


@router.post("/context/preview")
async def preview_context(
    memory_ids: List[str],
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(MemoryEntry).where(and_(MemoryEntry.id.in_(memory_ids), MemoryEntry.deleted_at.is_(None)))
    )
    memories = result.scalars().all()
    context = "\n\n---\n\n".join([f"## {m.title}\n{m.content[:1000]}" for m in memories])
    return {"context": context, "memory_count": len(memories), "total_chars": len(context)}


@router.get("/review/queue")
async def get_review_queue(
    project_id: Optional[int] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    conditions = [MemoryEntry.deleted_at.is_(None), MemoryEntry.ai_suggested == True]
    if project_id: conditions.append(MemoryEntry.project_id == project_id)
    query = select(MemoryEntry).where(and_(*conditions)).order_by(MemoryEntry.created_at).limit(limit)
    result = await db.execute(query)
    return {"items": [m.to_dict() for m in result.scalars().all()]}


@router.post("/review/{memory_id}")
async def review_memory(
    memory_id: str,
    status: str = Query("approved"),
    comment: Optional[str] = Query(None),
    user=require_permissions("memory:write"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(MemoryEntry).where(and_(MemoryEntry.id == memory_id, MemoryEntry.deleted_at.is_(None))))
    memory = result.scalar_one_or_none()
    if not memory: raise HTTPException(status_code=404, detail="Memory not found")
    memory.ai_review_status = status
    if comment is not None: memory.ai_review_comment = comment
    await db.commit()
    return memory.to_dict()


@router.post("/review/{memory_id}/reset")
async def reset_review(
    memory_id: str,
    user=require_permissions("memory:write"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(MemoryEntry).where(and_(MemoryEntry.id == memory_id, MemoryEntry.deleted_at.is_(None))))
    memory = result.scalar_one_or_none()
    if not memory: raise HTTPException(status_code=404, detail="Memory not found")
    memory.ai_review_status = "pending"
    memory.ai_review_comment = None
    await db.commit()
    return memory.to_dict()


@router.post("/relations/auto-generate")
async def auto_generate_relations(
    project_id: Optional[int] = Query(None),
    user=require_permissions("memory:write"),
    db: AsyncSession = Depends(get_db)
):
    """为项目下的记忆自动生成关系（基于共享标签/分类）"""
    conditions = [MemoryEntry.deleted_at.is_(None)]
    if project_id: conditions.append(MemoryEntry.project_id == project_id)
    result = await db.execute(select(MemoryEntry).where(and_(*conditions)).limit(50))
    memories = result.scalars().all()
    count = 0
    for i, m1 in enumerate(memories):
        for m2 in memories[i+1:]:
            existing = await db.execute(select(MemoryRelation).where(and_(
                MemoryRelation.source_id == m1.id, MemoryRelation.target_id == m2.id
            )))
            if existing.scalar_one_or_none(): continue
            if m1.category == m2.category:
                rel = MemoryRelation(source_id=m1.id, target_id=m2.id, relation_type="related", strength=0.5)
                db.add(rel); count += 1
    await db.commit()
    return {"success": True, "relations_created": count}


@router.get("/timeline")
async def get_timeline(
    project_id: Optional[int] = Query(None),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取按时间线组织的记忆"""
    conditions = [MemoryEntry.deleted_at.is_(None)]
    if project_id:
        conditions.append(MemoryEntry.project_id == project_id)
    result = await db.execute(
        select(MemoryEntry).where(and_(*conditions)).order_by(desc(MemoryEntry.created_at)).limit(200)
    )
    memories = result.scalars().all()

    timeline = {}
    for m in memories:
        date_key = m.created_at.strftime("%Y-%m") if m.created_at else "unknown"
        if date_key not in timeline:
            timeline[date_key] = []
        timeline[date_key].append({
            "id": m.id, "title": m.title, "category": m.category,
            "content_preview": m.content[:150] if m.content else "",
            "memory_tier": m.memory_tier,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        })

    sorted_months = sorted(timeline.keys(), reverse=True)
    return {
        "timeline": [
            {"month": month, "count": len(timeline[month]), "items": timeline[month]}
            for month in sorted_months
        ],
        "total": len(memories)
    }


@router.post("/context/generate")
async def generate_context_package(
    data: ContextPackageCreate,
    project_id: Optional[int] = Query(None),
    user=require_permissions("memory:write"),
    db: AsyncSession = Depends(get_db)
):
    """创建上下文包并自动生成预览"""
    user_id = get_current_user_id(user)

    memories_result = await db.execute(
        select(MemoryEntry).where(and_(
            MemoryEntry.id.in_(data.memory_ids),
            MemoryEntry.deleted_at.is_(None)
        ))
    )
    memories = memories_result.scalars().all()
    mem_dict = {m.id: m for m in memories}

    ordered = [mem_dict[mid] for mid in data.memory_ids if mid in mem_dict]
    generated = ""
    total_tokens = 0
    for m in ordered:
        section = f"## {m.title}\n**分类**: {m.category} | **层级**: {m.memory_tier}\n\n{m.content}\n\n---\n\n"
        generated += section
        total_tokens += len(section) // 3

    pkg = ContextPackage(
        project_id=project_id, user_id=user_id,
        name=data.name, description=data.description,
        memory_ids=json.dumps(data.memory_ids),
        generated_context=generated,
        total_tokens=total_tokens,
        is_template=data.is_template,
    )
    db.add(pkg)
    await db.commit()
    await db.refresh(pkg)

    return {"success": True, "package": pkg.to_dict(include_context=True), "memory_count": len(ordered)}
