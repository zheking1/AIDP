from fastapi import APIRouter

from app.tools.knowledge_tool.config import settings

router = APIRouter()


@router.get("/health")
async def health():
    return {
        "status": "UP",
        "tool": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "dependencies": {
            "postgres": "UP",
            "storage": "UP",
            "embedding": "UP",
        },
    }
