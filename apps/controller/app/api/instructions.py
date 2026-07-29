from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.instructions import AgentInstruction
from app.services.context_pipeline import ContextPipeline

router = APIRouter(prefix="/api/instructions")


# ===== Request/Response Models =====

class InstructionCreate(BaseModel):
    project_id: int = 0
    agent_type: str = "main"
    role: str = ""
    constraints: dict = {}
    rules: list = []


class InstructionUpdate(BaseModel):
    role: Optional[str] = None
    constraints: Optional[dict] = None
    rules: Optional[list] = None


class ContextRequest(BaseModel):
    task: str
    project_id: str = "0"
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    hint_tags: List[str] = []


class SubagentRequest(BaseModel):
    task: str
    parent_trace_id: str
    project_id: str = "0"
    specialization: str = ""


# ===== CRUD Endpoints =====

@router.post("")
async def create_or_update(req: InstructionCreate, db: AsyncSession = Depends(get_db)):
    """Create or update agent instructions for a project"""
    result = await db.execute(
        select(AgentInstruction).where(
            AgentInstruction.project_id == req.project_id,
            AgentInstruction.agent_type == req.agent_type,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.role = req.role or existing.role
        existing.constraints = req.constraints or existing.constraints
        existing.rules = req.rules or existing.rules
    else:
        inst = AgentInstruction(
            project_id=req.project_id,
            agent_type=req.agent_type,
            role=req.role,
            constraints=req.constraints or {},
            rules=req.rules or [],
        )
        db.add(inst)

    await db.commit()
    return {"success": True, "agent_type": req.agent_type}


@router.get("")
async def get_instructions(
    project_id: int = 0, 
    agent_type: str = "main",
    db: AsyncSession = Depends(get_db)
):
    """Get agent instructions for a project"""
    result = await db.execute(
        select(AgentInstruction).where(
            AgentInstruction.project_id == project_id,
            AgentInstruction.agent_type == agent_type,
        )
    )
    inst = result.scalar_one_or_none()
    if not inst:
        return JSONResponse(
            {"error": "not_found", "message": "Instructions not found"}, 
            status_code=404
        )

    return {
        "id": inst.id,
        "project_id": inst.project_id,
        "agent_type": inst.agent_type,
        "role": inst.role,
        "constraints": inst.constraints,
        "rules": inst.rules,
        "created_at": inst.created_at.isoformat() if inst.created_at else None,
        "updated_at": inst.updated_at.isoformat() if inst.updated_at else None,
    }


@router.get("/list")
async def list_instructions(project_id: int = 0, db: AsyncSession = Depends(get_db)):
    """List all instructions for a project"""
    result = await db.execute(
        select(AgentInstruction).where(AgentInstruction.project_id == project_id)
    )
    instructions = result.scalars().all()
    return [
        {
            "id": i.id,
            "agent_type": i.agent_type,
            "role": i.role[:100] if i.role else None,
            "rules_count": len(i.rules or []),
        }
        for i in instructions
    ]


@router.put("/{instruction_id}")
async def update_instruction(
    instruction_id: int, 
    req: InstructionUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update specific instruction fields"""
    result = await db.execute(
        select(AgentInstruction).where(AgentInstruction.id == instruction_id)
    )
    inst = result.scalar_one_or_none()
    if not inst:
        raise HTTPException(404, "Instruction not found")

    if req.role is not None:
        inst.role = req.role
    if req.constraints is not None:
        inst.constraints = req.constraints
    if req.rules is not None:
        inst.rules = req.rules

    await db.commit()
    return {"success": True, "id": instruction_id}


@router.delete("/{instruction_id}")
async def delete_instruction(instruction_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an instruction"""
    result = await db.execute(
        select(AgentInstruction).where(AgentInstruction.id == instruction_id)
    )
    inst = result.scalar_one_or_none()
    if not inst:
        raise HTTPException(404, "Instruction not found")

    await db.delete(inst)
    await db.commit()
    return {"success": True, "deleted": True, "id": instruction_id}


# ===== 5-Stage Pipeline Endpoints =====

@router.post("/context")
async def assemble_context(
    req: ContextRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Execute full 5-Stage Context Pipeline:
    
    Stage 0: Load Agent Instructions
    Stage 1: Intent Analysis  
    Stage 2: Staged Retrieval (Memory -> Knowledge -> Asset)
    Stage 3: Skill Matching
    Stage 4: Context Assembly
    
    Returns assembled context package for LLM
    """
    try:
        pipeline = ContextPipeline(db)
        ctx = await pipeline.execute(
            task=req.task,
            project_id=req.project_id,
            user_id=req.user_id,
            session_id=req.session_id,
            hint_tags=req.hint_tags
        )
        
        return {
            "success": True,
            "trace_id": ctx.trace_id,
            "data": {
                "system_prompt": ctx.assembled_context.get("system_prompt"),
                "user_message": ctx.assembled_context.get("user_message"),
                "metadata": ctx.assembled_context.get("metadata"),
                "token_estimate": ctx.token_estimate,
                "stage_timings": ctx.stage_timings,
                "sources": {
                    "instructions_loaded": bool(ctx.instructions),
                    "intent_detected": ctx.intent.get("intent"),
                    "memories_count": len(ctx.memories),
                    "knowledge_count": len(ctx.knowledge),
                    "assets_count": len(ctx.assets),
                    "skills_matched": len(ctx.skills),
                    "rules_matched": len(ctx.rules)
                }
            }
        }
        
    except Exception as e:
        return JSONResponse(
            {
                "success": False,
                "error": str(e),
                "message": "Pipeline execution failed"
            },
            status_code=500
        )


@router.post("/subagent")
async def generate_subagent_instructions(
    req: SubagentRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate specialized instructions for a subagent
    
    Creates a focused context package for delegated tasks
    """
    try:
        # Load parent instructions
        result = await db.execute(
            select(AgentInstruction).where(
                AgentInstruction.project_id == int(req.project_id),
                AgentInstruction.agent_type == "main"
            )
        )
        parent_inst = result.scalar_one_or_none()
        
        # Build subagent-specific instructions
        subagent_role = f"""You are a specialized subagent focused on: {req.specialization}

Parent Task Context:
- You are working on a sub-task of: {req.parent_trace_id}
- Your focus area: {req.specialization}
- Original task: {req.task}

Guidelines:
- Focus only on your specialization area
- Report back with structured results
- Ask for clarification if the task is unclear
"""
        
        if parent_inst and parent_inst.constraints:
            constraints = parent_inst.constraints
        else:
            constraints = {"max_tokens": 2000, "response_format": "structured"}
        
        return {
            "success": True,
            "data": {
                "role": subagent_role,
                "constraints": constraints,
                "task": req.task,
                "specialization": req.specialization,
                "parent_trace_id": req.parent_trace_id
            }
        }
        
    except Exception as e:
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )


@router.get("/stages/info")
async def get_pipeline_info():
    """Get information about the 5-stage pipeline"""
    return {
        "success": True,
        "data": {
            "stages": [
                {
                    "stage": 0,
                    "name": "Load Instructions",
                    "description": "Load agent instructions from database (role, constraints, rules)",
                    "output": "instructions dict"
                },
                {
                    "stage": 1,
                    "name": "Intent Analysis",
                    "description": "Analyze user task to extract intent, domains, complexity",
                    "output": "intent dict with domains, complexity, tags"
                },
                {
                    "stage": 2,
                    "name": "Staged Retrieval",
                    "description": "Retrieve relevant context from Memory, Knowledge, Assets",
                    "output": "lists of memories, knowledge docs, assets"
                },
                {
                    "stage": 3,
                    "name": "Skill Matching",
                    "description": "Match relevant skills from SkillRouter",
                    "output": "list of matched skills and rules"
                },
                {
                    "stage": 4,
                    "name": "Context Assembly",
                    "description": "Assemble final context package with token budget management",
                    "output": "assembled context with system_prompt, metadata"
                }
            ],
            "version": "1.0.0"
        }
    }
