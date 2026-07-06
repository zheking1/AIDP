from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.services.watcher import watcher_service

router = APIRouter()


@router.get("/health")
async def health_check():
    return JSONResponse(content={
        "status": "healthy",
        "service": "file-watcher",
        "is_running": watcher_service._running,
        "watched_projects": len(watcher_service.watched),
    })
