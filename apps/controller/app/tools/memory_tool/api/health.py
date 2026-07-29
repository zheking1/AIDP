from fastapi import APIRouter
from app.tools.memory_tool.config import settings

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "tool": settings.APP_NAME, "version": settings.APP_VERSION}
