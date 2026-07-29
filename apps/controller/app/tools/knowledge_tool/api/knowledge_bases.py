import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.knowledge_tool.db.database import get_db
from app.tools.knowledge_tool.db.models import KnowledgeBase, KtDocument, ProjectKnowledgeBinding
from app.tools.knowledge_tool.schemas.knowledge_base import (
    KnowledgeBaseCreate, KnowledgeBaseUpdate, KnowledgeBaseInfo,
)
from app.tools.knowledge_tool.schemas.common import ApiResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/knowledge-bases", tags=["knowledge-bases"])


def _serialize_kb(kb, doc_count: int = 0, parent_name: str = None):
    return {
        "id": kb.id,
        "name": kb.name,
        "slug": kb.slug,
        "description": kb.description,
        "kb_level": kb.kb_level,
        "parent_id": kb.parent_id,
        "parent_name": parent_name,
        "domains": json.loads(kb.domains) if isinstance(kb.domains, str) else (kb.domains or []),
        "keywords": json.loads(kb.keywords) if isinstance(kb.keywords, str) else (kb.keywords or []),
        "tech_stack": json.loads(kb.tech_stack) if isinstance(kb.tech_stack, str) else (kb.tech_stack or []),
        "visibility": kb.visibility,
        "chunk_size": kb.chunk_size or 512,
        "embedding_model": kb.embedding_model or "text-embedding-3-small",
        "document_count": doc_count,
        "created_at": kb.created_at.isoformat() if kb.created_at else "",
        "updated_at": kb.updated_at.isoformat() if kb.updated_at else "",
    }


@router.get("", response_model=ApiResponse)
async def list_knowledge_bases(
    kb_level: str = None,
    parent_id: str = None,
    visibility: str = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(KnowledgeBase).where(KnowledgeBase.deleted_at.is_(None))
    if kb_level:
        q = q.where(KnowledgeBase.kb_level == kb_level)
    if parent_id is not None:
        q = q.where(KnowledgeBase.parent_id == parent_id)
    if visibility:
        q = q.where(KnowledgeBase.visibility == visibility)
    q = q.order_by(KnowledgeBase.kb_level.asc(), KnowledgeBase.name.asc())
    result = await db.execute(q)
    kbs = result.scalars().all()

    items = []
    for kb in kbs:
        doc_count_result = await db.execute(
            select(func.count(KtDocument.id)).where(
                KtDocument.knowledge_base_id == kb.id,
                KtDocument.deleted_at.is_(None),
            )
        )
        doc_count = doc_count_result.scalar() or 0
        items.append(_serialize_kb(kb, doc_count=doc_count))

    return ApiResponse(data={"items": items, "total": len(items)})


@router.post("", response_model=ApiResponse)
async def create_knowledge_base(req: KnowledgeBaseCreate, db: AsyncSession = Depends(get_db)):
    slug = req.slug or req.name.lower().replace(" ", "-").replace("_", "-")
    existing = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.slug == slug)
    )
    if existing.scalar():
        raise HTTPException(status_code=400, detail=f"slug '{slug}' already exists")

    if req.parent_id:
        parent = await db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == req.parent_id,
                KnowledgeBase.deleted_at.is_(None),
            )
        )
        if not parent.scalar():
            raise HTTPException(status_code=404, detail="parent knowledge base not found")

    kb = KnowledgeBase(
        name=req.name,
        slug=slug,
        description=req.description,
        kb_level=req.kb_level,
        parent_id=req.parent_id,
        domains=json.dumps(req.domains, ensure_ascii=False),
        keywords=json.dumps(req.keywords, ensure_ascii=False),
        tech_stack=json.dumps(req.tech_stack, ensure_ascii=False),
        visibility=req.visibility,
        chunk_size=req.chunk_size,
        overlap_size=req.overlap_size,
        embedding_model=req.embedding_model,
    )
    db.add(kb)
    await db.commit()
    await db.refresh(kb)

    return ApiResponse(data=_serialize_kb(kb), message="Knowledge base created")


@router.get("/{kb_id}", response_model=ApiResponse)
async def get_knowledge_base(kb_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.deleted_at.is_(None),
        )
    )
    kb = result.scalar()
    if not kb:
        raise HTTPException(status_code=404, detail="knowledge base not found")

    doc_count_result = await db.execute(
        select(func.count(KtDocument.id)).where(
            KtDocument.knowledge_base_id == kb.id,
            KtDocument.deleted_at.is_(None),
        )
    )
    doc_count = doc_count_result.scalar() or 0

    parent_name = None
    if kb.parent_id:
        parent_result = await db.execute(
            select(KnowledgeBase.name).where(KnowledgeBase.id == kb.parent_id)
        )
        parent_row = parent_result.scalar()
        parent_name = parent_row

    data = _serialize_kb(kb, doc_count=doc_count, parent_name=parent_name)

    children_result = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.parent_id == kb.id,
            KnowledgeBase.deleted_at.is_(None),
        ).order_by(KnowledgeBase.name.asc())
    )
    children = children_result.scalars().all()
    data["children"] = [_serialize_kb(c) for c in children]

    ancestors = []
    current = kb.parent_id
    while current:
        anc_result = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == current, KnowledgeBase.deleted_at.is_(None))
        )
        anc = anc_result.scalar()
        if anc:
            ancestors.append({"id": anc.id, "name": anc.name, "kb_level": anc.kb_level})
            current = anc.parent_id
        else:
            break
    data["ancestors"] = ancestors

    return ApiResponse(data=data)


@router.put("/{kb_id}", response_model=ApiResponse)
async def update_knowledge_base(kb_id: str, req: KnowledgeBaseUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.deleted_at.is_(None),
        )
    )
    kb = result.scalar()
    if not kb:
        raise HTTPException(status_code=404, detail="knowledge base not found")

    if req.name is not None:
        kb.name = req.name
    if req.description is not None:
        kb.description = req.description
    if req.domains is not None:
        kb.domains = json.dumps(req.domains, ensure_ascii=False)
    if req.keywords is not None:
        kb.keywords = json.dumps(req.keywords, ensure_ascii=False)
    if req.tech_stack is not None:
        kb.tech_stack = json.dumps(req.tech_stack, ensure_ascii=False)
    if req.visibility is not None:
        kb.visibility = req.visibility
    if req.chunk_size is not None:
        kb.chunk_size = req.chunk_size
    if req.overlap_size is not None:
        kb.overlap_size = req.overlap_size
    if req.embedding_model is not None:
        kb.embedding_model = req.embedding_model

    kb.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(kb)

    return ApiResponse(data=_serialize_kb(kb), message="Knowledge base updated")


@router.delete("/{kb_id}", response_model=ApiResponse)
async def delete_knowledge_base(kb_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.deleted_at.is_(None),
        )
    )
    kb = result.scalar()
    if not kb:
        raise HTTPException(status_code=404, detail="knowledge base not found")

    kb.deleted_at = datetime.now(timezone.utc)
    await db.commit()

    return ApiResponse(data={"id": kb_id}, message="Knowledge base deleted")