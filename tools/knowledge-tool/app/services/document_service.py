import json
import os
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import KtDocument
from app.schemas.document import DocumentCreateRequest, DocumentInfo
from app.config import settings


async def create_document(db: AsyncSession, req: DocumentCreateRequest) -> DocumentInfo:
    doc = KtDocument(
        workspace_id=req.workspace_id,
        project_id=req.project_id,
        knowledge_base_id=req.knowledge_base_id,
        title=req.title,
        doc_type=req.doc_type,
        visibility=req.visibility,
        version=req.version,
        tags=json.dumps(req.tags, ensure_ascii=False) if req.tags else "[]",
        source_uri=req.source_uri,
        index_status="created",
        metadata_=json.dumps(req.metadata, ensure_ascii=False) if req.metadata else "{}",
    )
    db.add(doc)
    await db.flush()
    return _doc_to_info(doc)


async def get_document(db: AsyncSession, doc_id: str, workspace_id: str = None) -> Optional[DocumentInfo]:
    q = select(KtDocument).where(
        KtDocument.id == doc_id,
        KtDocument.deleted_at.is_(None),
    )
    if workspace_id:
        q = q.where(KtDocument.workspace_id == workspace_id)
    result = await db.execute(q)
    doc = result.scalar_one_or_none()
    return _doc_to_info(doc) if doc else None


async def list_documents(
    db: AsyncSession,
    workspace_id: str = None,
    project_id: str = None,
    knowledge_base_id: str = None,
    doc_type: str = None,
    page: int = 1,
    page_size: int = 20,
    owner_type: str = None,
) -> list[DocumentInfo]:
    q = select(KtDocument).where(KtDocument.deleted_at.is_(None))

    if workspace_id:
        q = q.where(KtDocument.workspace_id == workspace_id)
    if project_id:
        q = q.where(KtDocument.project_id == project_id)
    if knowledge_base_id:
        q = q.where(KtDocument.knowledge_base_id == knowledge_base_id)
    if doc_type:
        q = q.where(KtDocument.doc_type == doc_type)
    if owner_type:
        q = q.where(KtDocument.owner_type == owner_type)

    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    docs = result.scalars().all()
    return [_doc_to_info(d) for d in docs]


async def delete_document(db: AsyncSession, doc_id: str, workspace_id: str = None) -> bool:
    q = select(KtDocument).where(
        KtDocument.id == doc_id,
        KtDocument.deleted_at.is_(None),
    )
    if workspace_id:
        q = q.where(KtDocument.workspace_id == workspace_id)
    result = await db.execute(q)
    doc = result.scalar_one_or_none()
    if not doc:
        return False
    doc.deleted_at = datetime.now(timezone.utc)
    return True


def _doc_to_info(doc: KtDocument) -> DocumentInfo:
    tags = doc.tags
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except (json.JSONDecodeError, TypeError):
            tags = []
    return DocumentInfo(
        id=doc.id,
        workspace_id=doc.workspace_id,
        project_id=doc.project_id,
        knowledge_base_id=doc.knowledge_base_id,
        title=doc.title,
        doc_type=doc.doc_type,
        visibility=doc.visibility,
        version=doc.version,
        index_status=doc.index_status,
        tags=tags or [],
        checksum=doc.checksum,
        file_name=doc.file_name,
        mime_type=doc.mime_type,
        file_size=doc.file_size,
        object_key=doc.object_key,
        created_at=doc.created_at.isoformat() if doc.created_at else "",
        updated_at=doc.updated_at.isoformat() if doc.updated_at else "",
    )


async def get_document_content(db: AsyncSession, doc_id: str) -> str:
    """Get document content from storage."""
    q = select(KtDocument).where(
        KtDocument.id == doc_id,
        KtDocument.deleted_at.is_(None),
    )
    result = await db.execute(q)
    doc = result.scalar_one_or_none()
    
    if not doc or not doc.object_key:
        return ""
    
    # Read from local storage
    if settings.STORAGE_PROVIDER == "local":
        file_path = os.path.join(settings.STORAGE_LOCAL_ROOT, doc.object_key)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading file: {e}")
            return ""
    
    return ""