from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.nas_storage_service import NASStorageService
from app.services.project_service import ProjectService
from app.services.permission_service import PermissionChecker
from app.db.auth_models import User

router = APIRouter(prefix="/api/projects", tags=["nas-storage"])


@router.get("/{project_id}/code-path")
async def get_code_path(request: Request, project_id: int, session: AsyncSession = Depends(get_db)):
    """获取项目代码路径"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    permission_checker = PermissionChecker(session, User(id=user_id))
    if not await permission_checker.can_view_project(user_id, project_id):
        raise HTTPException(status_code=403, detail="Permission denied")

    nas_service = NASStorageService()
    path = nas_service.get_project_path(project_id)
    exists = nas_service.project_exists(project_id)

    return JSONResponse(content={
        "path": path,
        "exists": exists
    })


@router.post("/{project_id}/sync-code")
async def sync_code(request: Request, project_id: int, session: AsyncSession = Depends(get_db)):
    """Sync project code to NAS"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    permission_checker = PermissionChecker(session, User(id=user_id))
    if not await permission_checker.can_manage_project(user_id, project_id):
        raise HTTPException(status_code=403, detail="Permission denied")

    body = await request.json()
    source = body.get("source")
    branch = body.get("branch", "main")

    if not source:
        raise HTTPException(status_code=400, detail="Source URL is required")

    nas_service = NASStorageService()
    path = nas_service.sync_code_from_git(project_id, source, branch)

    return JSONResponse(content={
        "success": True,
        "path": path
    })


@router.get("/{project_id}/files")
async def list_files(request: Request, project_id: int, path: str = "", session: AsyncSession = Depends(get_db)):
    """列出项目文件"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    permission_checker = PermissionChecker(session, User(id=user_id))
    if not await permission_checker.can_view_project(user_id, project_id):
        raise HTTPException(status_code=403, detail="Permission denied")

    nas_service = NASStorageService()
    files = nas_service.list_project_files(project_id, path)

    return JSONResponse(content={
        "files": files
    })


@router.get("/{project_id}/files/{file_path:path}")
async def read_file(request: Request, project_id: int, file_path: str, session: AsyncSession = Depends(get_db)):
    """读取项目文件"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    permission_checker = PermissionChecker(session, User(id=user_id))
    if not await permission_checker.can_view_project(user_id, project_id):
        raise HTTPException(status_code=403, detail="Permission denied")

    nas_service = NASStorageService()
    content = nas_service.read_file(project_id, file_path)

    if content is None:
        raise HTTPException(status_code=404, detail="File not found")

    return JSONResponse(content={
        "file_path": file_path,
        "content": content
    })


@router.post("/{project_id}/files/{file_path:path}")
async def write_file(request: Request, project_id: int, file_path: str, session: AsyncSession = Depends(get_db)):
    """写入项目文件"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    permission_checker = PermissionChecker(session, User(id=user_id))
    if not await permission_checker.can_manage_project(user_id, project_id):
        raise HTTPException(status_code=403, detail="Permission denied")

    body = await request.json()
    content = body.get("content")

    if content is None:
        raise HTTPException(status_code=400, detail="Content is required")

    nas_service = NASStorageService()
    nas_service.write_file(project_id, file_path, content)

    return JSONResponse(content={
        "success": True,
        "file_path": file_path
    })
