from fastapi import APIRouter
from app.config import settings

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "UP", "service": "AIDP Controller", "version": settings.APP_VERSION}
