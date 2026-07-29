from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.tools.context_optimizer.tools.context-optimizer.db.database import get_db
from app.tools.context_optimizer.tools.context-optimizer.services.requirement_analyzer import RequirementAnalyzer
from app.tools.context_optimizer.tools.context-optimizer.services.budget_allocator import BudgetAllocator
from app.tools.context_optimizer.tools.context-optimizer.services.result_refiner import ResultRefiner
from app.tools.context_optimizer.tools.context-optimizer.services.context_tracker import ContextTracker
from app.tools.context_optimizer.tools.context-optimizer.services.cache_service import CacheService
from app.tools.context_optimizer.tools.context-optimizer.services.adaptive_budget import AdaptiveBudgetAllocator
from app.tools.context_optimizer.tools.context-optimizer.services.llm_client import LLMClient
from app.tools.context_optimizer.tools.context-optimizer.services.staged_retriever import StagedRetriever
from app.tools.context_optimizer.tools.context-optimizer.services.skill_matcher import SkillMatcher
from app.tools.context_optimizer.tools.context-optimizer.services.context_assembler import ContextAssembler, InstructionAssembler

router = APIRouter()


@router.post("/api/analyze")
async def analyze(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    task = body.get("task", "")
    existing = body.get("existing_content", [])
    if not task:
        raise HTTPException(status_code=400, detail="task is required")
    analyzer = RequirementAnalyzer()
    plan = analyzer.analyze(task, existing)
    cache = CacheService(db)
    cached = await cache.get(f"analyze:{task}")
    if cached:
        return JSONResponse(content=cached)
    await cache.set(f"analyze:{task}", plan, 0)
    return JSONResponse(content=plan)


@router.post("/api/budget")
async def budget(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    plan = body.get("plan", {})
    total = body.get("total_budget", 8000)
    allocator = BudgetAllocator()
    result = allocator.allocate(plan, total)
    cache = CacheService(db)
    await cache.set(f"budget:{plan.get('required_tools', [])}", result, 0)
    return JSONResponse(content=result)


@router.post("/api/refine")
async def refine(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    results = body.get("results", {})
    budget = body.get("budget", 8000)
    refiner = ResultRefiner()
    output = refiner.refine(results, budget)
    return JSONResponse(content=output)


@router.post("/api/track")
async def track(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    action = body.get("action")
    session_id = body.get("session_id", "default")
    content = body.get("content", "")
    tracker = ContextTracker(db)
    if action == "add":
        tokens = await tracker.add_content(session_id, content)
        return JSONResponse(content={"token_usage": tokens, "session_id": session_id})
    elif action == "get":
        items = await tracker.get_content(session_id)
        total = await tracker.get_total_tokens(session_id)
        return JSONResponse(content={"content": items, "total_tokens": total})
    raise HTTPException(status_code=400, detail=f"Unknown action: {action}")


@router.post("/api/tools/{tool_name}/invoke")
async def invoke_tool(tool_name: str, request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    params = body.get("params", {})
    budget = body.get("budget", 2000)
    existing = body.get("existing", [])
    analyzer = RequirementAnalyzer()
    plan = analyzer.analyze(params.get("task", ""), existing)
    allocator = BudgetAllocator()
    alloc = allocator.allocate(plan, budget)
    tool_budget = alloc["allocation"].get(tool_name, 0)
    cache = CacheService(db)
    cached = await cache.get(f"tool:{tool_name}:{str(params)[:100]}")
    if cached:
        return JSONResponse(content={"results": cached, "tokens_used": 0, "cached": True})
    return JSONResponse(content={
        "tool": tool_name,
        "budget": tool_budget,
        "plan": plan,
        "results": [],
        "tokens_used": 0,
    })


@router.post("/api/adaptive/budget")
async def adaptive_budget(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    task = body.get("task", "")
    existing = body.get("existing_content", [])
    total_budget = body.get("total_budget", 8000)
    if not task:
        raise HTTPException(status_code=400, detail="task is required")
    allocator = AdaptiveBudgetAllocator(db)
    result = await allocator.allocate(task, existing, total_budget)
    return JSONResponse(content=result)


@router.post("/api/feedback")
async def record_feedback(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    task = body.get("task", "")
    result = body.get("result", {})
    feedback = body.get("feedback", "")
    if not feedback:
        raise HTTPException(status_code=400, detail="feedback is required")
    learner = AdaptiveBudgetAllocator(db)
    outcome = await learner.record_feedback(task, result, feedback)
    return JSONResponse(content=outcome)


@router.post("/api/staged-retrieve")
async def staged_retrieve(request: Request):
    body = await request.json()
    required_tools = body.get("required_tools", [])
    search_queries = body.get("search_queries", {})
    budget_hints = body.get("budget_hints", {})
    task_context = body.get("task_context", {})

    retriever = StagedRetriever()
    results = await retriever.retrieve(
        required_tools, search_queries, budget_hints, task_context
    )
    return JSONResponse(content=results)


@router.post("/api/assemble-context")
async def assemble_context(request: Request):
    body = await request.json()
    instructions = body.get("instructions", {})
    intent = body.get("intent", {})
    staged_results = body.get("staged_results", {})
    skills = body.get("skills", [])

    assembler = ContextAssembler()
    result = await assembler.assemble(instructions, intent, staged_results, skills)
    return JSONResponse(content=result)


@router.post("/api/assemble-subagent")
async def assemble_subagent(request: Request):
    body = await request.json()
    task = body.get("task", "")
    parent_instructions = body.get("parent_instructions", {})
    domain = body.get("domain", "")
    context = body.get("context", {})
    skills = body.get("skills", [])

    assembler = InstructionAssembler()
    result = await assembler.generate_subagent_instructions(
        task=task,
        parent_instructions=parent_instructions,
        domain=domain,
        context=context,
        skills=skills,
    )
    return JSONResponse(content=result)
