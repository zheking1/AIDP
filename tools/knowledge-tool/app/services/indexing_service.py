import io
import json
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import KtDocument, KtDocumentChunk, KtDocumentIndexJob
from app.parser.markdown_parser import MarkdownParser
from app.parser.plain_text_parser import PlainTextParser
from app.chunk.markdown_chunker import MarkdownChunker
from app.chunk.base import ChunkingOptions
from app.embedding.mock_provider import MockEmbeddingProvider
from app.storage.local_storage import LocalObjectStorage
from app.config import settings
from app.schemas.document import IndexJobInfo


markdown_parser = MarkdownParser()
plain_text_parser = PlainTextParser()
markdown_chunker = MarkdownChunker()
embedding_provider = MockEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
storage = LocalObjectStorage(root_path=settings.STORAGE_LOCAL_ROOT)


async def create_index_job(
    db: AsyncSession,
    document_id: str,
    workspace_id: str,
    project_id: str = None,
    chunk_size: int = 800,
    overlap: int = 120,
    embedding_model: str = "mock-embedding-v1",
    force: bool = False,
) -> IndexJobInfo:
    """Create an indexing job for a document."""
    doc_result = await db.execute(
        select(KtDocument).where(
            KtDocument.id == document_id,
            KtDocument.workspace_id == workspace_id,
            KtDocument.deleted_at.is_(None),
        )
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise ValueError("Document not found")

    job = KtDocumentIndexJob(
        document_id=document_id,
        workspace_id=workspace_id,
        project_id=project_id,
        status="pending",
        trigger_type="manual",
        force_reindex=force,
        chunk_size=chunk_size,
        overlap_size=overlap,
        embedding_model=embedding_model,
    )
    db.add(job)
    await db.flush()

    return _job_to_info(job)


async def run_index_job(db: AsyncSession, job_id: str) -> IndexJobInfo:
    """Execute an indexing job."""
    job_result = await db.execute(
        select(KtDocumentIndexJob).where(KtDocumentIndexJob.id == job_id)
    )
    job = job_result.scalar_one_or_none()
    if not job:
        raise ValueError("Job not found")

    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    await db.flush()

    try:
        doc_result = await db.execute(
            select(KtDocument).where(KtDocument.id == job.document_id)
        )
        doc = doc_result.scalar_one_one()
        if not doc:
            raise ValueError("Document not found")

        content = ""
        if doc.object_key:
            try:
                file_obj = storage.get(doc.object_key)
                content = file_obj.read().decode("utf-8")
                file_obj.close()
            except Exception:
                pass

        if not content:
            job.status = "failed"
            job.error_code = "SOURCE_NOT_FOUND"
            job.error_message = "No content to index"
            job.finished_at = datetime.now(timezone.utc)
            await db.flush()
            return _job_to_info(job)

        if doc.doc_type in ("markdown", "md"):
            parsed = markdown_parser.parse(type("Input", (), {"content": content, "file_name": doc.title})())
        else:
            parsed = plain_text_parser.parse(type("Input", (), {"content": content, "file_name": doc.title})())

        options = ChunkingOptions(
            chunk_size=job.chunk_size or settings.CHUNK_DEFAULT_SIZE,
            overlap=job.overlap_size or settings.CHUNK_DEFAULT_OVERLAP,
        )
        chunk_candidates = markdown_chunker.split(parsed.sections, options)

        old_chunks_result = await db.execute(
            select(KtDocumentChunk).where(KtDocumentChunk.document_id == doc.id)
        )
        for old_chunk in old_chunks_result.scalars().all():
            await db.delete(old_chunk)

        for candidate in chunk_candidates:
            emb = embedding_provider.embed(candidate.content)
            chunk = KtDocumentChunk(
                document_id=doc.id,
                workspace_id=doc.workspace_id,
                project_id=doc.project_id,
                chunk_index=candidate.chunk_index,
                content=candidate.content,
                content_hash=candidate.content_hash,
                token_count=candidate.token_count,
                heading_path=candidate.heading_path,
                source_start_line=candidate.start_line,
                source_end_line=candidate.end_line,
                embedding_model=embedding_provider.model_name(),
                embedding_provider=embedding_provider.provider_name(),
                embedding_dimension=embedding_provider.dimension(),
                embedding=json.dumps(emb.values),
            )
            db.add(chunk)

        doc.index_status = "indexed"
        doc.checksum = parsed.checksum
        job.status = "succeeded"
        job.chunk_count = len(chunk_candidates)
        job.finished_at = datetime.now(timezone.utc)
        await db.flush()

    except Exception as e:
        job.status = "failed"
        job.error_code = "INDEX_FAILED"
        job.error_message = str(e)
        job.finished_at = datetime.now(timezone.utc)
        await db.flush()

    return _job_to_info(job)


def _job_to_info(job: KtDocumentIndexJob) -> IndexJobInfo:
    return IndexJobInfo(
        id=job.id,
        document_id=job.document_id,
        status=job.status,
        chunk_count=job.chunk_count,
        error_code=job.error_code,
        error_message=job.error_message,
        started_at=job.started_at.isoformat() if job.started_at else None,
        finished_at=job.finished_at.isoformat() if job.finished_at else None,
    )
