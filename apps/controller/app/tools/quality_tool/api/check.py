from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional
from app.tools.quality_tool.services.quality_service import run_check, get_history

router = APIRouter(prefix="/api/check")


class CheckRequest(BaseModel):
    code: str
    checkType: str = "all"
    filename: Optional[str] = None
    language: Optional[str] = None
    userId: Optional[int] = None


@router.post("")
async def check_code(req: CheckRequest):
    return await run_check(
        code=req.code,
        check_type=req.checkType,
        filename=req.filename,
        language=req.language,
        user_id=req.userId,
    )


@router.get("/history")
async def history(userId: Optional[int] = Query(None), limit: int = Query(20)):
    return await get_history(user_id=userId, limit=limit)
