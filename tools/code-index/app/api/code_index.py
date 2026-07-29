from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.db.models import Node, Edge
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
    from sqlalchemy import select
    from app.db.models import Project
    result = await db.execute(select(Project).where(Project.id == project_id))
    proj = result.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    indexer = Indexer(db)
    result = await indexer.scan_and_index(project_id, proj.path)
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


@router.get("/api/search/typed")
async def search_typed(
    project_id: int,
    node_type: str = None,
    return_type: str = None,
    param_type: str = None,
    access_modifier: str = None,
    q: str = "",
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import and_, or_
    conditions = [Node.project_id == project_id]
    if node_type:
        conditions.append(Node.node_type == node_type)
    if return_type:
        conditions.append(Node.return_type.ilike(f"%{return_type}%"))
    if param_type and Node.params_json.isnot(None):
        conditions.append(Node.params_json.ilike(f"%{param_type}%"))
    if q:
        conditions.append(Node.name.ilike(f"%{q}%"))
    result = await db.execute(select(Node).where(*conditions).limit(limit))
    nodes = result.scalars().all()
    return JSONResponse(content={
        "symbols": [{
            "id": n.id, "node_type": n.node_type, "name": n.name,
            "qualified_name": n.qualified_name, "file_path": n.file_path,
            "line_start": n.line_start, "language": n.language,
            "signature": n.signature,
            "return_type": n.return_type,
            "params": n.params_json,
            "docstring": n.docstring,
        } for n in nodes],
        "total": len(nodes),
        "filters_applied": {"node_type": node_type, "return_type": return_type, "param_type": param_type, "query": q},
    })


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


@router.post("/api/index/file-content")
async def index_file_content(request: Request, db: AsyncSession = Depends(get_db)):
    """Index a file from uploaded content (for files not on NAS)."""
    body = await request.json()
    project_id = body.get("project_id")
    file_path = body.get("file_path", "")
    content = body.get("content", "")
    language = body.get("language", "python")

    if not project_id or not file_path or not content:
        raise HTTPException(status_code=400, detail="project_id, file_path, content required")

    import hashlib, os, re
    from app.db.models import Node, Edge

    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    lang = language or "unknown"

    file_node = Node(
        project_id=project_id, node_type="file",
        name=os.path.basename(file_path), qualified_name=file_path,
        file_path=file_path, language=lang, checksum=checksum,
    )
    db.add(file_node)
    await db.flush()

    # Extract classes and functions
    classes, functions = [], []
    if lang == "python":
        classes = [{"name": m.group(1), "line": content[:m.start()].count(chr(10)) + 1}
                   for m in re.finditer(r'^\s*class\s+(\w+)', content, re.MULTILINE)]
        functions = [{"name": m.group(1), "line": content[:m.start()].count(chr(10)) + 1}
                     for m in re.finditer(r'^\s*def\s+(\w+)', content, re.MULTILINE) if not m.group(1).startswith("_")]
    elif lang in ("typescript", "javascript"):
        classes = [{"name": m.group(1), "line": content[:m.start()].count(chr(10)) + 1}
                   for m in re.finditer(r'class\s+(\w+)', content)]
        functions = [{"name": m.group(1), "line": content[:m.start()].count(chr(10)) + 1}
                     for m in re.finditer(r'(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s+)?\()', content) if m.group(1) or m.group(2)]

    for cls in classes:
        node = Node(project_id=project_id, node_type="class", name=cls["name"],
                    qualified_name=f"{file_path}::{cls['name']}", file_path=file_path,
                    line_start=cls["line"], language=lang)
        db.add(node)
        await db.flush()
        db.add(Edge(project_id=project_id, source_id=file_node.id, target_id=node.id, edge_type="contains"))

    func_ids = {}
    for fn in functions:
        name = fn.get("name") or fn.get("group", "unknown")
        node = Node(project_id=project_id, node_type="function", name=name,
                    qualified_name=f"{file_path}::{name}", file_path=file_path,
                    line_start=fn["line"], language=lang)
        db.add(node)
        await db.flush()
        func_ids[name] = node.id
        db.add(Edge(project_id=project_id, source_id=file_node.id, target_id=node.id, edge_type="contains"))

    for imp in re.findall(r'(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))', content):
        mod = imp[0] or imp[1]
        db.add(Edge(project_id=project_id, source_id=file_node.id, target_id=0, edge_type="imports", metadata_={"import_name": mod}))

    if len(func_ids) > 1:
        for match in re.finditer(r'(\w+)\s*\(', content):
            call_name = match.group(1)
            if call_name in func_ids:
                for caller, cid in func_ids.items():
                    if caller != call_name:
                        db.add(Edge(project_id=project_id, source_id=cid, target_id=func_ids[call_name], edge_type="calls"))

    await db.commit()
    nodes = 1 + len(classes) + len(functions)
    edges = len(classes) + len(functions) + len(list(re.finditer(r'(?:from\s+[\w.]+\s+import|import\s+[\w.]+)', content)))
    return JSONResponse(content={"file": file_path, "nodes": nodes, "edges": edges, "language": lang})


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
