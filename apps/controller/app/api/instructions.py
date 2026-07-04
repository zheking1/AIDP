from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from app.models.instructions import AgentInstruction
from app.db.database import async_session_factory

router = APIRouter(prefix="/api/instructions")


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


@router.post("")
async def create_or_update(req: InstructionCreate):
    async with async_session_factory() as session:
        result = await session.execute(
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
            session.add(inst)

        await session.commit()
        return {"ok": True, "agent_type": req.agent_type}


@router.get("")
async def get_instructions(project_id: int = 0, agent_type: str = "main"):
    async with async_session_factory() as session:
        result = await session.execute(
            select(AgentInstruction).where(
                AgentInstruction.project_id == project_id,
                AgentInstruction.agent_type == agent_type,
            )
        )
        inst = result.scalar_one_or_none()
        if not inst:
            return JSONResponse({"error": "not found"}, status_code=404)

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
async def list_instructions(project_id: int = 0):
    async with async_session_factory() as session:
        result = await session.execute(
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
async def update_instruction(instruction_id: int, req: InstructionUpdate):
    async with async_session_factory() as session:
        result = await session.execute(
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

        await session.commit()
        return {"ok": True, "id": instruction_id}


@router.delete("/{instruction_id}")
async def delete_instruction(instruction_id: int):
    async with async_session_factory() as session:
        result = await session.execute(
            select(AgentInstruction).where(AgentInstruction.id == instruction_id)
        )
        inst = result.scalar_one_or_none()
        if not inst:
            raise HTTPException(404, "Instruction not found")

        await session.delete(inst)
        await session.commit()
        return {"deleted": True, "id": instruction_id}