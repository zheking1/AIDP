from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional
from app.db.database import get_db
from app.db.models import WatchedProject, WatchEvent
from app.services.project_mapper import ProjectMapper
from app.services.watcher import watcher_service

router = APIRouter()


class AddProjectRequest(BaseModel):
    project_name: str
    local_path: str
    code_index_project_id: int
    ignored_dirs: Optional[List[str]] = []
    ignored_patterns: Optional[List[str]] = []


class UpdateProjectRequest(BaseModel):
    ignored_dirs: Optional[List[str]] = None
    ignored_patterns: Optional[List[str]] = None
    is_active: Optional[bool] = None


@router.post("/api/watcher/projects")
async def add_project(request: AddProjectRequest, db: AsyncSession = Depends(get_db)):
    mapper = ProjectMapper(db)
    existing = await mapper.get_project_by_name(request.project_name)
    if existing:
        raise HTTPException(status_code=409, detail="Project already exists")

    project = await mapper.add_project(
        project_name=request.project_name,
        local_path=request.local_path,
        code_index_project_id=request.code_index_project_id,
        ignored_dirs=request.ignored_dirs,
        ignored_patterns=request.ignored_patterns,
    )

    await watcher_service.add_watched_project(project)
    return JSONResponse(content={"id": project.id, "project_name": project.project_name, "status": "watching"})


@router.get("/api/watcher/projects")
async def list_projects(db: AsyncSession = Depends(get_db)):
    mapper = ProjectMapper(db)
    projects = await mapper.list_active_projects()
    return JSONResponse(content={
        "projects": [
            {
                "id": p.id,
                "project_name": p.project_name,
                "local_path": p.local_path,
                "code_index_project_id": p.code_index_project_id,
                "is_active": p.is_active,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in projects
        ]
    })


@router.get("/api/watcher/projects/{project_id}")
async def get_project(project_id: int, db: AsyncSession = Depends(get_db)):
    mapper = ProjectMapper(db)
    project = await mapper.get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return JSONResponse(content={
        "id": project.id,
        "project_name": project.project_name,
        "local_path": project.local_path,
        "code_index_project_id": project.code_index_project_id,
        "is_active": project.is_active,
        "ignored_dirs": project.ignored_dirs,
        "ignored_patterns": project.ignored_patterns,
    })


@router.patch("/api/watcher/projects/{project_id}")
async def update_project(project_id: int, request: UpdateProjectRequest, db: AsyncSession = Depends(get_db)):
    mapper = ProjectMapper(db)
    project = await mapper.get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if request.ignored_dirs is not None:
        project.ignored_dirs = request.ignored_dirs
    if request.ignored_patterns is not None:
        project.ignored_patterns = request.ignored_patterns
    if request.is_active is not None:
        project.is_active = request.is_active
        if request.is_active:
            await watcher_service.add_watched_project(project)
        else:
            await watcher_service.remove_watched_project(project_id)

    await db.commit()
    return JSONResponse(content={"status": "updated"})


@router.delete("/api/watcher/projects/{project_id}")
async def delete_project(project_id: int, db: AsyncSession = Depends(get_db)):
    await watcher_service.remove_watched_project(project_id)
    mapper = ProjectMapper(db)
    deleted = await mapper.delete_project(project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found")
    return JSONResponse(content={"status": "deleted"})


@router.post("/api/watcher/projects/{project_id}/rescan")
async def rescan_project(project_id: int, db: AsyncSession = Depends(get_db)):
    mapper = ProjectMapper(db)
    project = await mapper.get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    result = await watcher_service.rescan_project(project)
    return JSONResponse(content=result)


@router.get("/api/watcher/projects/{project_id}/events")
async def get_events(
    project_id: int,
    limit: int = 100,
    processed: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(WatchEvent).where(WatchEvent.project_id == project_id)
    if processed is not None:
        query = query.where(WatchEvent.processed == processed)
    query = query.order_by(WatchEvent.created_at.desc()).limit(limit)

    result = await db.execute(query)
    events = result.scalars().all()
    return JSONResponse(content={
        "events": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "file_path": e.file_path,
                "processed": e.processed,
                "error_message": e.error_message,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ]
    })


@router.get("/api/watcher/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    mapper = ProjectMapper(db)
    projects = await mapper.list_active_projects()

    total_events = 0
    pending_events = 0
    error_events = 0

    for p in projects:
        result = await db.execute(
            select(WatchEvent).where(WatchEvent.project_id == p.id)
        )
        events = result.scalars().all()
        total_events += len(events)
        pending_events += sum(1 for e in events if not e.processed)
        error_events += sum(1 for e in events if e.error_message)

    return JSONResponse(content={
        "active_projects": len(projects),
        "total_events": total_events,
        "pending_events": pending_events,
        "error_events": error_events,
    })
