from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.event_collector import EventCollector
from app.services.pattern_analyzer import PatternAnalyzer
from app.services.llm_pattern_analyzer import LLMPatternAnalyzer
from app.services.evolution_router import EvolutionRouter
from app.services.tool_updater import ToolUpdater
from app.services.stats_analyzer import StatsAnalyzer
from app.services.batch_processor import BatchProcessor

router = APIRouter()


@router.post("/api/events")
async def collect_event(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    event_type = body.get("type", "error")
    source = body.get("source", "unknown")
    content = body.get("content", "")
    result = body.get("result")
    metadata = body.get("metadata", {})

    collector = EventCollector(db)
    event = await collector.collect(event_type, source, content, result, metadata)

    analyzer = LLMPatternAnalyzer(db)
    analysis = await analyzer.analyze(event_type, content, result, metadata)
    saved = await analyzer.save_analysis(event.id, analysis)

    router_inst = EvolutionRouter()
    targets = router_inst.route(analysis)

    updater = ToolUpdater(db)
    updates = await updater.apply_evolution(saved.id, targets, analysis.get("update_type", "经验"))

    await collector.mark_processed(event.id)

    return JSONResponse(content={
        "success": True,
        "event_id": event.id,
        "analysis": analysis,
        "targets": targets,
    })


@router.post("/api/events/batch")
async def collect_batch(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    processor = BatchProcessor(db)
    result = await processor.process_batch(body.get("events", []))
    return JSONResponse(content=result)


@router.post("/api/analyze/{event_id}")
async def analyze_event(event_id: int, db: AsyncSession = Depends(get_db)):
    collector = EventCollector(db)
    event = await collector.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    analyzer = LLMPatternAnalyzer(db)
    analysis = await analyzer.analyze(event.event_type, event.content or "", event.result, event.metadata_)
    saved = await analyzer.save_analysis(event.id, analysis)

    router_inst = EvolutionRouter()
    targets = router_inst.route(analysis)

    updater = ToolUpdater(db)
    updates = await updater.apply_evolution(saved.id, targets, analysis.get("update_type", "经验"))

    return JSONResponse(content={
        "analysis": analysis,
        "targets": targets,
    })


@router.get("/api/evolution/history")
async def get_history(db: AsyncSession = Depends(get_db)):
    analyzer = PatternAnalyzer(db)
    analyses = await analyzer.get_analyses()
    return JSONResponse(content={
        "history": [{
            "id": a.id,
            "event_id": a.event_id,
            "category": a.category,
            "error_type": a.error_type,
            "fix_pattern": a.fix_pattern,
            "success_pattern": a.success_pattern,
            "affected_tools": a.affected_tools,
            "priority": a.priority,
            "confidence": a.confidence,
        } for a in analyses[:50]],
    })


@router.get("/api/evolution/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    stats = StatsAnalyzer(db)
    result = await stats.get_stats()
    return JSONResponse(content=result)
