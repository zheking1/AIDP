import json
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.knowledge_tool.db.database import get_db
from app.tools.knowledge_tool.db.models import KnowledgeBase, ProjectKnowledgeBinding, KtDocument
from app.tools.knowledge_tool.schemas.knowledge_base import (
    ProjectBindingCreate, ProjectBindingInfo, AutoMatchRequest,
)
from app.tools.knowledge_tool.schemas.common import ApiResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["project-bindings"])


# ── 知识库侧绑定查询 ────────────────────────────────────

kb_bindings_router = APIRouter(prefix="/api/knowledge-bases", tags=["kb-bindings"])


@kb_bindings_router.get("/{kb_id}/bindings", response_model=ApiResponse)
async def list_kb_bindings(kb_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProjectKnowledgeBinding, KnowledgeBase.name, KnowledgeBase.slug, KnowledgeBase.kb_level)
        .join(KnowledgeBase, ProjectKnowledgeBinding.knowledge_base_id == KnowledgeBase.id)
        .where(ProjectKnowledgeBinding.knowledge_base_id == kb_id)
    )
    rows = result.all()
    items = []
    for binding, kb_name, kb_slug, kb_level in rows:
        items.append({
            "id": binding.id,
            "project_id": binding.project_id,
            "knowledge_base_id": binding.knowledge_base_id,
            "kb_name": kb_name,
            "kb_slug": kb_slug,
            "kb_level": kb_level,
            "binding_type": binding.binding_type,
            "priority": binding.priority,
            "created_at": binding.created_at.isoformat() if binding.created_at else "",
        })
    return ApiResponse(data={"items": items, "total": len(items)})


# ── 项目侧绑定查询与管理 ────────────────────────────────

@router.get("/{project_id}/knowledge-bases", response_model=ApiResponse)
async def list_project_bindings(project_id: str, db: AsyncSession = Depends(get_db)):
    """获取项目的所有知识库绑定 (含显式 + 继承 + 自动)"""
    result = await db.execute(
        select(ProjectKnowledgeBinding, KnowledgeBase)
        .join(KnowledgeBase, ProjectKnowledgeBinding.knowledge_base_id == KnowledgeBase.id)
        .where(
            ProjectKnowledgeBinding.project_id == project_id,
            KnowledgeBase.deleted_at.is_(None),
        )
        .order_by(ProjectKnowledgeBinding.priority.desc(), ProjectKnowledgeBinding.binding_type.desc())
    )
    rows = result.all()
    items = []
    for binding, kb in rows:
        doc_count_result = await db.execute(
            select(func.count(KtDocument.id)).where(
                KtDocument.knowledge_base_id == kb.id,
                KtDocument.deleted_at.is_(None),
            )
        )
        doc_count = doc_count_result.scalar() or 0
        items.append({
            "id": binding.id,
            "project_id": binding.project_id,
            "knowledge_base_id": kb.id,
            "kb_name": kb.name,
            "kb_slug": kb.slug,
            "kb_level": kb.kb_level,
            "binding_type": binding.binding_type,
            "priority": binding.priority,
            "document_count": doc_count,
            "created_at": binding.created_at.isoformat() if binding.created_at else "",
        })
    return ApiResponse(data={"items": items, "total": len(items)})


@router.post("/bindings", response_model=ApiResponse)
async def create_binding(req: ProjectBindingCreate, db: AsyncSession = Depends(get_db)):
    kb_result = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.id == req.knowledge_base_id,
            KnowledgeBase.deleted_at.is_(None),
        )
    )
    if not kb_result.scalar():
        raise HTTPException(status_code=404, detail="knowledge base not found")

    existing = await db.execute(
        select(ProjectKnowledgeBinding).where(
            ProjectKnowledgeBinding.project_id == req.project_id,
            ProjectKnowledgeBinding.knowledge_base_id == req.knowledge_base_id,
        )
    )
    if existing.scalar():
        raise HTTPException(status_code=400, detail="binding already exists")

    binding = ProjectKnowledgeBinding(
        project_id=req.project_id,
        knowledge_base_id=req.knowledge_base_id,
        binding_type=req.binding_type,
        priority=req.priority,
    )
    db.add(binding)
    await db.commit()
    await db.refresh(binding)

    return ApiResponse(data={
        "id": binding.id,
        "project_id": binding.project_id,
        "knowledge_base_id": binding.knowledge_base_id,
        "binding_type": binding.binding_type,
        "priority": binding.priority,
        "created_at": binding.created_at.isoformat() if binding.created_at else "",
    }, message="Binding created")


@router.delete("/bindings/{binding_id}", response_model=ApiResponse)
async def delete_binding(binding_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProjectKnowledgeBinding).where(ProjectKnowledgeBinding.id == binding_id)
    )
    binding = result.scalar()
    if not binding:
        raise HTTPException(status_code=404, detail="binding not found")

    await db.delete(binding)
    await db.commit()

    return ApiResponse(data={"id": binding_id}, message="Binding deleted")


@router.post("/{project_id}/auto-match", response_model=ApiResponse)
async def auto_match_knowledge_bases(
    project_id: str,
    req: AutoMatchRequest = None,
    db: AsyncSession = Depends(get_db),
):
    """根据项目的 tech_stack 自动匹配框架级知识库"""
    tech_stack = req.tech_stack if req else []

    if not tech_stack:
        return ApiResponse(data={"matched": [], "total": 0}, message="no tech_stack provided")

    framework_kbs_result = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.kb_level == "framework",
            KnowledgeBase.deleted_at.is_(None),
        )
    )
    framework_kbs = framework_kbs_result.scalars().all()

    existing_result = await db.execute(
        select(ProjectKnowledgeBinding.knowledge_base_id).where(
            ProjectKnowledgeBinding.project_id == project_id,
        )
    )
    existing_kb_ids = {r[0] for r in existing_result.all()}

    matched = []
    for kb in framework_kbs:
        kb_stack = json.loads(kb.tech_stack) if isinstance(kb.tech_stack, str) else (kb.tech_stack or [])
        overlap = [t for t in tech_stack if t.lower() in [s.lower() for s in kb_stack]]
        if overlap and kb.id not in existing_kb_ids:
            priority = len(overlap) * 5
            binding = ProjectKnowledgeBinding(
                project_id=project_id,
                knowledge_base_id=kb.id,
                binding_type="auto_matched",
                priority=priority,
            )
            db.add(binding)
            matched.append({
                "kb_id": kb.id,
                "kb_name": kb.name,
                "kb_slug": kb.slug,
                "overlap_tech": overlap,
                "priority": priority,
            })

    if matched:
        await db.commit()

    return ApiResponse(data={"matched": matched, "total": len(matched)})


@router.post("/auto-import", response_model=ApiResponse)
async def auto_import_knowledge(req: dict, db: AsyncSession = Depends(get_db)):
    project_id = req.get("project_id")
    project_path = req.get("project_path", "")
    import_options = req.get("import_options", {})
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id is required")

    from app.tools.knowledge_tool.services.project_scanner import ProjectKnowledgeScanner
    scanner = ProjectKnowledgeScanner()
    scan_result = scanner.scan_project(project_path)

    kb_result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.slug == f"project-{project_id}").limit(1)
    )
    kb = kb_result.scalar_one_or_none()
    if not kb:
        kb = KnowledgeBase(
            name=f"Project {project_id} Knowledge",
            slug=f"project-{project_id}",
            description=f"Auto-imported knowledge for project {project_id}",
            kb_level="project",
            visibility="private",
            owner_id=project_id,
        )
        db.add(kb)
        await db.flush()

    docs_imported = 0
    if import_options.get("include_docs", True):
        for doc in scan_result.get("documents", []):
            db_doc = KtDocument(
                knowledge_base_id=kb.id,
                workspace_id=project_id,
                project_id=project_id,
                title=doc["title"][:512],
                doc_type=doc["doc_type"],
                visibility="project",
                source_uri=doc.get("source_uri", ""),
                tags=json.dumps(doc.get("tags", [])),
                summary=doc.get("content", "")[:500],
            )
            db.add(db_doc)
            docs_imported += 1

    rules_stored = []
    if import_options.get("include_rules", True):
        rules_stored = scan_result.get("rules", [])
        if not hasattr(req, "_rules_store"):
            setattr(req, "_rules_store", [])
        getattr(req, "_rules_store").extend(rules_stored)

    binding = ProjectKnowledgeBinding(
        project_id=project_id,
        knowledge_base_id=kb.id,
        binding_type="auto_matched",
        priority=10,
    )
    db.add(binding)
    await db.commit()

    return ApiResponse(data={
        "kb_id": kb.id,
        "kb_slug": kb.slug,
        "documents_imported": docs_imported,
        "rules_extracted": len(rules_stored),
        "document_types": scan_result.get("document_types", {}),
    })


@router.get("/rules", response_model=ApiResponse)
async def get_coding_rules(
    project_id: str = None,
    category: str = None,
    limit: int = 50,
):
    rules = []
    if project_id:
        from app.tools.knowledge_tool.services.rule_extractor import CodingRuleExtractor
        extractor = CodingRuleExtractor()
        rules = extractor.extract_from_comments(
            os.path.join(os.getcwd(), "..", "..", "projects", project_id or "")
        )
    if category:
        rules = [r for r in rules if r.get("category") == category]
    rules = rules[:limit]
    categories = list(set(r.get("category") for r in rules))
    return ApiResponse(data={"rules": rules, "total": len(rules), "categories": categories})