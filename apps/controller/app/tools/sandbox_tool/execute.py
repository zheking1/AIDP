from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional
from app.tools.sandbox_tool.tools.sandbox-tool.services.execution_service import execute_code, get_history

router = APIRouter(prefix="/api/execute")


class ExecuteRequest(BaseModel):
    code: str
    language: str = "python"
    stdin: Optional[str] = None
    userId: Optional[int] = None


@router.post("")
async def run_code(req: ExecuteRequest):
    return await execute_code(
        code=req.code,
        language=req.language,
        stdin=req.stdin,
        user_id=req.userId,
    )


@router.get("/history")
async def history(userId: Optional[int] = Query(None), limit: int = Query(20)):
    return await get_history(user_id=userId, limit=limit)
