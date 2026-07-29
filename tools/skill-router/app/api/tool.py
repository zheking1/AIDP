import time
import uuid
from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings
from app.mcp.tools import _get_user_id

router = APIRouter(tags=["tool"])


class ToolInvokeRequest(BaseModel):
    trace_id: Optional[str] = None
    capability: str
    context: dict = {}
    input: dict = {}


class ToolInvokeResponse(BaseModel):
    trace_id: str
    tool: str
    capability: str
    success: bool
    output: Any = None
    error: Optional[dict] = None
    elapsed_ms: int = 0


CAPABILITIES = [
    {
        "name": "resolve_task",
        "description": "Resolve a task to matching skills.",
        "permission": "skill:resolve",
        "endpoint": "MCP resolve_task",
        "timeout_ms": 10000,
        "input_schema": {
            "type": "object",
            "required": ["task"],
            "properties": {
                "task": {"type": "string"},
                "mode": {"type": "string", "default": "auto"},
                "hint_tags": {"type": "array", "items": {"type": "string"}},
                "top_k": {"type": "integer", "default": 5},
                "role": {"type": "string"},
                "session_id": {"type": "string"},
                "api_key": {"type": "string"},
            },
        },
    },
    {
        "name": "skill_register",
        "description": "Register a new skill.",
        "permission": "skill:write",
        "endpoint": "MCP skill_register",
        "timeout_ms": 10000,
        "input_schema": {
            "type": "object",
            "required": ["name", "content"],
            "properties": {
                "name": {"type": "string"},
                "content": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "description": {"type": "string"},
                "group_name": {"type": "string"},
                "auto_classify": {"type": "boolean", "default": True},
                "api_key": {"type": "string"},
            },
        },
    },
    {
        "name": "skill_update",
        "description": "Update an existing skill.",
        "permission": "skill:write",
        "endpoint": "MCP skill_update",
        "timeout_ms": 5000,
        "input_schema": {
            "type": "object",
            "required": ["id"],
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "description": {"type": "string"},
                "content": {"type": "string"},
                "tags": {"type": "string"},
                "api_key": {"type": "string"},
            },
        },
    },
    {
        "name": "skill_delete",
        "description": "Delete a skill.",
        "permission": "skill:write",
        "endpoint": "MCP skill_delete",
        "timeout_ms": 5000,
        "input_schema": {
            "type": "object",
            "required": ["id"],
            "properties": {
                "id": {"type": "string"},
                "api_key": {"type": "string"},
            },
        },
    },
    {
        "name": "skill_get",
        "description": "Get skill details by ID.",
        "permission": "skill:read",
        "endpoint": "MCP skill_get",
        "timeout_ms": 5000,
        "input_schema": {
            "type": "object",
            "required": ["id"],
            "properties": {
                "id": {"type": "string"},
                "api_key": {"type": "string"},
            },
        },
    },
    {
        "name": "skill_run",
        "description": "Run a skill by task matching.",
        "permission": "skill:execute",
        "endpoint": "MCP skill_run",
        "timeout_ms": 30000,
        "input_schema": {
            "type": "object",
            "required": ["task"],
            "properties": {
                "task": {"type": "string"},
                "mode": {"type": "string", "default": "auto"},
                "top_k": {"type": "integer", "default": 5},
                "api_key": {"type": "string"},
            },
        },
    },
    {
        "name": "skill_list",
        "description": "List skills with filters.",
        "permission": "skill:read",
        "endpoint": "MCP skill_list",
        "timeout_ms": 5000,
        "input_schema": {
            "type": "object",
            "properties": {
                "q": {"type": "string"},
                "tag": {"type": "string"},
                "limit": {"type": "integer", "default": 50},
                "offset": {"type": "integer", "default": 0},
                "api_key": {"type": "string"},
            },
        },
    },
    {
        "name": "rule_create",
        "description": "Create a new rule.",
        "permission": "rule:write",
        "endpoint": "MCP rule_create",
        "timeout_ms": 5000,
        "input_schema": {
            "type": "object",
            "required": ["name", "content"],
            "properties": {
                "name": {"type": "string"},
                "content": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "priority": {"type": "integer", "default": 0},
                "api_key": {"type": "string"},
            },
        },
    },
    {
        "name": "rule_list",
        "description": "List rules with filters.",
        "permission": "rule:read",
        "endpoint": "MCP rule_list",
        "timeout_ms": 5000,
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 50},
                "offset": {"type": "integer", "default": 0},
                "api_key": {"type": "string"},
            },
        },
    },
    {
        "name": "model_add",
        "description": "Add an LLM model configuration.",
        "permission": "model:write",
        "endpoint": "MCP model_add",
        "timeout_ms": 5000,
        "input_schema": {
            "type": "object",
            "required": ["name", "endpoint", "api_key", "model_name"],
            "properties": {
                "name": {"type": "string"},
                "endpoint": {"type": "string"},
                "api_key": {"type": "string"},
                "model_name": {"type": "string"},
                "mcp_api_key": {"type": "string"},
            },
        },
    },
    {
        "name": "model_list",
        "description": "List LLM model configurations.",
        "permission": "model:read",
        "endpoint": "MCP model_list",
        "timeout_ms": 3000,
        "input_schema": {
            "type": "object",
            "properties": {
                "role": {"type": "string"},
                "mcp_api_key": {"type": "string"},
            },
        },
    },
    {
        "name": "cache_flush",
        "description": "Flush resolve cache.",
        "permission": "cache:write",
        "endpoint": "MCP cache_flush",
        "timeout_ms": 5000,
        "input_schema": {
            "type": "object",
            "properties": {
                "key_hash": {"type": "string"},
                "api_key": {"type": "string"},
            },
        },
    },
    {
        "name": "evolution_submit",
        "description": "Submit an evolution (version update).",
        "permission": "evolution:write",
        "endpoint": "MCP evolution_submit",
        "timeout_ms": 10000,
        "input_schema": {
            "type": "object",
            "required": ["resource_type", "resource_id", "change_type", "diff_summary"],
            "properties": {
                "resource_type": {"type": "string"},
                "resource_id": {"type": "string"},
                "change_type": {"type": "string"},
                "diff_summary": {"type": "string"},
                "api_key": {"type": "string"},
            },
        },
    },
    {
        "name": "evolution_rollback",
        "description": "Rollback an evolution.",
        "permission": "evolution:write",
        "endpoint": "MCP evolution_rollback",
        "timeout_ms": 10000,
        "input_schema": {
            "type": "object",
            "required": ["evolution_id", "trigger_reason"],
            "properties": {
                "evolution_id": {"type": "string"},
                "trigger_reason": {"type": "string"},
                "api_key": {"type": "string"},
            },
        },
    },
    {
        "name": "analyze_intent",
        "description": "Analyze user task intent and identify required tools, queries, budget hints. Stage 1 of AIDP context pipeline.",
        "permission": "skill:resolve",
        "endpoint": "MCP analyze_intent",
        "timeout_ms": 5000,
        "input_schema": {
            "type": "object",
            "required": ["task"],
            "properties": {
                "task": {"type": "string"},
                "instructions": {"type": "object"},
            },
        },
    },
]


@router.get("/tool/manifest")
async def get_manifest():
    return {
        "apiVersion": "aidp.dev/v1",
        "kind": "Tool",
        "metadata": {
            "name": "skillrouter",
            "displayName": "Skill Router",
            "version": "0.1.0",
            "description": "Core routing engine for AI agent task resolution.",
        },
        "runtime": {
            "modes": ["standalone", "managed"],
            "docker": {
                "image": "aidp/skillrouter:0.1.0",
                "port": 8788,
            },
        },
        "capabilities": [
            {
                "name": c["name"],
                "description": c["description"],
                "endpoint": c["endpoint"],
                "timeoutMs": c["timeout_ms"],
                "permission": c["permission"],
            }
            for c in CAPABILITIES
        ],
    }


@router.get("/tool/capabilities")
async def get_capabilities():
    return {
        "tool": "skillrouter",
        "version": "0.1.0",
        "capabilities": CAPABILITIES,
    }


@router.post("/tool/invoke", response_model=ToolInvokeResponse)
async def invoke_tool(req: ToolInvokeRequest):
    start = time.time()
    trace_id = req.trace_id or f"tr_{uuid.uuid4().hex[:12]}"
    inp = req.input

    try:
        from app.services.resolve_service import resolve_skills
        from app.services.skill_service import create_skill, update_skill, delete_skill, get_skill
        from app.services.rule_service import create_rule
        from app.services.cache_service import delete_cache
        from app.services.evolution_service import submit_evolution, rollback_evolution
        from app.services.model_service import add_model, list_models
        from app.db.database import async_session_factory
        from app.db.models import Skill
        from sqlalchemy import select

        api_key = inp.get("api_key") or req.context.get("api_key")
        user_id = await _get_user_id(api_key)
        # Public capabilities that don't require auth
        if not user_id and req.capability in ("analyze_intent", "resolve_task"):
            from app.db.database import async_session_factory as _asf
            from sqlalchemy import text as _text
            async with _asf() as _s:
                _r = await _s.execute(_text("SELECT id FROM users WHERE username = 'admin' LIMIT 1"))
                _row = _r.fetchone()
                if _row:
                    from uuid import UUID
                    user_id = UUID(str(_row[0]))
        if not user_id:
            return ToolInvokeResponse(
                trace_id=trace_id,
                tool="skillrouter",
                capability=req.capability,
                success=False,
                error={"code": "PERMISSION_DENIED", "message": "Invalid or missing api_key"},
                elapsed_ms=int((time.time() - start) * 1000),
            )

        output = None

        if req.capability == "resolve_task":
            async with async_session_factory() as session:
                result = await resolve_skills(
                    session=session,
                    task=inp.get("task", ""),
                    user_id=user_id,
                    mode=inp.get("mode", "auto"),
                    hint_tags=inp.get("hint_tags", []),
                    top_k=inp.get("top_k", 5),
                    role=inp.get("role"),
                )
                output = result

        elif req.capability == "skill_register":
            async with async_session_factory() as session:
                skill = await create_skill(
                    session=session,
                    name=inp.get("name", ""),
                    content=inp.get("content", ""),
                    tags=inp.get("tags"),
                    user_id=user_id,
                )
                # Update description separately (create_skill doesn't accept it)
                description = inp.get("description")
                if description:
                    from app.db.models import Skill
                    skill_obj = await session.get(Skill, skill.id)
                    if skill_obj:
                        skill_obj.description = description
                        await session.commit()
                
                # Generate embedding for the skill
                try:
                    from app.services.vector_service import generate_embedding
                    embed_text = f"{skill.name} {description or ''} {inp.get('content', '')[:500]}"
                    embedding = await generate_embedding(embed_text)
                    if embedding:
                        from app.db.models import Skill
                        skill_obj = await session.get(Skill, skill.id)
                        if skill_obj:
                            from pgvector.sqlalchemy import Vector
                            skill_obj.embedding = embedding
                            await session.commit()
                except Exception as e:
                    import logging
                    logging.warning(f"Failed to generate embedding for skill {skill.name}: {e}")
                
                output = {"id": str(skill.id), "name": skill.name, "tags": skill.tags or []}

        elif req.capability == "skill_update":
            async with async_session_factory() as session:
                result = await update_skill(
                    session=session,
                    skill_id=inp.get("id", ""),
                    name=inp.get("name"),
                    description=inp.get("description"),
                    content=inp.get("content"),
                    tags=inp.get("tags"),
                )
                output = result

        elif req.capability == "skill_delete":
            async with async_session_factory() as session:
                result = await delete_skill(session=session, skill_id=inp.get("id", ""))
                output = result

        elif req.capability == "skill_get":
            async with async_session_factory() as session:
                result = await get_skill(session=session, skill_id=inp.get("id", ""))
                if result:
                    output = {
                        "id": str(result.id),
                        "name": result.name,
                        "description": result.description,
                        "content": result.content,
                        "tags": result.tags or [],
                        "scope": result.scope,
                        "is_active": result.is_active,
                        "review_status": result.review_status,
                        "has_embedding": result.embedding is not None,
                    }
                else:
                    output = None

        elif req.capability == "skill_list":
            async with async_session_factory() as session:
                q = select(Skill).where(Skill.user_id == user_id, Skill.is_active == True)
                result = await session.execute(q)
                skills = result.scalars().all()
                output = [{"id": str(s.id), "name": s.name, "tags": s.tags or []} for s in skills]

        elif req.capability == "rule_create":
            async with async_session_factory() as session:
                result = await create_rule(
                    session=session,
                    name=inp.get("name", ""),
                    content=inp.get("content", ""),
                    tags=inp.get("tags"),
                    priority=inp.get("priority", 0),
                    user_id=user_id,
                )
                output = {"id": str(result.id), "name": result.name, "tags": result.tags or [], "priority": result.priority}

        elif req.capability == "rule_list":
            from app.db.models import Rule
            async with async_session_factory() as session:
                q = select(Rule).where(Rule.user_id == user_id)
                result = await session.execute(q)
                rules = result.scalars().all()
                output = [{"id": str(r.id), "name": r.name} for r in rules]

        elif req.capability == "model_add":
            result = await add_model(
                name=inp.get("name", ""),
                endpoint=inp.get("endpoint", ""),
                api_key=inp.get("api_key", ""),
                model_name=inp.get("model_name", ""),
                user_id=user_id,
            )
            output = result

        elif req.capability == "model_list":
            result = await list_models(role=inp.get("role"), user_id=user_id)
            output = result

        elif req.capability == "cache_flush":
            result = await delete_cache(key_hash=inp.get("key_hash"))
            output = result

        elif req.capability == "evolution_submit":
            result = await submit_evolution(
                resource_type=inp.get("resource_type", ""),
                resource_id=inp.get("resource_id", ""),
                change_type=inp.get("change_type", ""),
                diff_summary=inp.get("diff_summary", ""),
                user_id=user_id,
            )
            output = result

        elif req.capability == "evolution_rollback":
            result = await rollback_evolution(
                evolution_id=inp.get("evolution_id", ""),
                trigger_reason=inp.get("trigger_reason", ""),
                user_id=user_id,
            )
            output = result

        elif req.capability == "analyze_intent":
            from app.services.classification_service import analyze_intent_for_retrieval
            instructions = inp.get("instructions") or req.context.get("instructions", {})
            output = await analyze_intent_for_retrieval(
                task=inp.get("task", ""),
                instructions=instructions,
            )

        elif req.capability == "skill_run":
            from app.services.resolve_service import resolve_task
            output = await resolve_task(
                task=inp.get("task", ""),
                user_id=user_id,
                hint_tags=inp.get("hint_tags", []),
                role=inp.get("role"),
            )

        else:
            return ToolInvokeResponse(
                trace_id=trace_id,
                tool="skillrouter",
                capability=req.capability,
                success=False,
                error={"code": "NOT_FOUND", "message": f"Capability '{req.capability}' not found"},
                elapsed_ms=int((time.time() - start) * 1000),
            )

        return ToolInvokeResponse(
            trace_id=trace_id,
            tool="skillrouter",
            capability=req.capability,
            success=True,
            output=output,
            elapsed_ms=int((time.time() - start) * 1000),
        )

    except Exception as e:
        return ToolInvokeResponse(
            trace_id=trace_id,
            tool="skillrouter",
            capability=req.capability,
            success=False,
            error={"code": "INTERNAL_ERROR", "message": str(e)},
            elapsed_ms=int((time.time() - start) * 1000),
        )
