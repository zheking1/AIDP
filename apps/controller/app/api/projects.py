from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.project_service import ProjectService
from app.services.permission_service import PermissionChecker
from app.db.auth_models import User

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("/")
async def create_project(request: Request, session: AsyncSession = Depends(get_db)):
    """创建项目"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    body = await request.json()
    name = body.get("name")
    description = body.get("description", "")
    project_type = body.get("type", "")

    if not name:
        raise HTTPException(status_code=400, detail="Project name is required")

    project_service = ProjectService(session)
    project = await project_service.create_project(name, description, project_type, str(user_id))

    return JSONResponse(content={
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "type": project.project_type,
        "owner_id": project.owner_id
    })


@router.get("/")
async def get_projects(request: Request, session: AsyncSession = Depends(get_db)):
    """获取项目列表"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    project_service = ProjectService(session)
    projects = await project_service.get_projects(user_id)

    return JSONResponse(content={
        "projects": [{
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "type": p.project_type,
            "owner_id": p.owner_id
        } for p in projects]
    })


@router.get("/{project_id}")
async def get_project(request: Request, project_id: int, session: AsyncSession = Depends(get_db)):
    """获取项目详情"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    project_service = ProjectService(session)
    project = await project_service.get_project(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return JSONResponse(content={
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "type": project.project_type,
        "owner_id": project.owner_id
    })


@router.put("/{project_id}")
async def update_project(request: Request, project_id: int, session: AsyncSession = Depends(get_db)):
    """更新项目"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    permission_checker = PermissionChecker(session, User(id=user_id))
    if not await permission_checker.can_manage_project(user_id, project_id):
        raise HTTPException(status_code=403, detail="Permission denied")

    body = await request.json()
    project_service = ProjectService(session)
    project = await project_service.update_project(
        project_id,
        name=body.get("name"),
        description=body.get("description"),
        project_type=body.get("type")
    )

    return JSONResponse(content={
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "type": project.project_type,
        "owner_id": project.owner_id
    })


@router.delete("/{project_id}")
async def delete_project(request: Request, project_id: int, session: AsyncSession = Depends(get_db)):
    """删除项目"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    permission_checker = PermissionChecker(session, User(id=user_id))
    if not await permission_checker.can_manage_project(user_id, project_id):
        raise HTTPException(status_code=403, detail="Permission denied")

    project_service = ProjectService(session)
    await project_service.delete_project(project_id)

    return JSONResponse(content={"message": "Project deleted successfully"})


@router.get("/{project_id}/members")
async def get_project_members(request: Request, project_id: int, session: AsyncSession = Depends(get_db)):
    """获取项目成员"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    permission_checker = PermissionChecker(session, User(id=user_id))
    if not await permission_checker.can_view_project(user_id, project_id):
        raise HTTPException(status_code=403, detail="Permission denied")

    project_service = ProjectService(session)
    members = await project_service.get_members(project_id)

    return JSONResponse(content={
        "members": [{
            "id": m.id,
            "project_id": m.project_id,
            "user_id": m.user_id,
            "role": m.role
        } for m in members]
    })


@router.post("/{project_id}/members")
async def add_project_member(request: Request, project_id: int, session: AsyncSession = Depends(get_db)):
    """添加项目成员"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    permission_checker = PermissionChecker(session, User(id=user_id))
    if not await permission_checker.can_manage_project(user_id, project_id):
        raise HTTPException(status_code=403, detail="Permission denied")

    body = await request.json()
    member_user_id = body.get("user_id")
    role = body.get("role", "member")

    if not member_user_id:
        raise HTTPException(status_code=400, detail="User ID is required")

    project_service = ProjectService(session)
    member = await project_service.add_member(project_id, member_user_id, role)

    return JSONResponse(content={
        "id": member.id,
        "project_id": member.project_id,
        "user_id": member.user_id,
        "role": member.role
    })


@router.delete("/{project_id}/members/{user_id}")
async def remove_project_member(request: Request, project_id: int, user_id: int, session: AsyncSession = Depends(get_db)):
    """移除项目成员"""
    session_user_id = request.session.get("user_id")
    if not session_user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    permission_checker = PermissionChecker(session, User(id=session_user_id))
    if not await permission_checker.can_manage_project(session_user_id, project_id):
        raise HTTPException(status_code=403, detail="Permission denied")

    project_service = ProjectService(session)
    await project_service.remove_member(project_id, user_id)

    return JSONResponse(content={"message": "Member removed successfully"})
