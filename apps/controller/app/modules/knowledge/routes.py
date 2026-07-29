"""
Knowledge Module Routes
知识库模块 API 路由
"""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
import json
import re

from app.db.database import async_session_factory
from app.modules.knowledge.models import KnowledgeBase, KnowledgeDocument, DocumentChunk, ProjectKnowledgeBinding
from app.core.permissions import require_permissions, check_scope_read_access
from app.core.utils import get_current_user_id
from app.api.auth import get_current_user

router = APIRouter()


class BaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    slug: Optional[str] = None
    description: Optional[str] = None
    kb_level: str = Field("project")
    parent_id: Optional[str] = None
    domains: str = Field("[]")  # JSON string
    keywords: str = Field("[]")
    tech_stack: str = Field("[]")
    visibility: str = Field("private")
    chunking_strategy: str = Field("fixed")
    chunk_size: int = Field(500, ge=100, le=5000)
    chunk_overlap: int = Field(50, ge=0, le=500)
    embedding_model: str = Field("text-embedding-3-small")


class BaseUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    kb_level: Optional[str] = None
    parent_id: Optional[str] = None
    domains: Optional[str] = None
    keywords: Optional[str] = None
    tech_stack: Optional[str] = None
    visibility: Optional[str] = None
    chunking_strategy: Optional[str] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    embedding_model: Optional[str] = None
    document_count: Optional[int] = None
    total_chunks: Optional[int] = None


class DocumentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    source_type: str = Field("manual")
    source_uri: Optional[str] = None
    mime_type: Optional[str] = None
    category: Optional[str] = None
    tags: str = Field("[]")
    checksum: Optional[str] = None
    version: str = Field("v1")
    summary: Optional[str] = None
    visibility: str = Field("private")
    owner_type: str = Field("personal")
    created_by: Optional[str] = None
    updated_by: Optional[str] = None


class SearchQuery(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(10, ge=1, le=50)


class DocumentCreateSimple(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    doc_type: str = Field("markdown")
    category: Optional[str] = None
    base_id: Optional[str] = None


@router.post("/documents")
async def create_document_standalone(
    data: DocumentCreateSimple,
    user=require_permissions("knowledge:write"),
):
    async with async_session_factory() as db:
        user_id = get_current_user_id(user)
        doc = KnowledgeDocument(
            base_id=data.base_id, user_id=user_id,
            title=data.title, content=data.content, category=data.category,
            source_type="manual", processing_status="completed"
        )
        db.add(doc)
        if data.base_id:
            result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == data.base_id))
            kb = result.scalar_one_or_none()
            if kb: kb.document_count += 1
        await db.commit()
        await db.refresh(doc)
        return doc.to_dict(include_content=True)


class UpdateDocumentRequest(BaseModel):
    title: Optional[str] = None
    doc_type: Optional[str] = None
    category: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[str] = None
    summary: Optional[str] = None
    visibility: Optional[str] = None


class BindingCreate(BaseModel):
    project_id: str
    knowledge_base_id: str
    binding_type: str = Field("explicit")
    priority: int = 0


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        yield session


def _slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r'[^a-z0-9\u4e00-\u9fff]+', '-', s)
    return s.strip('-')[:120]


def _kb_base_filter(user_id: str = None):
    """KnowledgeBase 访问隔离: private→创建者, team→登录用户, public→所有人"""
    if not user_id:
        return KnowledgeBase.visibility == "public"
    return or_(
        KnowledgeBase.visibility.in_(["public", "team"]),
        and_(KnowledgeBase.visibility == "private", KnowledgeBase.user_id == user_id),
    )


def _kb_doc_filter(user_id: str = None):
    """KnowledgeDocument 访问隔离: personal/private→创建者, team→登录用户, public/system→所有人"""
    if not user_id:
        return and_(
            KnowledgeDocument.visibility == "public",
            KnowledgeDocument.owner_type.in_(["team", "system"]),
        )
    return or_(
        KnowledgeDocument.visibility.in_(["public", "team"]),
        KnowledgeDocument.owner_type.in_(["team", "system"]),
        and_(KnowledgeDocument.user_id == user_id),
    )


def _check_kb_owner(doc, user_id: str):
    """校验文档/知识库归属: 非创建者不能修改他人 personal 内容"""
    if doc.user_id and doc.user_id != user_id:
        if getattr(doc, 'visibility', 'private') == 'private' or getattr(doc, 'owner_type', 'personal') == 'personal':
            raise HTTPException(status_code=403, detail="Cannot modify other user's personal content")
    return doc


@router.get("/bases")
async def list_bases(
    project_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await check_scope_read_access(user, "knowledge", "global")
    user_id = get_current_user_id(user)
    query = select(KnowledgeBase).where(and_(
        KnowledgeBase.deleted_at.is_(None),
        _kb_base_filter(user_id),
    ))
    if project_id:
        query = query.where(KnowledgeBase.project_id == project_id)
    if search:
        query = query.where(KnowledgeBase.name.ilike(f"%{search}%"))
    query = query.order_by(desc(KnowledgeBase.updated_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    bases = result.scalars().all()
    return {"items": [b.to_dict() for b in bases], "total": len(bases)}


@router.post("/bases")
async def create_base(
    data: BaseCreate,
    project_id: Optional[int] = Query(None),
    user=require_permissions("knowledge:write"),
    db: AsyncSession = Depends(get_db)
):
    user_id = get_current_user_id(user)
    slug = data.slug or _slugify(data.name)
    # Ensure unique slug
    existing = await db.execute(select(KnowledgeBase).where(KnowledgeBase.slug == slug))
    if existing.scalar_one_or_none():
        slug = slug + "-" + str(int(datetime.now().timestamp()))
    kb = KnowledgeBase(
        project_id=project_id, user_id=user_id,
        name=data.name, slug=slug, description=data.description,
        kb_level=data.kb_level, parent_id=data.parent_id,
        domains=data.domains, keywords=data.keywords, tech_stack=data.tech_stack,
        visibility=data.visibility,
        chunking_strategy=data.chunking_strategy,
        chunk_size=data.chunk_size, chunk_overlap=data.chunk_overlap,
        embedding_model=data.embedding_model
    )
    db.add(kb)
    await db.commit()
    await db.refresh(kb)
    return kb.to_dict()


@router.get("/bases/{base_id}")
async def get_base(
    base_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(KnowledgeBase).where(and_(KnowledgeBase.id == base_id, KnowledgeBase.deleted_at.is_(None)))
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    await check_scope_read_access(user, "knowledge", "global")
    user_id = get_current_user_id(user)
    if user_id is None and kb.visibility == "private":
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    if kb.visibility == "private" and kb.user_id and kb.user_id != user_id:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    data = kb.to_dict()
    # Include children
    children = await db.execute(
        select(KnowledgeBase).where(and_(KnowledgeBase.parent_id == base_id, KnowledgeBase.deleted_at.is_(None)))
    )
    data["children"] = [c.to_dict() for c in children.scalars().all()]
    # Include parent info
    if kb.parent_id:
        parent = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == kb.parent_id)
        )
        p = parent.scalar_one_or_none()
        data["parent"] = {"id": p.id, "name": p.name} if p else None
    return data


@router.put("/bases/{base_id}")
async def update_base(
    base_id: str,
    data: BaseUpdate,
    user=require_permissions("knowledge:write"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(KnowledgeBase).where(and_(KnowledgeBase.id == base_id, KnowledgeBase.deleted_at.is_(None)))
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    user_id = get_current_user_id(user)
    _check_kb_owner(kb, user_id)
    for field, val in data.model_dump(exclude_none=True).items():
        setattr(kb, field, val)
    kb.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(kb)
    return kb.to_dict()


@router.delete("/bases/{base_id}")
async def delete_base(
    base_id: str,
    user=require_permissions("knowledge:delete"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(KnowledgeBase).where(and_(KnowledgeBase.id == base_id, KnowledgeBase.deleted_at.is_(None)))
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    user_id = get_current_user_id(user)
    _check_kb_owner(kb, user_id)
    kb.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return {"success": True, "message": "Knowledge base deleted"}


@router.get("/documents-list")
async def list_all_documents(
    base_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    doc_type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await check_scope_read_access(user, "knowledge", "global")
    user_id = get_current_user_id(user)
    query = select(KnowledgeDocument).where(and_(
        KnowledgeDocument.deleted_at.is_(None),
        _kb_doc_filter(user_id),
    ))
    if base_id:
        query = query.where(KnowledgeDocument.base_id == base_id)
    if doc_type:
        query = query.where(KnowledgeDocument.doc_type == doc_type)
    if category:
        query = query.where(KnowledgeDocument.category == category)
    if status:
        query = query.where(KnowledgeDocument.status == status)
    if search:
        query = query.where(KnowledgeDocument.title.ilike(f"%{search}%"))
    total = await db.execute(select(func.count()).select_from(KnowledgeDocument).where(and_(KnowledgeDocument.deleted_at.is_(None), _kb_doc_filter(user_id))))
    total_count = total.scalar() or 0
    query = query.order_by(desc(KnowledgeDocument.updated_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    docs = result.scalars().all()
    return {"items": [d.to_dict() for d in docs], "total": total_count}


@router.get("/bases/{base_id}/documents")
async def list_documents(
    base_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await check_scope_read_access(user, "knowledge", "global")
    user_id = get_current_user_id(user)
    query = select(KnowledgeDocument).where(
        and_(KnowledgeDocument.base_id == base_id, KnowledgeDocument.deleted_at.is_(None), _kb_doc_filter(user_id))
    ).order_by(desc(KnowledgeDocument.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    docs = result.scalars().all()
    return {"items": [d.to_dict() for d in docs], "total": len(docs)}


@router.post("/bases/{base_id}/documents")
async def create_document(
    base_id: str,
    data: DocumentCreate,
    user=require_permissions("knowledge:write"),
    db: AsyncSession = Depends(get_db)
):
    user_id = get_current_user_id(user)
    doc = KnowledgeDocument(
        base_id=base_id, user_id=user_id,
        title=data.title, content=data.content, category=data.category,
        source_type=data.source_type, source_uri=data.source_uri,
        mime_type=data.mime_type, processing_status="completed"
    )
    db.add(doc)

    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == base_id)
    )
    kb = result.scalar_one_or_none()
    if kb:
        kb.document_count += 1

    await db.commit()
    await db.refresh(doc)
    return doc.to_dict(include_content=True)


class UpdateDocumentRequest(BaseModel):
    title: Optional[str] = None
    doc_type: Optional[str] = None
    category: Optional[str] = None
    content: Optional[str] = None
    promotion_status: Optional[str] = None
    promotion_report: Optional[str] = None
    promotion_source_id: Optional[str] = None
    promotion_source_scope: Optional[str] = None


@router.put("/documents/{doc_id}")
async def update_document(
    doc_id: str,
    data: UpdateDocumentRequest,
    user=require_permissions("knowledge:write"),
    db: AsyncSession = Depends(get_db)
):
    user_id = get_current_user_id(user)
    result = await db.execute(
        select(KnowledgeDocument).where(and_(KnowledgeDocument.id == doc_id, KnowledgeDocument.deleted_at.is_(None)))
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    _check_kb_owner(doc, user_id)
    for field, val in data.model_dump(exclude_none=True).items():
        setattr(doc, field, val)
    doc.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(doc)
    return doc.to_dict(include_content=True)


@router.get("/documents/{doc_id}")
async def get_document(
    doc_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(KnowledgeDocument).where(and_(KnowledgeDocument.id == doc_id, KnowledgeDocument.deleted_at.is_(None)))
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    await check_scope_read_access(user, "knowledge", "global")
    user_id = get_current_user_id(user)
    if doc.visibility == "private" and doc.user_id and doc.user_id != user_id:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.owner_type == "personal" and doc.user_id and doc.user_id != user_id:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc.to_dict(include_content=True)


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    user=require_permissions("knowledge:delete"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(KnowledgeDocument).where(and_(KnowledgeDocument.id == doc_id, KnowledgeDocument.deleted_at.is_(None)))
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    user_id = get_current_user_id(user)
    _check_kb_owner(doc, user_id)
    doc.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return {"success": True, "message": "Document deleted"}


# ── Project-KB Bindings ──────────────────────────────────

@router.get("/bindings/{kb_id}")
async def list_bindings(
    kb_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await check_scope_read_access(user, "knowledge", "global")
    result = await db.execute(
        select(ProjectKnowledgeBinding).where(ProjectKnowledgeBinding.knowledge_base_id == kb_id)
    )
    return {"items": [b.to_dict() for b in result.scalars().all()]}


@router.post("/bindings")
async def create_binding(
    data: BindingCreate,
    user=require_permissions("knowledge:write"),
    db: AsyncSession = Depends(get_db)
):
    existing = await db.execute(
        select(ProjectKnowledgeBinding).where(
            and_(ProjectKnowledgeBinding.project_id == data.project_id,
                 ProjectKnowledgeBinding.knowledge_base_id == data.knowledge_base_id)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Binding already exists")
    binding = ProjectKnowledgeBinding(
        project_id=data.project_id,
        knowledge_base_id=data.knowledge_base_id,
        binding_type=data.binding_type,
        priority=data.priority
    )
    db.add(binding)
    await db.commit()
    await db.refresh(binding)
    return binding.to_dict()


@router.delete("/bindings/{binding_id}")
async def delete_binding(
    binding_id: str,
    user=require_permissions("knowledge:delete"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(ProjectKnowledgeBinding).where(ProjectKnowledgeBinding.id == binding_id)
    )
    binding = result.scalar_one_or_none()
    if not binding:
        raise HTTPException(status_code=404, detail="Binding not found")
    await db.delete(binding)
    await db.commit()
    return {"success": True}


# ── Web Import ──────────────────────────────────

from app.services.web_import_service import WebImportService


class ImportAnalyzeRequest(BaseModel):
    url: str = Field(..., min_length=1)
    top_k: int = Field(10, ge=1, le=100)


class ImportDirectRequest(BaseModel):
    url: str = Field(..., min_length=1)
    kb_name: Optional[str] = None
    kb_level: str = Field("framework")
    auto_detect: bool = True


@router.post("/import-web/analyze")
async def analyze_url(
    data: ImportAnalyzeRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    svc = WebImportService()
    result = await svc.analyze(data.url)
    return result


@router.post("/import-web/direct-import")
async def direct_import(
    data: ImportDirectRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    svc = WebImportService()
    result = await svc.import_from_url(data.url, data.kb_name, data.kb_level, data.auto_detect)
    return result


@router.post("/search")
async def search_documents(
    query: SearchQuery,
    base_id: Optional[str] = Query(None),
    project_id: Optional[int] = Query(None),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await check_scope_read_access(user, "knowledge", "global")
    user_id = get_current_user_id(user)
    keywords = query.query.lower().split()
    search_pattern = f"%{query.query}%"
    conditions = [
        KnowledgeDocument.deleted_at.is_(None),
        or_(KnowledgeDocument.title.ilike(search_pattern), KnowledgeDocument.content.ilike(search_pattern))
    ]
    if base_id:
        conditions.append(KnowledgeDocument.base_id == base_id)
    if project_id:
        conditions.append(KnowledgeDocument.project_id == project_id)

    conditions.append(_kb_doc_filter(user_id))
    sql_query = select(KnowledgeDocument).where(and_(*conditions)).limit(query.top_k)
    result = await db.execute(sql_query)
    docs = result.scalars().all()

    results = []
    for doc in docs:
        title = (doc.title or "").lower()
        content = (doc.content or "").lower()
        title_matches = sum(1 for kw in keywords if kw in title)
        content_matches = sum(1 for kw in keywords if kw in content)
        score = min(1.0, (title_matches * 3 + content_matches) / max(len(keywords), 1) / 4)
        highlights = []
        for kw in keywords:
            if kw in title or kw in content:
                highlights.append(kw)
        results.append({"document": doc.to_dict(), "score": round(score, 3), "highlights": list(set(highlights))})

    results.sort(key=lambda x: x["score"], reverse=True)
    return {"query": query.query, "total": len(results), "results": results}


class SemanticSearchQuery(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(10, ge=1, le=50)


@router.post("/search/semantic")
async def search_documents_semantic(
    query: SemanticSearchQuery,
    base_id: Optional[str] = Query(None),
    project_id: Optional[int] = Query(None),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.semantic_search import semantic_search
    user_id = get_current_user_id(user)
    results = await semantic_search(
        db=db, query=query.query, top_k=query.top_k,
        base_id=base_id, project_id=project_id, user_id=user_id,
    )
    return {"query": query.query, "total": len(results), "results": results}


@router.get("/documents/{doc_id}/chunks")
async def get_document_chunks(
    doc_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await check_scope_read_access(user, "knowledge", "global")
    result = await db.execute(
        select(DocumentChunk).where(DocumentChunk.document_id == doc_id)
        .order_by(DocumentChunk.chunk_index).offset(skip).limit(limit)
    )
    chunks = result.scalars().all()
    return {"items": [c.to_dict() for c in chunks], "total": len(chunks)}


@router.get("/stats")
async def get_knowledge_stats(
    project_id: Optional[int] = Query(None),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await check_scope_read_access(user, "knowledge", "global")
    base_conditions = [KnowledgeBase.deleted_at.is_(None)]
    doc_conditions = [KnowledgeDocument.deleted_at.is_(None)]
    if project_id:
        base_conditions.append(KnowledgeBase.project_id == project_id)
        doc_conditions.append(KnowledgeDocument.project_id == project_id)

    total_bases = await db.execute(select(func.count(KnowledgeBase.id)).where(and_(*base_conditions)))
    total_docs = await db.execute(select(func.count(KnowledgeDocument.id)).where(and_(*doc_conditions)))

    return {"total_bases": total_bases.scalar() or 0, "total_documents": total_docs.scalar() or 0}


@router.get("/graph")
async def get_knowledge_graph(
    project_id: Optional[int] = Query(None),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取知识图谱数据（知识库层级 + 文档关系）"""
    await check_scope_read_access(user, "knowledge", "global")

    base_conditions = [KnowledgeBase.deleted_at.is_(None)]
    doc_conditions = [KnowledgeDocument.deleted_at.is_(None)]
    if project_id:
        base_conditions.append(KnowledgeBase.project_id == project_id)

    bases_result = await db.execute(
        select(KnowledgeBase).where(and_(*base_conditions)).limit(100)
    )
    bases = bases_result.scalars().all()

    nodes = []
    links = []
    base_ids = [b.id for b in bases]

    for b in bases:
        nodes.append({
            "id": b.id, "label": b.name, "type": "base",
            "level": b.kb_level, "doc_count": b.document_count,
            "chunk_count": b.total_chunks,
        })
        if b.parent_id and b.parent_id in base_ids:
            links.append({"source": b.parent_id, "target": b.id, "type": "parent"})

    if base_ids:
        docs_result = await db.execute(
            select(KnowledgeDocument).where(
                and_(KnowledgeDocument.base_id.in_(base_ids), *doc_conditions)
            ).limit(200)
        )
        docs = docs_result.scalars().all()
        for d in docs:
            nodes.append({
                "id": d.id, "label": d.title, "type": "document",
                "category": d.category, "chunk_count": d.chunk_count,
            })
            if d.base_id:
                links.append({"source": d.base_id, "target": d.id, "type": "contains"})

    return {"nodes": nodes, "links": links, "total_nodes": len(nodes), "total_links": len(links)}
