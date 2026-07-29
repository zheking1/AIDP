"""
Skills Module Routes
技能模块 API 路由 - 三层架构: global/personal/project
"""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.db.database import async_session_factory
from app.modules.skills.models import Skill, SkillGroup, SkillFile, SkillEvolution
from app.core.permissions import require_permissions, check_scope_read_access
from app.core.utils import get_current_user_id
from app.api.auth import get_current_user

router = APIRouter()


class SkillCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    scope: str = Field("personal", description="global, personal, project")
    instruction: Optional[str] = None
    content: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    exec_config: Optional[dict] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)
    weight_config: Optional[dict] = Field(default_factory=dict)
    examples: List[dict] = Field(default_factory=list)
    group_id: Optional[str] = None
    source_type: str = Field("manual")
    source_url: Optional[str] = None


class SkillUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    instruction: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    exec_config: Optional[dict] = None
    dependencies: Optional[List[str]] = None
    weight_config: Optional[dict] = None
    examples: Optional[List[dict]] = None
    group_id: Optional[str] = None
    review_status: Optional[str] = None
    promotion_status: Optional[str] = None
    promotion_report: Optional[str] = None
    promotion_source_id: Optional[str] = None
    promotion_source_scope: Optional[str] = None


class SkillGroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    scope: str = Field("personal")
    parent_id: Optional[str] = None


class SkillFileCreate(BaseModel):
    path: str = Field(..., min_length=1)
    content: Optional[str] = None
    language: Optional[str] = None
    is_entry: bool = False
    sort_order: int = 0


class SkillSearchQuery(BaseModel):
    query: str = Field(..., min_length=1)
    scope: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    top_k: int = Field(20, ge=1, le=100)


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        yield session


def _scope_filter(model, scope: str, user_id: str = None, project_id: int = None):
    if scope == "global":
        return model.scope == "global"
    elif scope == "personal":
        return and_(model.scope == "personal", model.user_id == user_id)
    elif scope == "project":
        return and_(model.scope == "project", model.project_id == project_id)
    return model.scope == scope


# ==================== Static routes FIRST (before /{skill_id}) ====================

@router.get("/capabilities")
async def skill_capabilities():
    """返回技能模块的能力声明"""
    return {
        "module": "skills",
        "version": "1.0.0",
        "capabilities": [
            {"name": "skill_list", "description": "List skills with filters"},
            {"name": "skill_create", "description": "Create a skill"},
            {"name": "skill_update", "description": "Update a skill"},
            {"name": "skill_delete", "description": "Delete a skill"},
            {"name": "skill_search", "description": "Search skills"},
            {"name": "skill_import", "description": "Import skill from URL"},
            {"name": "skill_review", "description": "Review a skill"},
            {"name": "skill_exec_config", "description": "Save execution config"},
        ]
    }


@router.get("/list")
async def list_skills(
    scope: str = Query("personal", description="global, personal, project"),
    project_id: Optional[int] = Query(None),
    group_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await check_scope_read_access(user, "skills", scope)
    user_id = get_current_user_id(user)
    query = select(Skill).where(Skill.deleted_at.is_(None))
    query = query.where(_scope_filter(Skill, scope, user_id, project_id))

    if group_id:
        query = query.where(Skill.group_id == group_id)
    if search:
        pattern = f"%{search}%"
        query = query.where(or_(Skill.name.ilike(pattern), Skill.description.ilike(pattern)))
    if tag:
        query = query.where(Skill.tags.like(f'%"%{tag}%"%'))

    total_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(total_query)
    total = total_result.scalar() or 0

    query = query.order_by(desc(Skill.updated_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    skills = result.scalars().all()

    return {"items": [s.to_dict() for s in skills], "scope": scope, "total": total, "count": len(skills)}


@router.get("/stats")
async def get_skills_stats(
    project_id: Optional[int] = Query(None),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await check_scope_read_access(user, "skills", "global")
    user_id = get_current_user_id(user)

    scope_conditions = or_(
        Skill.scope == "global",
        and_(Skill.scope == "personal", Skill.user_id == user_id),
        and_(Skill.scope == "project", Skill.project_id == project_id) if project_id else False
    )

    total = await db.execute(
        select(func.count(Skill.id)).where(and_(Skill.deleted_at.is_(None), scope_conditions))
    )

    by_scope = await db.execute(
        select(Skill.scope, func.count(Skill.id)).where(Skill.deleted_at.is_(None)).group_by(Skill.scope)
    )

    return {
        "total": total.scalar() or 0,
        "by_scope": {row[0]: row[1] for row in by_scope.all()}
    }


@router.get("/groups/list")
async def list_groups(
    scope: str = Query("personal"),
    project_id: Optional[int] = Query(None),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await check_scope_read_access(user, "skills", scope)
    user_id = get_current_user_id(user)
    query = select(SkillGroup).where(_scope_filter(SkillGroup, scope, user_id, project_id))
    query = query.order_by(SkillGroup.sort_order)
    result = await db.execute(query)
    groups = result.scalars().all()
    return {"items": [g.to_dict() for g in groups]}


@router.post("/groups/create")
async def create_group(
    data: SkillGroupCreate,
    project_id: Optional[int] = Query(None),
    user=require_permissions("skills:write:personal"),
    db: AsyncSession = Depends(get_db)
):
    user_id = get_current_user_id(user)
    group = SkillGroup(
        name=data.name, description=data.description, scope=data.scope,
        parent_id=data.parent_id, user_id=user_id if data.scope != "global" else None,
        project_id=project_id if data.scope == "project" else None
    )
    db.add(group)
    await db.commit()
    await db.refresh(group)
    return group.to_dict()


@router.delete("/groups/{group_id}")
async def delete_group(
    group_id: str,
    user=require_permissions("skills:write:personal"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(SkillGroup).where(SkillGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    await db.delete(group)
    await db.commit()
    return {"success": True}


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[str] = None


@router.put("/groups/{group_id}")
async def update_group(
    group_id: str,
    data: GroupUpdate,
    user=require_permissions("skills:write:personal"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(SkillGroup).where(SkillGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if data.name is not None:
        group.name = data.name
    if data.parent_id is not None:
        group.parent_id = data.parent_id
    await db.commit()
    await db.refresh(group)
    return group.to_dict()


@router.post("/create")
async def create_skill(
    data: SkillCreate,
    project_id: Optional[int] = Query(None),
    user=require_permissions("skills:write:personal"),
    db: AsyncSession = Depends(get_db)
):
    user_id = get_current_user_id(user)

    if data.scope == "project" and not project_id:
        raise HTTPException(status_code=400, detail="Project skill requires project_id")

    skill = Skill(
        name=data.name, description=data.description, scope=data.scope,
        instruction=data.instruction, content=data.content,
        tags=json.dumps(data.tags), exec_config=json.dumps(data.exec_config),
        dependencies=json.dumps(data.dependencies), weight_config=json.dumps(data.weight_config),
        examples=json.dumps(data.examples), group_id=data.group_id,
        source_type=data.source_type, source_url=data.source_url,
        user_id=user_id if data.scope != "global" else None,
        project_id=project_id if data.scope == "project" else None
    )
    db.add(skill)
    await db.commit()
    await db.refresh(skill)
    return skill.to_dict(include_content=True)


@router.post("/search")
async def search_skills(
    query: SkillSearchQuery,
    project_id: Optional[int] = Query(None),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await check_scope_read_access(user, "skills", query.scope or "global")
    user_id = get_current_user_id(user)
    search_pattern = f"%{query.query}%"

    conditions = [
        Skill.deleted_at.is_(None),
        or_(Skill.name.ilike(search_pattern), Skill.description.ilike(search_pattern))
    ]

    if query.scope:
        conditions.append(_scope_filter(Skill, query.scope, user_id, project_id))
    else:
        conditions.append(or_(
            Skill.scope == "global",
            and_(Skill.scope == "personal", Skill.user_id == user_id),
            and_(Skill.scope == "project", Skill.project_id == project_id) if project_id else False
        ))

    sql_query = select(Skill).where(and_(*conditions)).limit(query.top_k)
    result = await db.execute(sql_query)
    skills = result.scalars().all()

    return {
        "query": query.query,
        "total": len(skills),
        "results": [s.to_dict(include_content=True) for s in skills]
    }


# ==================== Parameterized routes AFTER static routes ====================

@router.get("/{skill_id}")
async def get_skill(
    skill_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Skill).where(and_(Skill.id == skill_id, Skill.deleted_at.is_(None)))
    )
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    await check_scope_read_access(user, "skills", skill.scope)

    skill.access_count += 1
    skill.last_accessed_at = datetime.now(timezone.utc)
    await db.commit()
    return skill.to_dict(include_content=True)


@router.put("/{skill_id}")
async def update_skill(
    skill_id: str,
    data: SkillUpdate,
    user=require_permissions("skills:write:personal"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Skill).where(and_(Skill.id == skill_id, Skill.deleted_at.is_(None)))
    )
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    update_fields = {
        'name': data.name, 'description': data.description,
        'instruction': data.instruction, 'content': data.content,
        'group_id': data.group_id, 'review_status': data.review_status,
        'promotion_status': data.promotion_status,
        'promotion_report': data.promotion_report,
        'promotion_source_id': data.promotion_source_id,
        'promotion_source_scope': data.promotion_source_scope,
    }
    json_fields = {
        'tags': data.tags, 'exec_config': data.exec_config,
        'dependencies': data.dependencies, 'weight_config': data.weight_config,
        'examples': data.examples
    }

    for field, value in update_fields.items():
        if value is not None:
            setattr(skill, field, value)
    for field, value in json_fields.items():
        if value is not None:
            setattr(skill, field, json.dumps(value))

    await db.commit()
    await db.refresh(skill)
    return skill.to_dict(include_content=True)


@router.delete("/{skill_id}")
async def delete_skill(
    skill_id: str,
    user=require_permissions("skills:write:personal"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Skill).where(and_(Skill.id == skill_id, Skill.deleted_at.is_(None)))
    )
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    skill.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return {"success": True, "message": "Skill deleted"}


@router.get("/{skill_id}/files")
async def get_skill_files(
    skill_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(SkillFile).where(SkillFile.skill_id == skill_id).order_by(SkillFile.sort_order)
    )
    files = result.scalars().all()
    return {"items": [f.to_dict() for f in files]}


@router.post("/{skill_id}/files")
async def save_skill_files(
    skill_id: str,
    files: List[SkillFileCreate],
    user=require_permissions("skills:write:personal"),
    db: AsyncSession = Depends(get_db)
):
    existing = await db.execute(
        select(SkillFile).where(SkillFile.skill_id == skill_id)
    )
    for f in existing.scalars().all():
        await db.delete(f)

    for file_data in files:
        sf = SkillFile(
            skill_id=skill_id, path=file_data.path, content=file_data.content,
            language=file_data.language, is_entry=file_data.is_entry,
            sort_order=file_data.sort_order
        )
        db.add(sf)

    await db.commit()
    return {"success": True, "count": len(files)}


@router.post("/{skill_id}/move")
async def move_skill(
    skill_id: str,
    group_id: Optional[str] = Query(None),
    scope: Optional[str] = Query(None),
    user=require_permissions("skills:write:personal"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Skill).where(and_(Skill.id == skill_id, Skill.deleted_at.is_(None)))
    )
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    if group_id is not None:
        skill.group_id = group_id
    if scope is not None:
        skill.scope = scope

    await db.commit()
    return skill.to_dict()


class ExecConfigUpdate(BaseModel):
    exec_config: dict = Field(...)


@router.post("/{skill_id}/exec-config")
async def save_exec_config(
    skill_id: str,
    data: ExecConfigUpdate,
    user=require_permissions("skills:write:personal"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Skill).where(and_(Skill.id == skill_id, Skill.deleted_at.is_(None)))
    )
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    skill.exec_config = json.dumps(data.exec_config)
    await db.commit()
    return {"success": True, "exec_config": data.exec_config}


class ReviewRequest(BaseModel):
    report: str = Field(..., min_length=1)
    status: str = Field("approved")
    log: List[str] = Field(default_factory=list)
    risk_patterns: List[str] = Field(default_factory=list)


@router.post("/{skill_id}/review")
async def review_skill(
    skill_id: str,
    data: ReviewRequest,
    user=require_permissions("skills:write:personal"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Skill).where(and_(Skill.id == skill_id, Skill.deleted_at.is_(None)))
    )
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    skill.review_status = data.status
    skill.review_report = data.report
    existing_log = json.loads(skill.review_log) if skill.review_log else []
    existing_log.append(datetime.now(timezone.utc).isoformat() + " - " + data.report[:100])
    skill.review_log = json.dumps(existing_log)
    if data.risk_patterns:
        skill.allow_risk_patterns = json.dumps(data.risk_patterns)
    await db.commit()
    return skill.to_dict(include_content=True)


class ImportFromUrlRequest(BaseModel):
    url: str = Field(..., min_length=1)
    name: Optional[str] = None
    scope: str = Field("personal")


@router.post("/import")
async def import_skill_from_url(
    data: ImportFromUrlRequest,
    project_id: Optional[int] = Query(None),
    user=require_permissions("skills:write:personal"),
    db: AsyncSession = Depends(get_db)
):
    """从 URL 导入技能"""
    import httpx
    user_id = get_current_user_id(user)
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(data.url, headers={"User-Agent": "AIDP-Skill-Import/1.0"})
            resp.raise_for_status()
            body = resp.text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch: {str(e)}")

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(body, "html.parser")
    title = soup.title.string.strip() if soup.title else data.name or "Imported Skill"
    for tag in soup(["script", "style", "nav", "footer", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)[:50000]

    skill = Skill(
        name=data.name or title[:200],
        description=f"Imported from {data.url}",
        instruction=text[:5000],
        content=text,
        scope=data.scope,
        source_type="web", source_url=data.url,
        user_id=user_id if data.scope != "global" else None,
        project_id=project_id if data.scope == "project" else None
    )
    db.add(skill)
    await db.commit()
    await db.refresh(skill)
    return skill.to_dict(include_content=True)


@router.get("/{skill_id}/package")
async def download_skill_package(
    skill_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    import io, tarfile, json
    result = await db.execute(select(Skill).where(and_(Skill.id == skill_id, Skill.deleted_at.is_(None))))
    skill = result.scalar_one_or_none()
    if not skill: raise HTTPException(status_code=404, detail="Skill not found")
    files_result = await db.execute(select(SkillFile).where(SkillFile.skill_id == skill_id))
    files = files_result.scalars().all()
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        sd = json.dumps({"name":skill.name,"description":skill.description,"instruction":skill.instruction,"content":skill.content,"tags":json.loads(skill.tags) if skill.tags else [],"exec_config":json.loads(skill.exec_config) if skill.exec_config else {},"version":skill.version}, ensure_ascii=False, indent=2)
        info = tarfile.TarInfo(name="skill.json"); info.size = len(sd.encode())
        tar.addfile(info, io.BytesIO(sd.encode()))
        for f in files:
            c = f.content or ""; info = tarfile.TarInfo(name=f.path); info.size = len(c.encode())
            tar.addfile(info, io.BytesIO(c.encode()))
    from fastapi.responses import Response
    return Response(content=buf.getvalue(), media_type="application/gzip", headers={"Content-Disposition": f'attachment; filename="{skill.name}.tar.gz"'})


@router.post("/upload")
async def upload_skill_package(
    file: bytes,
    user=require_permissions("skills:write:personal"),
    db: AsyncSession = Depends(get_db)
):
    import io, tarfile, json
    user_id = get_current_user_id(user)
    try:
        with tarfile.open(fileobj=io.BytesIO(file), mode="r:gz") as tar:
            members = tar.getmembers()
            sd = None; files = []
            for m in members:
                c = tar.extractfile(m).read().decode("utf-8") if m.isfile() else ""
                if m.name == "skill.json": sd = json.loads(c)
                else: files.append({"path": m.name, "content": c})
            if not sd: raise HTTPException(status_code=400, detail="skill.json not found")
            skill = Skill(name=sd.get("name","Imported"),description=sd.get("description"),instruction=sd.get("instruction"),content=sd.get("content"),tags=json.dumps(sd.get("tags",[])),exec_config=json.dumps(sd.get("exec_config",{})),version=sd.get("version",1),scope="personal",source_type="package",user_id=user_id)
            db.add(skill); await db.flush()
            for fd in files: db.add(SkillFile(skill_id=skill.id, path=fd["path"], content=fd["content"]))
            await db.commit(); await db.refresh(skill)
            return skill.to_dict(include_content=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid package: {str(e)}")


class EvolutionLogCreate(BaseModel):
    new_content: str = Field(..., min_length=1)
    old_content: Optional[str] = None
    diff_summary: Optional[str] = None
    trigger_reason: str = Field("manual")
    old_version: Optional[int] = None


@router.post("/{skill_id}/evolutions")
async def create_evolution(
    skill_id: str,
    data: EvolutionLogCreate,
    user=require_permissions("skills:write:personal"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Skill).where(and_(Skill.id == skill_id, Skill.deleted_at.is_(None))))
    skill = result.scalar_one_or_none()
    if not skill: raise HTTPException(status_code=404, detail="Skill not found")
    evo = SkillEvolution(
        skill_id=skill_id, old_version=data.old_version or skill.version,
        old_content=data.old_content, new_content=data.new_content,
        diff_summary=data.diff_summary, trigger_reason=data.trigger_reason, status="completed",
    )
    skill.version = (skill.version or 1) + 1
    db.add(evo); await db.commit(); await db.refresh(evo)
    return evo.to_dict()


@router.get("/{skill_id}/evolutions")
async def list_evolutions(
    skill_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(SkillEvolution).where(SkillEvolution.skill_id == skill_id)
        .order_by(desc(SkillEvolution.created_at)).limit(50)
    )
    return {"items": [e.to_dict() for e in result.scalars().all()]}

