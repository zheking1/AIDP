from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.indexer import Indexer
from app.services.search_service import SearchService
from app.services.code_explore import CodeExploreService
from app.services.scanner import Scanner
from app.services.incremental_indexer import IncrementalIndexer
from app.services.lsp_client import LSPClient

router = APIRouter()


@router.post("/api/projects")
async def create_project(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    name = body.get("name", "")
    path = body.get("path", "")
    if not name or not path:
        raise HTTPException(status_code=400, detail="name and path are required")
    indexer = Indexer(db)
    project = await indexer.create_project(name, path)
    return JSONResponse(content={"id": project.id, "name": project.name, "path": project.path})


@router.post("/api/projects/{project_id}/scan")
async def scan_project(request: Request, project_id: int, db: AsyncSession = Depends(get_db)):
    indexer = Indexer(db)
    result = await indexer.scan_and_index(project_id, f"/tmp/project_{project_id}")
    return JSONResponse(content=result)


@router.get("/api/projects")
async def list_projects(db: AsyncSession = Depends(get_db)):
    svc = SearchService(db)
    projects = await svc.list_projects()
    return JSONResponse(content={"projects": projects})


@router.post("/api/explore")
async def explore(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    project_id = body.get("project_id")
    action = body.get("action", "summary")
    params = body.get("params", {})
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id is required")
    svc = CodeExploreService(db)
    result = await svc.explore(project_id, action, params)
    return JSONResponse(content=result)


@router.get("/api/search")
async def search(project_id: int, q: str = "", type: str = None, limit: int = 50, db: AsyncSession = Depends(get_db)):
    svc = SearchService(db)
    symbols = await svc.search_symbols(project_id, q, type, limit)
    return JSONResponse(content={"symbols": symbols, "total": len(symbols)})


@router.post("/api/index/file")
async def index_file(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    project_id = body.get("project_id")
    file_path = body.get("file_path")
    if not project_id or not file_path:
        raise HTTPException(status_code=400, detail="project_id and file_path required")
    indexer = IncrementalIndexer(db)
    return JSONResponse(await indexer.index_file(project_id, file_path))


@router.post("/api/index/directory")
async def index_directory(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    project_id = body.get("project_id")
    dir_path = body.get("dir_path")
    if not project_id or not dir_path:
        raise HTTPException(status_code=400, detail="project_id and dir_path required")
    indexer = IncrementalIndexer(db)
    return JSONResponse(await indexer.index_directory(project_id, dir_path))


@router.get("/api/lsp/references")
async def lsp_references(project_id: int, symbol: str, file: str = None, kind: str = None, db: AsyncSession = Depends(get_db)):
    client = LSPClient(db)
    refs = await client.find_references(project_id, symbol, file, kind)
    return JSONResponse({"references": refs})


@router.get("/api/lsp/implementation")
async def lsp_implementation(project_id: int, interface: str, db: AsyncSession = Depends(get_db)):
    client = LSPClient(db)
    impls = await client.find_implementation(project_id, interface)
    return JSONResponse({"implementations": impls})


@router.get("/api/lsp/hover")
async def lsp_hover(project_id: int, file: str, line: int, db: AsyncSession = Depends(get_db)):
    client = LSPClient(db)
    hover = await client.hover(project_id, file, line)
    return JSONResponse({"hover": hover})
