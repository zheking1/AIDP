from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.document import DocumentCreateRequest, IndexJobRequest
from app.services import document_service, indexing_service
from app.services.knowledge_graph import KnowledgeGraph, CodeLinker, DriftDetector
from app.services.search_service import FTS5SearchService, SemanticSearchService
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("", response_model=ApiResponse)
async def create_document(req: DocumentCreateRequest, db: AsyncSession = Depends(get_db)):
    doc = await document_service.create_document(db, req)
    return ApiResponse(data=doc.model_dump())


@router.get("", response_model=ApiResponse)
async def list_documents(
    workspace_id: str,
    project_id: str = None,
    doc_type: str = None,
    owner_type: str = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    docs = await document_service.list_documents(
        db, workspace_id=workspace_id, project_id=project_id,
        doc_type=doc_type, page=page, page_size=page_size,
        owner_type=owner_type,
    )
    return ApiResponse(data=[d.model_dump() for d in docs])


@router.get("/{document_id}", response_model=ApiResponse)
async def get_document(document_id: str, workspace_id: str, db: AsyncSession = Depends(get_db)):
    doc = await document_service.get_document(db, document_id, workspace_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return ApiResponse(data=doc.model_dump())


@router.delete("/{document_id}", response_model=ApiResponse)
async def delete_document(document_id: str, workspace_id: str, db: AsyncSession = Depends(get_db)):
    ok = await document_service.delete_document(db, document_id, workspace_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Document not found")
    return ApiResponse(message="Document deleted")


@router.post("/{document_id}/index", response_model=ApiResponse)
async def index_document(
    document_id: str,
    req: IndexJobRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        job = await indexing_service.create_index_job(
            db,
            document_id=document_id,
            workspace_id=req.workspace_id,
            project_id=req.project_id,
            chunk_size=req.chunk_size,
            overlap=req.overlap,
            embedding_model=req.embedding_model,
            force=req.force,
        )
        result = await indexing_service.run_index_job(db, job.id)
        return ApiResponse(data=result.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{document_id}/graph")
async def get_doc_graph(document_id: str, workspace_id: str, db: AsyncSession = Depends(get_db)):
    graph = KnowledgeGraph(db)
    docs = await document_service.list_documents(db, workspace_id=workspace_id)
    relevance = await graph.compute_relevance(int(document_id), int(document_id))
    return ApiResponse(data={"document_id": document_id, "relevance": relevance, "communities": []})


@router.post("/{document_id}/link")
async def link_code(document_id: str, workspace_id: str, request: dict, db: AsyncSession = Depends(get_db)):
    body = request if isinstance(request, dict) else await request.json()
    code_refs = body.get("code_refs", [])
    linker = CodeLinker(db)
    links = await linker.link_document_to_code(int(document_id), code_refs)
    return ApiResponse(data={"links": links})


@router.get("/{document_id}/drift")
async def check_drift(document_id: str, workspace_id: str, db: AsyncSession = Depends(get_db)):
    detector = DriftDetector(db)
    drifts = await detector.detect_drift(int(document_id))
    return ApiResponse(data={"drifts": drifts})


@router.get("/search/fts")
async def fts_search(workspace_id: str, q: str, limit: int = 20, db: AsyncSession = Depends(get_db)):
    svc = FTS5SearchService(db)
    results = await svc.search(q, workspace_id, limit)
    return ApiResponse(data=results)


@router.get("/search/semantic")
async def semantic_search(workspace_id: str, q: str, limit: int = 10, db: AsyncSession = Depends(get_db)):
    svc = SemanticSearchService(db)
    results = await svc.search(q, workspace_id, limit)
    return ApiResponse(data=results)
