import datetime
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.db.database import async_session_factory
from app.modules.evolution.models import EvolutionVersion

logger = logging.getLogger(__name__)
router = APIRouter()


class EvolutionPropose(BaseModel):
    title: str
    description: str = ""
    source_project_id: int = 0
    source_event_id: Optional[int] = None
    source_analysis_id: Optional[int] = None
    source_tool: str = ""
    changes: dict = {}
    affected_tools: list = []
    version: str = "0.1.0"


class ReviewAction(BaseModel):
    version_id: int
    action: str
    comment: str = ""
    reviewer_id: int = 0
    reviewer_name: str = ""


class VersionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    changes: Optional[dict] = None
    affected_tools: Optional[list] = None
    version: Optional[str] = None


async def get_db():
    async with async_session_factory() as db:
        yield db


@router.post("/propose")
async def propose_evolution(req: EvolutionPropose, db: AsyncSession = Depends(get_db)):
    """项目级进化提案 — 将发现的优秀模式提交给管理员审核"""
    version = EvolutionVersion(
        version=req.version,
        level="project",
        title=req.title,
        description=req.description,
        source_project_id=req.source_project_id,
        source_event_id=req.source_event_id,
        source_analysis_id=req.source_analysis_id,
        source_tool=req.source_tool,
        changes=req.changes,
        affected_tools=req.affected_tools,
        review_status="pending",
        review_log=[],
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)

    return {"success": True, "version_id": version.id, "status": "pending"}


@router.get("/versions")
async def list_versions(
    level: str = "",
    status: str = "",
    project_id: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """列出进化版本"""
    q = select(EvolutionVersion)
    if level:
        q = q.where(EvolutionVersion.level == level)
    if status:
        q = q.where(EvolutionVersion.review_status == status)
    if project_id:
        q = q.where(EvolutionVersion.source_project_id == project_id)
    q = q.order_by(desc(EvolutionVersion.created_at)).limit(100)

    result = await db.execute(q)
    versions = result.scalars().all()
    return {
        "versions": [
            {
                "id": v.id,
                "version": v.version,
                "level": v.level,
                "title": v.title,
                "description": v.description[:200] if v.description else "",
                "review_status": v.review_status,
                "source_project_id": v.source_project_id,
                "created_by_name": v.created_by_name,
                "affected_tools": v.affected_tools,
                "created_at": v.created_at.isoformat() if v.created_at else None,
                "published_at": v.published_at.isoformat() if v.published_at else None,
            }
            for v in versions
        ],
        "pending_count": len([v for v in versions if v.review_status == "pending"]),
        "total": len(versions),
    }


@router.get("/versions/{version_id}")
async def get_version(version_id: int, db: AsyncSession = Depends(get_db)):
    """获取单个版本详情"""
    result = await db.execute(
        select(EvolutionVersion).where(EvolutionVersion.id == version_id)
    )
    v = result.scalar_one_or_none()
    if not v:
        raise HTTPException(404, "Version not found")

    return {
        "id": v.id,
        "version": v.version,
        "level": v.level,
        "title": v.title,
        "description": v.description,
        "source_project_id": v.source_project_id,
        "created_by_name": v.created_by_name,
        "changes": v.changes,
        "affected_tools": v.affected_tools,
        "affected_projects": v.affected_projects,
        "review_status": v.review_status,
        "reviewed_by_name": v.reviewed_by_name,
        "reviewed_at": v.reviewed_at.isoformat() if v.reviewed_at else None,
        "review_comment": v.review_comment,
        "review_log": v.review_log,
        "is_rollback_point": v.is_rollback_point,
        "parent_version": v.parent_version,
        "created_at": v.created_at.isoformat() if v.created_at else None,
        "published_at": v.published_at.isoformat() if v.published_at else None,
    }


@router.post("/review")
async def review_evolution(req: ReviewAction, db: AsyncSession = Depends(get_db)):
    """管理员审核进化提案"""
    result = await db.execute(
        select(EvolutionVersion).where(EvolutionVersion.id == req.version_id)
    )
    v = result.scalar_one_or_none()
    if not v:
        raise HTTPException(404, "Version not found")

    if v.review_status not in ("pending", "needs_modification"):
        raise HTTPException(400, f"Cannot review version in status: {v.review_status}")

    log_entry = {
        "action": req.action,
        "comment": req.comment,
        "reviewer": req.reviewer_name,
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }

    review_log = (v.review_log or []) + [log_entry]

    if req.action == "approve":
        v.review_status = "approved"
        v.level = "system"
        v.reviewed_by = req.reviewer_id
        v.reviewed_by_name = req.reviewer_name
        v.reviewed_at = datetime.datetime.utcnow()
        v.review_comment = req.comment
        v.published_at = datetime.datetime.utcnow()
    elif req.action == "reject":
        v.review_status = "rejected"
        v.reviewed_by = req.reviewer_id
        v.reviewed_by_name = req.reviewer_name
        v.reviewed_at = datetime.datetime.utcnow()
        v.review_comment = req.comment
    elif req.action == "request_changes":
        v.review_status = "needs_modification"
        v.review_comment = req.comment
    else:
        raise HTTPException(400, f"Unknown action: {req.action}")

    v.review_log = review_log
    await db.commit()

    return {
        "success": True,
        "version_id": v.id,
        "new_status": v.review_status,
        "new_level": v.level,
    }


@router.post("/versions/{version_id}/publish")
async def publish_version(version_id: int, db: AsyncSession = Depends(get_db)):
    """发布已批准的版本到系统级"""
    result = await db.execute(
        select(EvolutionVersion).where(EvolutionVersion.id == version_id)
    )
    v = result.scalar_one_or_none()
    if not v:
        raise HTTPException(404, "Version not found")
    if v.review_status != "approved":
        raise HTTPException(400, "Only approved versions can be published")

    v.published_at = datetime.datetime.utcnow()
    v.level = "system"
    await db.commit()

    return {"success": True, "version_id": v.id, "published": True}


@router.post("/versions/{version_id}/rollback")
async def rollback_version(version_id: int, db: AsyncSession = Depends(get_db)):
    """回退到指定版本"""
    result = await db.execute(
        select(EvolutionVersion).where(EvolutionVersion.id == version_id)
    )
    v = result.scalar_one_or_none()
    if not v:
        raise HTTPException(404, "Version not found")
    if v.level != "system":
        raise HTTPException(400, "Can only rollback system-level versions")

    v.is_rollback_point = True
    await db.commit()

    return {"success": True, "version_id": v.id, "rolled_back": True}


@router.put("/versions/{version_id}")
async def update_version(
    version_id: int, req: VersionUpdate, db: AsyncSession = Depends(get_db)
):
    """更新版本信息"""
    result = await db.execute(
        select(EvolutionVersion).where(EvolutionVersion.id == version_id)
    )
    v = result.scalar_one_or_none()
    if not v:
        raise HTTPException(404, "Version not found")

    if req.title is not None:
        v.title = req.title
    if req.description is not None:
        v.description = req.description
    if req.changes is not None:
        v.changes = req.changes
    if req.affected_tools is not None:
        v.affected_tools = req.affected_tools
    if req.version is not None:
        v.version = req.version

    await db.commit()
    return {"success": True, "version_id": v.id}


@router.delete("/versions/{version_id}")
async def delete_version(version_id: int, db: AsyncSession = Depends(get_db)):
    """删除版本（仅 pending/rejected）"""
    result = await db.execute(
        select(EvolutionVersion).where(EvolutionVersion.id == version_id)
    )
    v = result.scalar_one_or_none()
    if not v:
        raise HTTPException(404, "Version not found")
    if v.level == "system":
        raise HTTPException(400, "Cannot delete system-level versions")

    await db.delete(v)
    await db.commit()
    return {"success": True, "deleted": True}


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """进化统计概览"""
    import asyncio

    async def _count(where_clause):
        q = select(EvolutionVersion).where(where_clause)
        r = await db.execute(q)
        return len(r.scalars().all())

    pending = await _count(EvolutionVersion.review_status == "pending")
    approved = await _count(EvolutionVersion.review_status == "approved")
    system = await _count(EvolutionVersion.level == "system")
    project = await _count(EvolutionVersion.level == "project")
    total = await _count(EvolutionVersion.id > 0)

    return {
        "total": total,
        "pending": pending,
        "approved": approved,
        "system_level": system,
        "project_level": project,
    }


class SmartProposeRequest(BaseModel):
    task: str = ""
    result: str = ""
    event_type: str = "success"
    source: str = "controller"
    project_id: int = 0


@router.post("/analyze-and-propose")
async def analyze_and_propose(req: SmartProposeRequest, db: AsyncSession = Depends(get_db)):
    """智能分析 → 调用 evolution-engine LLM 分析 → 自动生成进化提案"""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "http://127.0.0.1:18089/api/events",
                json={
                    "type": req.event_type,
                    "source": req.source,
                    "content": req.task,
                    "result": req.result,
                    "metadata": {"project_id": req.project_id},
                },
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code == 200:
                data = resp.json()
                analysis = data.get("analysis", {})
                targets = data.get("targets", [])

                confidence = analysis.get("confidence", 0)
                if confidence >= 0.5:
                    version = EvolutionVersion(
                        version="0.1.0",
                        level="project",
                        title=analysis.get("success_pattern") or analysis.get("fix_pattern") or req.task[:100],
                        description=f"任务: {req.task}\n分析: {analysis.get('category', '')}\n模式: {analysis.get('success_pattern') or analysis.get('fix_pattern', '')}",
                        source_project_id=req.project_id,
                        changes={
                            "type": analysis.get("category"),
                            "pattern": analysis.get("success_pattern") or analysis.get("fix_pattern"),
                            "root_cause": analysis.get("root_cause"),
                            "update_type": analysis.get("update_type"),
                        },
                        affected_tools=targets,
                        review_status="pending",
                        review_log=[],
                    )
                    db.add(version)
                    await db.commit()
                    await db.refresh(version)

                    return {
                        "success": True,
                        "version_id": version.id,
                        "title": version.title,
                        "confidence": confidence,
                        "analysis": analysis,
                        "targets": targets,
                        "status": "pending",
                        "auto_proposed": True,
                    }
                else:
                    return {
                        "success": True,
                        "auto_proposed": False,
                        "confidence": confidence,
                        "message": "置信度不足，跳过自动提案",
                        "analysis": analysis,
                    }
            else:
                return {"success": False, "error": f"Evolution engine returned {resp.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e), "message": "Evolution engine 不可用，请确认服务是否启动 (端口 18089)"}