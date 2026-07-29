"""
文档分类与自动导入模块
提供文档分类、规则提取、智能路由存储功能
"""

import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import os

from fastapi import APIRouter, Header
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import async_session_factory
from app.core.utils import gen_uuid
from app.services.doc_classifier import DocClassifier

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Models ──────────────────────────────────────────

class ClassifyRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    filename: str = ""

class ClassifyResponse(BaseModel):
    classification: Dict[str, Any]
    source: str = "llm"

class ImportDocItem(BaseModel):
    title: str
    content: str
    filename: str = ""
    source_uri: str = ""

class ImportRequest(BaseModel):
    project_id: Optional[int] = None
    kb_name: Optional[str] = None
    documents: List[ImportDocItem]
    auto_classify: bool = True
    auto_create_kb: bool = True

class ImportResult(BaseModel):
    total: int
    classified: int
    stored: Dict[str, int]
    errors: List[str]

# ── Routes ──────────────────────────────────────────

@router.post("/classify", response_model=ClassifyResponse)
async def classify_document(
    data: ClassifyRequest,
):
    result = await DocClassifier.classify(data.title, data.content, data.filename)
    return ClassifyResponse(classification=result, source="llm" if result.get("confidence") != "low" else "fallback")


@router.post("/import", response_model=ImportResult)
async def import_documents(
    data: ImportRequest,
    x_api_key: Optional[str] = Header(None),
):
    user_id = "admin"
    if x_api_key:
        from app.db.auth_models import ApiKey
        async with async_session_factory() as db:
            result = await db.execute(
                select(ApiKey).where(ApiKey.key == x_api_key, ApiKey.is_active == True)
            )
            key = result.scalar_one_or_none()
            if key:
                user_id = key.user_id or "admin"

    stored = {"knowledge": 0, "rule": 0, "skill": 0, "agent": 0}
    errors = []

    for doc in data.documents:
            try:
                classification = await DocClassifier.classify(doc.title, doc.content, doc.filename)
                doc_type = classification.get("doc_type", "document")

                if doc_type in ("document", "standard"):
                    async with async_session_factory() as kdb:
                        result = await _store_as_knowledge(kdb, doc, classification, data, user_id)
                        if result:
                            stored["knowledge"] += 1

                if doc_type == "rule" or (doc_type == "standard" and classification.get("has_rules")):
                    async with async_session_factory() as rdb:
                        result = await _store_as_rule(rdb, doc, classification, user_id)
                        if result:
                            stored["rule"] += 1

                if doc_type == "skill":
                    async with async_session_factory() as sdb:
                        result = await _store_as_skill(sdb, doc, classification, user_id)
                        if result:
                            stored["skill"] += 1

                if doc_type == "agent":
                    async with async_session_factory() as adb:
                        result = await _store_as_agent(adb, doc, classification, user_id)
                        if result:
                            stored["agent"] += 1

            except Exception as e:
                errors.append(f"{doc.title}: {str(e)[:200]}")

    return ImportResult(
        total=len(data.documents),
        classified=len(data.documents) - len(errors),
        stored=stored,
        errors=errors,
    )


# ── Storage Logic ───────────────────────────────────

async def _ensure_knowledge_base(db: AsyncSession, classification: dict, user_id: str, project_id: int = None) -> str:
    from app.modules.knowledge.models import KnowledgeBase
    level = classification.get("level", "project")
    tech_stack = classification.get("tech_stack", [])

    kb_name = None
    if tech_stack:
        kb_name = f"{tech_stack[0]} {level} docs"
    else:
        kb_name = f"{level} knowledge base"

    result = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.name == kb_name,
            KnowledgeBase.deleted_at.is_(None),
        ).limit(1)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing.id

    import re
    slug = kb_name.lower().strip()
    slug = re.sub(r'[^a-z0-9\u4e00-\u9fff]+', '-', slug)[:120]

    kb = KnowledgeBase(
        project_id=project_id, user_id=user_id,
        name=kb_name, slug=slug,
        description=f"Auto-created {level} knowledge base",
        kb_level=level,
        domains=json.dumps([classification.get("category", "")]),
        tech_stack=json.dumps(tech_stack),
        visibility="private",
    )
    db.add(kb)
    await db.flush()
    await db.refresh(kb)
    return kb.id


async def _store_as_knowledge(db: AsyncSession, doc: ImportDocItem, classification: dict, request: ImportRequest, user_id: str) -> bool:
    from app.modules.knowledge.models import KnowledgeDocument

    base_id = None
    if request.auto_create_kb:
        base_id = await _ensure_knowledge_base(db, classification, user_id, request.project_id)

    # Use raw INSERT to avoid schema mismatch with ORM
    doc_id = gen_uuid()
    now = datetime.now(timezone.utc)
    tags_json = json.dumps(classification.get("tags", []))
    extra_json = json.dumps({
        "classification": classification,
        "imported_at": now.isoformat(),
    })
    summary = (classification.get("summary") or "")[:500]

    await db.execute(
        text("""
            INSERT INTO aidp_knowledge_documents
            (id, base_id, project_id, user_id, title, source_type, source_uri,
             content, category, tags, summary, processing_status, extra_data,
             owner_type, visibility, created_at, updated_at)
            VALUES (:id, :base_id, :project_id, :user_id, :title, :source_type, :source_uri,
             :content, :category, :tags, :summary, :status, :extra,
             :owner_type, :visibility, :now, :now)
        """),
        {
            "id": doc_id,
            "base_id": base_id,
            "project_id": request.project_id,
            "user_id": user_id,
            "title": doc.title[:500],
            "source_type": "import",
            "source_uri": doc.source_uri or doc.filename,
            "content": doc.content,
            "category": classification.get("category"),
            "tags": tags_json,
            "summary": summary,
            "status": "completed",
            "extra": extra_json,
            "owner_type": "team",
            "visibility": "public",
            "now": now,
        }
    )
    await db.commit()

    # Generate and store embedding for semantic search
    try:
        from app.services.semantic_search import get_embedding
        text_for_embed = f"{doc.title} {summary} {doc.content[:2000]}"
        emb = await get_embedding(text_for_embed)
        if emb:
            await db.execute(
                text("UPDATE aidp_knowledge_documents SET embedding = :emb, embedding_model = :model WHERE id = :id"),
                {"emb": json.dumps(emb), "model": "bge-m3", "id": doc_id}
            )
            await db.commit()
    except Exception:
        pass

    # Also push to doc-index for wiki/code-linking/drift features
    await _store_to_doc_index(doc, classification)

    return True


async def _store_to_doc_index(doc: ImportDocItem, classification: dict):
    import httpx
    try:
        tech_stack = classification.get("tech_stack", [])
        framework = tech_stack[0] if tech_stack else None
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                "http://localhost:18087/api/docs",
                json={
                    "title": doc.title,
                    "content": doc.content,
                    "source": "import",
                    "language": classification.get("category"),
                    "framework": framework,
                    "category": classification.get("category"),
                    "level": classification.get("level"),
                    "tags": classification.get("tags", []),
                },
                headers={"Content-Type": "application/json"},
            )
    except Exception as e:
        logger.warning(f"doc-index push failed for {doc.title}: {e}")


async def _store_as_rule(db: AsyncSession, doc: ImportDocItem, classification: dict, user_id: str) -> bool:
    from app.modules.rules.models import Rule

    rule = Rule(
        id=gen_uuid(),
        name=doc.title[:200],
        content=doc.content,
        description=(classification.get("summary") or "")[:500],
        category=classification.get("category", "code_style"),
        severity=classification.get("severity", "medium"),
        scope=classification.get("scope", "project"),
        tags=json.dumps(classification.get("tags", [])),
        user_id=user_id,
    )
    db.add(rule)
    await db.commit()
    return True


async def _store_as_skill(db: AsyncSession, doc: ImportDocItem, classification: dict, user_id: str) -> bool:
    from app.modules.skills.models import Skill

    content = doc.content
    instruction = ""

    if "instruction:" in content.lower():
        parts = content.split("content:", 1) if "content:" in content.lower() else [content]
        if len(parts) > 1:
            instruction = parts[0].replace("instruction:", "").replace("Instruction:", "").strip()
            content = parts[1].strip()

    skill = Skill(
        id=gen_uuid(),
        name=doc.title[:200],
        content=content,
        instruction=instruction or (classification.get("summary") or "")[:500],
        description=(classification.get("summary") or "")[:500],
        tags=json.dumps(classification.get("tags", [])),
        scope="project",
        user_id=user_id,
    )
    db.add(skill)
    await db.commit()
    return True


async def _store_as_agent(db: AsyncSession, doc: ImportDocItem, classification: dict, user_id: str) -> bool:
    from app.modules.agents.models import Agent

    agent = Agent(
        id=gen_uuid(),
        name=doc.title[:200],
        role=classification.get("role", ""),
        instructions=doc.content if classification.get("has_instructions") else "",
        scope="personal",
        user_id=user_id,
        extra_data=json.dumps({
            "classification": classification,
            "source": doc.filename or doc.source_uri,
        }),
    )
    db.add(agent)
    await db.commit()
    return True