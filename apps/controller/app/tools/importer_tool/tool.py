import time
import uuid
from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select, and_

from app.tools.importer_tool.config import settings

router = APIRouter(tags=["tool"])

def _make_id(prefix: str = "pr") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


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


@router.get("/tool/manifest")
async def get_manifest():
    return {
        "apiVersion": "aidp.dev/v1",
        "kind": "Tool",
        "metadata": {
            "name": settings.APP_NAME,
            "displayName": "Importer Tool",
            "version": settings.APP_VERSION,
            "description": "Conversational content import tool. Classifies, quality-checks, and persists documents, skills, rules, and plans into AIDP.",
        },
        "runtime": {
            "modes": ["standalone", "managed"],
            "docker": {
                "image": f"aidp/{settings.APP_NAME}:{settings.APP_VERSION}",
                "port": settings.PORT,
            },
        },
        "capabilities": [
            {
                "name": "importer.import",
                "description": "Import a single item (text/url/file) with auto-classify, quality check, and persist.",
                "endpoint": "POST /tool/invoke",
                "timeoutMs": 30000,
                "permission": "importer:write",
            },
            {
                "name": "importer.import_batch",
                "description": "Scan a directory and batch-import all matching files.",
                "endpoint": "POST /tool/invoke",
                "timeoutMs": 120000,
                "permission": "importer:write",
            },
            {
                "name": "importer.classify",
                "description": "Classify content without importing.",
                "endpoint": "POST /tool/invoke",
                "timeoutMs": 5000,
                "permission": "importer:read",
            },
            {
                "name": "importer.status",
                "description": "Get import session status.",
                "endpoint": "POST /tool/invoke",
                "timeoutMs": 3000,
                "permission": "importer:read",
            },
            {
                "name": "promotion.review",
                "description": "Submit content for AI-powered promotion review. Analyzes quality, security, generality, completeness, and risk.",
                "endpoint": "POST /tool/invoke",
                "timeoutMs": 120000,
                "permission": "promotion:write",
            },
            {
                "name": "promotion.execute",
                "description": "Execute the promotion after review passes. Changes scope from personal to global.",
                "endpoint": "POST /tool/invoke",
                "timeoutMs": 30000,
                "permission": "promotion:write",
            },
            {
                "name": "promotion.config.save",
                "description": "Save or update a user's AI review configuration (provider, model, API key, redaction rules).",
                "endpoint": "POST /tool/invoke",
                "timeoutMs": 5000,
                "permission": "promotion:write",
            },
            {
                "name": "promotion.config.get",
                "description": "Get the user's current AI review configuration.",
                "endpoint": "POST /tool/invoke",
                "timeoutMs": 3000,
                "permission": "promotion:read",
            },
            {
                "name": "promotion.logs",
                "description": "Get promotion audit logs for a given entity or user.",
                "endpoint": "POST /tool/invoke",
                "timeoutMs": 5000,
                "permission": "promotion:read",
            },
        ],
    }


@router.get("/tool/capabilities")
async def get_capabilities():
    return {
        "tool": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "capabilities": [
            {
                "name": "importer.import",
                "description": "Import a single item (text/url/file) with auto-classify, quality check, and persist.",
                "permission": "importer:write",
                "timeout_ms": 30000,
                "input_schema": {
                    "type": "object",
                    "required": ["source"],
                    "properties": {
                        "source": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string", "enum": ["text", "url", "file"]},
                                "content": {"type": "string"},
                                "url": {"type": "string"},
                                "path": {"type": "string"},
                                "name": {"type": "string"},
                            },
                        },
                        "session_id": {"type": "string"},
                        "confirm": {"type": "object"},
                        "auto_confirm": {"type": "boolean"},
                        "scope": {"type": "string"},
                        "project_id": {"type": "integer"},
                    },
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"},
                        "status": {"type": "string"},
                        "classification": {"type": "object"},
                        "quality_check": {"type": "object"},
                        "result": {"type": "object"},
                        "summary": {"type": "string"},
                    },
                },
            },
            {
                "name": "importer.import_batch",
                "description": "Scan a directory and batch-import all matching files.",
                "permission": "importer:write",
                "timeout_ms": 120000,
                "input_schema": {
                    "type": "object",
                    "required": ["source"],
                    "properties": {
                        "source": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string", "enum": ["directory"]},
                                "path": {"type": "string"},
                                "pattern": {"type": "string"},
                            },
                        },
                        "confirm": {"type": "array"},
                        "scope": {"type": "string"},
                        "project_id": {"type": "integer"},
                    },
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"},
                        "status": {"type": "string"},
                        "items": {"type": "array"},
                        "summary": {"type": "object"},
                    },
                },
            },
            {
                "name": "importer.classify",
                "description": "Classify content without importing.",
                "permission": "importer:read",
                "timeout_ms": 5000,
                "input_schema": {
                    "type": "object",
                    "required": ["content"],
                    "properties": {
                        "content": {"type": "string"},
                        "filename": {"type": "string"},
                    },
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "confidence": {"type": "string"},
                        "title": {"type": "string"},
                        "suggested_tags": {"type": "array"},
                        "suggested_category": {"type": "string"},
                    },
                },
            },
            {
                "name": "importer.status",
                "description": "Get import session status.",
                "permission": "importer:read",
                "timeout_ms": 3000,
                "input_schema": {
                    "type": "object",
                    "required": ["session_id"],
                    "properties": {
                        "session_id": {"type": "string"},
                    },
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"},
                        "status": {"type": "string"},
                        "items": {"type": "array"},
                        "summary": {"type": "object"},
                    },
                },
            },
            {
                "name": "promotion.review",
                "description": "Submit content for AI-powered promotion review.",
                "permission": "promotion:write",
                "timeout_ms": 120000,
                "input_schema": {
                    "type": "object",
                    "required": ["entity_type", "entity_id", "content"],
                    "properties": {
                        "entity_type": {"type": "string", "enum": ["skill", "rule", "knowledge"]},
                        "entity_id": {"type": "string"},
                        "content": {"type": "string"},
                        "from_scope": {"type": "string", "default": "personal"},
                        "triggered_by": {"type": "string"},
                        "user_id": {"type": "string"},
                    },
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string"},
                        "from_scope": {"type": "string"},
                        "to_scope": {"type": "string"},
                        "review_report": {"type": "object"},
                        "triggered_by": {"type": "string"},
                        "log_id": {"type": "string"},
                    },
                },
            },
            {
                "name": "promotion.execute",
                "description": "Execute promotion after review passes.",
                "permission": "promotion:write",
                "timeout_ms": 30000,
                "input_schema": {
                    "type": "object",
                    "required": ["entity_type", "entity_id"],
                    "properties": {
                        "entity_type": {"type": "string", "enum": ["skill", "rule", "knowledge"]},
                        "entity_id": {"type": "string"},
                    },
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string"},
                        "entity_id": {"type": "string"},
                    },
                },
            },
            {
                "name": "promotion.config.save",
                "description": "Save or update user's AI review configuration.",
                "permission": "promotion:write",
                "timeout_ms": 5000,
                "input_schema": {
                    "type": "object",
                    "required": ["user_id"],
                    "properties": {
                        "user_id": {"type": "string"},
                        "provider": {"type": "string"},
                        "api_base": {"type": "string"},
                        "model_name": {"type": "string"},
                        "api_key": {"type": "string"},
                        "max_tokens": {"type": "integer"},
                        "temperature": {"type": "number"},
                        "redact_regexes": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "config_id": {"type": "string"},
                        "status": {"type": "string"},
                    },
                },
            },
            {
                "name": "promotion.config.get",
                "description": "Get user's current AI review configuration.",
                "permission": "promotion:read",
                "timeout_ms": 3000,
                "input_schema": {
                    "type": "object",
                    "required": ["user_id"],
                    "properties": {
                        "user_id": {"type": "string"},
                    },
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "config": {"type": "object"},
                    },
                },
            },
            {
                "name": "promotion.logs",
                "description": "Get promotion audit logs.",
                "permission": "promotion:read",
                "timeout_ms": 5000,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "entity_type": {"type": "string"},
                        "entity_id": {"type": "string"},
                        "limit": {"type": "integer"},
                    },
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "logs": {"type": "array"},
                        "total": {"type": "integer"},
                    },
                },
            },
        ],
    }


@router.post("/tool/invoke", response_model=ToolInvokeResponse)
async def invoke_tool(req: ToolInvokeRequest):
    start = time.time()
    trace_id = req.trace_id or f"tr_{uuid.uuid4().hex[:12]}"

    try:
        inp = req.input

        if req.capability == "importer.import":
            from app.tools.importer_tool.services.orchestrator import handle_import
            output = await handle_import(inp, trace_id=trace_id, context=req.context)

        elif req.capability == "importer.import_batch":
            from app.tools.importer_tool.services.orchestrator import handle_import_batch
            output = await handle_import_batch(inp, trace_id=trace_id, context=req.context)

        elif req.capability == "importer.classify":
            from app.tools.importer_tool.services.classifier import classify_content
            result = classify_content(inp.get("content", ""), inp.get("filename"))
            output = result

        elif req.capability == "importer.status":
            from app.tools.importer_tool.db.models import async_session, ImportSession
            from sqlalchemy import select
            session_id = inp.get("session_id")
            if not session_id:
                return ToolInvokeResponse(
                    trace_id=trace_id, tool=settings.APP_NAME,
                    capability=req.capability, success=False,
                    error={"code": "VALIDATION_ERROR", "message": "session_id is required"},
                    elapsed_ms=int((time.time() - start) * 1000),
                )
            async with async_session() as db:
                result = await db.execute(select(ImportSession).where(ImportSession.id == session_id))
                session = result.scalar_one_or_none()
                if not session:
                    return ToolInvokeResponse(
                        trace_id=trace_id, tool=settings.APP_NAME,
                        capability=req.capability, success=False,
                        error={"code": "NOT_FOUND", "message": "Session not found"},
                        elapsed_ms=int((time.time() - start) * 1000),
                    )
                items = [item.to_dict() for item in session.items]
                s = session.to_dict()
                s["items"] = items
                output = s

        elif req.capability == "promotion.review":
            from app.tools.importer_tool.services.promotion_review import PromotionReviewService, RedactionEngine
            from app.tools.importer_tool.db.models import async_session, PromotionReviewConfig, PromotionLog

            entity_type = inp["entity_type"]
            entity_id = inp["entity_id"]
            content = inp["content"]
            from_scope = inp.get("from_scope", "personal")
            triggered_by = inp.get("triggered_by", "system")
            user_id = inp.get("user_id")

            service = PromotionReviewService()
            async with async_session() as db:
                config = None
                if user_id:
                    r = await db.execute(
                        select(PromotionReviewConfig).where(
                            and_(PromotionReviewConfig.user_id == user_id, PromotionReviewConfig.is_active == True)
                        )
                    )
                    config = r.scalar_one_or_none()

                review_result = await service.submit_for_review(
                    entity_type=entity_type, entity_id=entity_id,
                    content=content, from_scope=from_scope,
                    triggered_by=triggered_by, config=config,
                )

                log = PromotionLog(
                    id=_make_id("pl"),
                    entity_type=entity_type, entity_id=entity_id,
                    action=review_result["action"],
                    from_scope=review_result["from_scope"],
                    to_scope=review_result["to_scope"],
                    review_report=review_result["review_report"],
                    triggered_by=triggered_by,
                    metadata=json.dumps({"trace_id": trace_id}),
                )
                db.add(log)
                await db.commit()

                review_report_dict = json.loads(review_result["review_report"])
                output = {
                    "action": review_result["action"],
                    "from_scope": review_result["from_scope"],
                    "to_scope": review_result["to_scope"],
                    "review_report": review_report_dict,
                    "triggered_by": triggered_by,
                    "log_id": log.id,
                }

        elif req.capability == "promotion.execute":
            from app.tools.importer_tool.services.promotion_review import PromotionReviewService
            from app.tools.importer_tool.db.models import async_session, PromotionLog

            entity_type = inp["entity_type"]
            entity_id = inp["entity_id"]
            triggered_by = inp.get("triggered_by", "system")

            service = PromotionReviewService()
            controller_base = settings.CONTROLLER_URL
            result = await service.execute_promotion(entity_type, entity_id, controller_base)

            async with async_session() as db:
                log = PromotionLog(
                    id=_make_id("pl"),
                    entity_type=entity_type, entity_id=entity_id,
                    action="promoted",
                    from_scope="personal", to_scope="global",
                    triggered_by=triggered_by,
                    metadata=json.dumps({"trace_id": trace_id, "controller_result": str(result)}),
                )
                db.add(log)
                await db.commit()

            output = {"status": "promoted", "entity_id": entity_id}

        elif req.capability == "promotion.config.save":
            from app.tools.importer_tool.db.models import async_session, PromotionReviewConfig
            from sqlalchemy import select, and_

            user_id = inp["user_id"]
            async with async_session() as db:
                r = await db.execute(
                    select(PromotionReviewConfig).where(PromotionReviewConfig.user_id == user_id)
                )
                config = r.scalar_one_or_none()

                if not config:
                    config = PromotionReviewConfig(
                        id=_make_id("pc"),
                        user_id=user_id,
                    )
                    db.add(config)

                for field in ("provider", "api_base", "model_name", "api_key", "max_tokens", "temperature", "is_active"):
                    if field in inp:
                        setattr(config, field, inp[field])
                if "redact_regexes" in inp:
                    config.redact_regexes = json.dumps(inp["redact_regexes"])

                await db.commit()
                output = {"config_id": config.id, "status": "saved"}

        elif req.capability == "promotion.config.get":
            from app.tools.importer_tool.db.models import async_session, PromotionReviewConfig
            from sqlalchemy import select

            user_id = inp["user_id"]
            async with async_session() as db:
                r = await db.execute(
                    select(PromotionReviewConfig).where(PromotionReviewConfig.user_id == user_id)
                )
                config = r.scalar_one_or_none()
                output = {"config": config.to_dict() if config else None}

        elif req.capability == "promotion.logs":
            from app.tools.importer_tool.db.models import async_session, PromotionLog
            from sqlalchemy import select

            entity_type = inp.get("entity_type")
            entity_id = inp.get("entity_id")
            limit = inp.get("limit", 50)

            async with async_session() as db:
                q = select(PromotionLog)
                if entity_type and entity_id:
                    q = q.where(
                        and_(PromotionLog.entity_type == entity_type, PromotionLog.entity_id == entity_id)
                    )
                q = q.order_by(PromotionLog.created_at.desc()).limit(limit)
                r = await db.execute(q)
                logs = [log.to_dict() for log in r.scalars().all()]
                output = {"logs": logs, "total": len(logs)}

        else:
            return ToolInvokeResponse(
                trace_id=trace_id, tool=settings.APP_NAME,
                capability=req.capability, success=False,
                error={"code": "NOT_FOUND", "message": f"Capability '{req.capability}' not found"},
                elapsed_ms=int((time.time() - start) * 1000),
            )

        return ToolInvokeResponse(
            trace_id=trace_id, tool=settings.APP_NAME,
            capability=req.capability, success=True,
            output=output,
            elapsed_ms=int((time.time() - start) * 1000),
        )

    except Exception as e:
        return ToolInvokeResponse(
            trace_id=trace_id, tool=settings.APP_NAME,
            capability=req.capability, success=False,
            error={"code": "INTERNAL_ERROR", "message": str(e)},
            elapsed_ms=int((time.time() - start) * 1000),
        )
