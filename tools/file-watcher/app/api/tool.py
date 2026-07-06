from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/tool/capabilities")
async def get_capabilities():
    return JSONResponse(content={
        "tool": "file-watcher",
        "version": "0.1.0",
        "capabilities": [
            {
                "name": "watcher.add_project",
                "description": "Add a project to watch for file changes",
                "parameters": {
                    "project_name": {"type": "string", "required": True},
                    "local_path": {"type": "string", "required": True},
                    "code_index_project_id": {"type": "integer", "required": True},
                    "ignored_dirs": {"type": "array", "required": False},
                    "ignored_patterns": {"type": "array", "required": False},
                },
            },
            {
                "name": "watcher.list_projects",
                "description": "List all watched projects",
                "parameters": {},
            },
            {
                "name": "watcher.remove_project",
                "description": "Remove a project from watching",
                "parameters": {
                    "project_id": {"type": "integer", "required": True},
                },
            },
            {
                "name": "watcher.rescan",
                "description": "Rescan a project directory and rebuild index",
                "parameters": {
                    "project_id": {"type": "integer", "required": True},
                },
            },
            {
                "name": "watcher.get_events",
                "description": "Get recent watch events for a project",
                "parameters": {
                    "project_id": {"type": "integer", "required": True},
                    "limit": {"type": "integer", "required": False, "default": 100},
                },
            },
            {
                "name": "watcher.stats",
                "description": "Get watcher statistics",
                "parameters": {},
            },
        ],
    })


@router.post("/tool/invoke")
async def invoke_tool(request: Request):
    body = await request.json()
    capability = body.get("capability")
    args = body.get("arguments", {})

    if capability == "watcher.add_project":
        from app.services.project_mapper import ProjectMapper
        from app.db.database import async_session
        from app.services.watcher import watcher_service
        async with async_session() as db:
            mapper = ProjectMapper(db)
            project = await mapper.add_project(
                project_name=args["project_name"],
                local_path=args["local_path"],
                code_index_project_id=args["code_index_project_id"],
                ignored_dirs=args.get("ignored_dirs", []),
                ignored_patterns=args.get("ignored_patterns", []),
            )
            await watcher_service.add_watched_project(project)
            return JSONResponse(content={"id": project.id, "status": "watching"})

    elif capability == "watcher.list_projects":
        from app.services.project_mapper import ProjectMapper
        from app.db.database import async_session
        async with async_session() as db:
            mapper = ProjectMapper(db)
            projects = await mapper.list_active_projects()
            return JSONResponse(content={
                "projects": [{"id": p.id, "name": p.project_name, "path": p.local_path} for p in projects]
            })

    elif capability == "watcher.remove_project":
        from app.services.watcher import watcher_service
        from app.services.project_mapper import ProjectMapper
        from app.db.database import async_session
        async with async_session() as db:
            await watcher_service.remove_watched_project(args["project_id"])
            mapper = ProjectMapper(db)
            await mapper.delete_project(args["project_id"])
            return JSONResponse(content={"status": "deleted"})

    elif capability == "watcher.rescan":
        from app.services.watcher import watcher_service
        from app.services.project_mapper import ProjectMapper
        from app.db.database import async_session
        async with async_session() as db:
            mapper = ProjectMapper(db)
            project = await mapper.get_project_by_id(args["project_id"])
            if not project:
                return JSONResponse(status_code=404, content={"error": "Project not found"})
            result = await watcher_service.rescan_project(project)
            return JSONResponse(content=result)

    elif capability == "watcher.get_events":
        from app.db.database import async_session
        from app.db.models import WatchEvent
        from sqlalchemy import select
        async with async_session() as db:
            query = (
                select(WatchEvent)
                .where(WatchEvent.project_id == args["project_id"])
                .order_by(WatchEvent.created_at.desc())
                .limit(args.get("limit", 100))
            )
            result = await db.execute(query)
            events = result.scalars().all()
            return JSONResponse(content={
                "events": [{"type": e.event_type, "file": e.file_path, "time": e.created_at.isoformat()} for e in events]
            })

    elif capability == "watcher.stats":
        from app.services.project_mapper import ProjectMapper
        from app.db.database import async_session
        async with async_session() as db:
            mapper = ProjectMapper(db)
            projects = await mapper.list_active_projects()
            return JSONResponse(content={"active_projects": len(projects)})

    return JSONResponse(status_code=400, content={"error": f"Unknown capability: {capability}"})
