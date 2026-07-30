from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.tools.doc_index.db.database import get_db
from app.tools.doc_index.services.parser import DocParser
from app.tools.doc_index.services.search_service import SearchService
from app.tools.doc_index.services.linker import CodeLinker
from app.tools.doc_index.services.drift_detector import DriftDetector
from app.tools.doc_index.services.wiki_generator import WikiGenerator

router = APIRouter()


@router.post("/api/docs")
async def create_doc(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    title = body.get("title", "")
    content = body.get("content", "")
    url = body.get("url")  # allow None for non-unique constraint
    source = body.get("source", "manual")
    language = body.get("language")
    framework = body.get("framework")
    category = body.get("category")
    level = body.get("level")
    tags = body.get("tags", [])
    if not title or not content:
        raise HTTPException(status_code=400, detail="title and content are required")

    parser = DocParser()
    parsed = parser.parse_markdown(content, url)

    from app.tools.doc_index.db.models import DocPage
    from sqlalchemy import text
    doc = DocPage(
        title=parsed["title"] or title,
        url=url or None,
        content=content,
        summary=parsed["summary"],
        word_count=parsed["word_count"],
        source=source,
        language=language or None,
        framework=framework or None,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    return JSONResponse(content={
        "id": doc.id,
        "title": doc.title,
        "url": doc.url,
        "language": doc.language,
        "framework": doc.framework,
        "word_count": doc.word_count,
    })


@router.get("/api/docs")
async def list_docs(db: AsyncSession = Depends(get_db)):
    svc = SearchService(db)
    docs = await svc.get_all_pages()
    return JSONResponse(content={"docs": docs})


@router.get("/api/docs/{doc_id}")
async def get_doc(doc_id: int, db: AsyncSession = Depends(get_db)):
    svc = SearchService(db)
    doc = await svc.get_page(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return JSONResponse(content=doc)


@router.post("/api/docs/{doc_id}/link")
async def link_code(doc_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    code_nodes = body.get("code_nodes", [])
    if not code_nodes:
        raise HTTPException(status_code=400, detail="code_nodes required")
    linker = CodeLinker(db)
    links = await linker.link_document_to_code(doc_id, code_nodes)
    return JSONResponse(content={"linked": len(links)})


@router.get("/api/docs/{doc_id}/links")
async def get_links(doc_id: int, db: AsyncSession = Depends(get_db)):
    linker = CodeLinker(db)
    links = await linker.get_code_links(doc_id)
    return JSONResponse(content={
        "links": [{"node_type": l.node_type, "node_name": l.node_name,
                    "file_path": l.file_path, "line_start": l.line_start} for l in links]
    })


@router.post("/api/docs/{doc_id}/drift")
async def detect_drift(doc_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    code_changes = body.get("changes", [])
    detector = DriftDetector(db)
    drifts = await detector.detect_drift(doc_id, code_changes)
    return JSONResponse(content={"drifts_detected": len(drifts)})


@router.get("/api/docs/{doc_id}/drifts")
async def get_drifts(doc_id: int, db: AsyncSession = Depends(get_db)):
    detector = DriftDetector(db)
    drifts = await detector.get_drifts(doc_id)
    return JSONResponse(content={
        "drifts": [{"section": d.section_heading, "score": d.drift_score,
                     "status": d.status} for d in drifts]
    })


@router.get("/api/wiki")
async def generate_wiki(language: str = None, framework: str = None, db: AsyncSession = Depends(get_db)):
    generator = WikiGenerator(db)
    wiki = await generator.generate_wiki(language, framework)
    return JSONResponse(content=wiki)
