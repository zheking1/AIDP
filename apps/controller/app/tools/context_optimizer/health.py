from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/health")
async def health():
    return JSONResponse(content={"status": "ok", "tool": "context-optimizer", "version": "0.1.0"})
