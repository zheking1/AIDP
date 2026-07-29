from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.knowledge_tool.tools.knowledge-tool.db.database import get_db
from app.tools.knowledge_tool.tools.knowledge-tool.schemas.search import SearchRequest, SearchResult
from app.tools.knowledge_tool.tools.knowledge-tool.services.search_service import SearchService
from app.tools.knowledge_tool.tools.knowledge-tool.schemas.common import ApiResponse

router = APIRouter(prefix="/api/knowledge", tags=["search"])


@router.post("/search", response_model=ApiResponse)
async def search_knowledge(req: SearchRequest, db: AsyncSession = Depends(get_db)):
    svc = SearchService(db)
    result = await svc.search(
        query=req.query,
        workspace_id=req.workspace_id,
        project_id=req.project_id,
        knowledge_base_ids=req.knowledge_base_ids,
        task_domains=req.task_domains,
        top_k=req.top_k,
        min_score=req.min_score,
    )
    return ApiResponse(data=result)


@router.post("/search/semantic", response_model=ApiResponse)
async def semantic_search_knowledge(req: SearchRequest, db: AsyncSession = Depends(get_db)):
    svc = SearchService(db)
    search_mode = req.search_mode or "hybrid"
    result = await svc.semantic_search(
        query=req.query,
        workspace_id=req.workspace_id,
        project_id=req.project_id,
        knowledge_base_ids=req.knowledge_base_ids,
        task_domains=req.task_domains,
        top_k=req.top_k,
        search_mode=search_mode,
    )
    return ApiResponse(data=result)