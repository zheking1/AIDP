from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.search import SearchRequest
from app.services import search_service
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/api/knowledge", tags=["search"])


@router.post("/search", response_model=ApiResponse)
async def search_knowledge(req: SearchRequest, db: AsyncSession = Depends(get_db)):
    result = await search_service.search(db, req)
    return ApiResponse(data=result.model_dump())
