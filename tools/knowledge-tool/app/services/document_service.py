from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import KtDocument
from app.schemas.document import DocumentCreateRequest, DocumentInfo


async def create_document(db: AsyncSession, req: DocumentCreateRequest) -> DocumentInfo:
    """Create a new document."""
    doc = KtDocument(
        workspace_id=req.workspace_id,
        project_id=req.project_id,
        title=req.title,
        doc_type=req.doc_type,
        visibility=req.visibility,
        version=req.version,
        tags=req.tags,
        source_uri=req.source_uri,
        index_status="created",
        metadata_=req.metadata,
    )
    db.add(doc)
    await db.flush()

    return _doc_to_info(doc)


async def get_document(db: AsyncSession, doc_id: str, workspace_id: str) -> Optional[DocumentInfo]:
    """Get a document by ID with scope check."""
    result = await db.execute(
        select(KtDocument).where(
            KtDocument.id == doc_id,
            KtDocument.workspace_id == workspace_id,
            KtDocument.deleted_at.is_(None),
        )
    )
    doc = result.scalar_one_or_none()
    if doc:
        return _doc_to_info(doc)
    return None


async def list_documents(
    db: AsyncSession,
    workspace_id: str,
    project_id: Optional[str] = None,
    doc_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    owner_type: Optional[str] = None,
) -> list[DocumentInfo]:
    """List documents with scope filter."""
    query = select(KtDocument).where(
        KtDocument.workspace_id == workspace_id,
        KtDocument.deleted_at.is_(None),
    )

    if project_id:
        query = query.where(KtDocument.project_id == project_id)
    if doc_type:
        query = query.where(KtDocument.doc_type == doc_type)
    if owner_type:
        query = query.where(KtDocument.owner_type == owner_type)

    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    docs = result.scalars().all()
    return [_doc_to_info(d) for d in docs]


async def delete_document(db: AsyncSession, doc_id: str, workspace_id: str) -> bool:
    """Soft delete a document."""
    from datetime import datetime, timezone
    result = await db.execute(
        select(KtDocument).where(
            KtDocument.id == doc_id,
            KtDocument.workspace_id == workspace_id,
            KtDocument.deleted_at.is_(None),
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        return False
    doc.deleted_at = datetime.now(timezone.utc)
    return True


def _doc_to_info(doc: KtDocument) -> DocumentInfo:
    return DocumentInfo(
        id=doc.id,
        workspace_id=doc.workspace_id,
        project_id=doc.project_id,
        title=doc.title,
        doc_type=doc.doc_type,
        visibility=doc.visibility,
        version=doc.version,
        index_status=doc.index_status,
        tags=doc.tags or [],
        checksum=doc.checksum,
        created_at=doc.created_at.isoformat() if doc.created_at else "",
        updated_at=doc.updated_at.isoformat() if doc.updated_at else "",
    )
