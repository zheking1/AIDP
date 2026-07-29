from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.tools.knowledge_tool.db.database import get_db
from app.tools.knowledge_tool.services.two_step_ingest import TwoStepIngestEngine, LLMClient
from app.tools.knowledge_tool.schemas.document import DocumentCreateRequest
from app.tools.knowledge_tool.schemas.common import ApiResponse

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/ingest", response_model=ApiResponse)
async def ingest_document(req: DocumentCreateRequest, db: AsyncSession = Depends(get_db)):
    engine = TwoStepIngestEngine(db)
    result = await engine.ingest(
        title=req.title,
        content=req.content or "",
        workspace_id=req.workspace_id,
        project_id=req.project_id,
        doc_type=req.doc_type,
    )
    return ApiResponse(data=result)
