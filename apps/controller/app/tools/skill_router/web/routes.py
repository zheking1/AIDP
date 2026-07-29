import uuid
from datetime import datetime, timezone

import bcrypt
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select, func, update, text

from app.tools.skill_router.db.init_db import get_session
from app.tools.skill_router.db.models import (
    Skill, SkillFile, Rule, Evolution, LLMConfig, OperationLog, ResolveCache, User, Project,
    SkillPermission, ROLES,
)
from app.tools.skill_router.services.resolve_service import resolve_task
from app.tools.skill_router.web.i18n_utils import render_template
from sqlalchemy.orm import selectinload
from app.tools.skill_router.config import settings

router = APIRouter()


async def _user_id_from_session(user: dict, db=None) -> uuid.UUID:
    try:
        return uuid.UUID(user.get("id", ""))
    except (ValueError, AttributeError):
        if db:
            from app.tools.skill_router.config import settings
            from app.tools.skill_router.db.models import User
            result = await db.execute(select(User).where(User.username == settings.admin_username))
            admin = result.scalar_one_or_none()
            if admin:
                return admin.id
        return uuid.UUID(int=1)


@router.get("/skills")
async def skills_page(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)
    async with get_session() as db:
        user = request.session["user"]
        user_id = await _user_id_from_session(user, db=db)
        q = select(Skill).options(selectinload(Skill.files)).where(
            (Skill.user_id == user_id) | (Skill.scope == "public")
        ).order_by(Skill.updated_at.desc())
        result = await db.execute(q)
        skills = result.scalars().all()
        # Load groups for group tree
        from app.tools.skill_router.db.models import SkillGroup
        groups_result = await db.execute(
            select(SkillGroup).where(SkillGroup.user_id == user_id).order_by(SkillGroup.sort_order)
        )
        groups = [g.to_dict() for g in groups_result.scalars().all()]
        groups_map = {g["id"]: g["name"] for g in groups}
        skills_data = []
        for s in skills:
            d = s.to_dict()
            # 排除 embedding 字段，避免 numpy ndarray 无法 JSON 序列化
            d.pop("embedding", None)
            d["group_name"] = groups_map.get(str(d.get("group_id")), "")
            skills_data.append(d)
    return render_template("skills/list.html", request, skills=skills_data, groups=groups)


@router.get("/skills/create")
async def skill_create_page(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)
    return render_template("skills/form.html", request, skill=None, groups=[])


@router.post("/skills/create")
async def skill_create(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)
    form = await request.form()
    tags = [t.strip() for t in form.get("tags", "").split(",") if t.strip()]
    allowed = form.get("allowed_roles", "")
    allowed_roles = [r.strip() for r in allowed.split(",") if r.strip()] if allowed else None
    scope = form.get("scope", "private")
    sensitive = form.get("sensitive") == "on"
    instruction = form.get("instruction", "").strip() or None
    async with get_session() as db:
        user = request.session["user"]
        user_id = await _user_id_from_session(user, db=db)
        # Check name uniqueness
        name = form["name"].strip()
        existing = await db.execute(select(Skill).where(Skill.user_id == user_id, Skill.name == name))
        if existing.scalar_one_or_none():
            return HTMLResponse(f'<script>alert("{_("Skill name already exists")}");history.back()</script>', status_code=200)
        group_id = form.get("group_id") or None
        skill = Skill(name=name, tags=tags, content=form["content"], version=1, review_status="pending", user_id=user_id, allowed_roles=allowed_roles, scope=scope, sensitive=sensitive, instruction=instruction, group_id=group_id)
        db.add(skill)
        await db.commit()
    return RedirectResponse(url="/skills", status_code=302)


def _parse_skill_id(skill_id: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(skill_id)
    except (ValueError, AttributeError):
        return None


# ------ Skill Import (must be before {skill_id} route) ------

@router.get("/skills/import")
async def skill_import_page(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    # Get user's skill groups
    try:
        from app.tools.skill_router.db.models import SkillGroup
        from sqlalchemy import select as sa_select
        async with get_session() as db:
            user_id = uuid.UUID(user["id"])
            result = await db.execute(
                sa_select(SkillGroup).where(SkillGroup.user_id == user_id).order_by(SkillGroup.name)
            )
            groups = [{"id": str(g.id), "name": g.name} for g in result.scalars().all()]
    except Exception:
        groups = []

    return render_template("skills/import.html", request, groups=groups)


@router.get("/skills/{skill_id}")
async def skill_detail(request: Request, skill_id: str):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)
    uid = _parse_skill_id(skill_id)
    if not uid:
        return HTMLResponse("Invalid ID", status_code=400)
    async with get_session() as db:
        result = await db.execute(select(Skill).options(selectinload(Skill.files)).where(Skill.id == uid))
        skill = result.scalars().first()
        if not skill:
            return HTMLResponse("Not found", status_code=404)
        skill_data = skill.to_dict()
        if not skill_data.get("content") and skill_data.get("files"):
            entry = next((f for f in skill_data["files"] if f.get("is_entry")), skill_data["files"][0])
            skill_data["content"] = entry["content"]
    return render_template("skills/detail.html", request, skill=skill_data, is_admin=_is_admin(request.session.get("user", {})))


@router.post("/skills/{skill_id}/publish")
async def skill_publish(request: Request, skill_id: str):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)
    if not _is_admin(request.session["user"]):
        return HTMLResponse("Forbidden", status_code=403)
    uid = _parse_skill_id(skill_id)
    if not uid:
        return HTMLResponse("Invalid ID", status_code=400)
    form = await request.form()
    scope = form.get("scope", "public")
    async with get_session() as db:
        result = await db.execute(select(Skill).where(Skill.id == uid))
        skill = result.scalars().first()
        if not skill:
            return HTMLResponse("Not found", status_code=404)
        skill.scope = scope
        await db.commit()
    return RedirectResponse(url=f"/skills/{skill_id}", status_code=302)


@router.post("/skills/{skill_id}/copy")
async def skill_copy(request: Request, skill_id: str):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)
    uid = _parse_skill_id(skill_id)
    if not uid:
        return HTMLResponse("Invalid ID", status_code=400)
    async with get_session() as db:
        result = await db.execute(select(Skill).options(selectinload(Skill.files)).where(Skill.id == uid))
        orig = result.scalars().first()
        if not orig:
            return HTMLResponse("Not found", status_code=404)
        if orig.scope != "public":
            return HTMLResponse("Not a public skill", status_code=400)
        user = request.session["user"]
        user_id = await _user_id_from_session(user, db=db)
        copy = Skill(
            name=orig.name + " (copy)", tags=orig.tags, content=orig.content,
            version=1, review_status="pending", scope="private",
            user_id=user_id, allowed_roles=orig.allowed_roles,
            exec_config=orig.exec_config
        )
        db.add(copy)
        await db.flush()
        for f in orig.files:
            db.add(SkillFile(
                skill_id=copy.id, path=f.path, content=f.content,
                language=f.language, is_entry=f.is_entry, sort_order=f.sort_order
            ))
        await db.commit()
    return RedirectResponse(url=f"/skills/{copy.id}", status_code=302)


@router.get("/skills/{skill_id}/edit")
async def skill_edit_page(request: Request, skill_id: str):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)
    uid = _parse_skill_id(skill_id)
    if not uid:
        return HTMLResponse("Invalid ID", status_code=400)
    async with get_session() as db:
        result = await db.execute(select(Skill).options(selectinload(Skill.files)).where(Skill.id == uid))
        skill = result.scalars().first()
        if not skill:
            return HTMLResponse("Not found", status_code=404)
        skill_data = skill.to_dict()
        if not skill_data.get("content") and skill_data.get("files"):
            entry = next((f for f in skill_data["files"] if f.get("is_entry")), skill_data["files"][0])
            skill_data["content"] = entry["content"]
        # Load groups
        from app.tools.skill_router.db.models import SkillGroup
        user_id = await _user_id_from_session(request.session["user"], db=db)
        groups_result = await db.execute(
            select(SkillGroup).where(SkillGroup.user_id == user_id).order_by(SkillGroup.sort_order)
        )
        groups = [g.to_dict() for g in groups_result.scalars().all()]
    return render_template("skills/form.html", request, skill=skill_data, groups=groups)


@router.post("/skills/{skill_id}/edit")
async def skill_edit(request: Request, skill_id: str):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)
    uid = _parse_skill_id(skill_id)
    if not uid:
        return HTMLResponse("Invalid ID", status_code=400)
    form = await request.form()
    tags = [t.strip() for t in form.get("tags", "").split(",") if t.strip()]
    async with get_session() as db:
        skill = await db.get(Skill, uid)
        if skill:
            skill.name = form["name"]
            skill.tags = tags
            skill.content = form["content"]
            skill.version += 1
            allowed = form.get("allowed_roles", "")
            skill.allowed_roles = [r.strip() for r in allowed.split(",") if r.strip()] if allowed else None
            skill.scope = form.get("scope", skill.scope)
            instruction = form.get("instruction", "").strip()
            skill.instruction = instruction or None
            examples = form.get("examples", "")
            skill.examples = [e.strip() for e in examples.split("\n") if e.strip()] if examples else []
            group_id = form.get("group_id") or None
            skill.group_id = group_id
            await db.commit()
    return RedirectResponse(url=f"/skills/{skill_id}", status_code=302)


@router.get("/skills/{skill_id}/review")
async def skill_review(request: Request, skill_id: str):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)
    uid = _parse_skill_id(skill_id)
    if not uid:
        return HTMLResponse("Invalid ID", status_code=400)
    async with get_session() as db:
        skill = await db.get(Skill, uid)
        if not skill:
            return HTMLResponse("Not found", status_code=404)
        skill_data = skill.to_dict()
    return render_template("skills/review.html", request, skill=skill_data, review=None, error=None)


@router.post("/skills/{skill_id}/review")
async def skill_review_run(request: Request, skill_id: str):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)
    uid = _parse_skill_id(skill_id)
    if not uid:
        return HTMLResponse("Invalid ID", status_code=400)
    async with get_session() as db:
        skill = await db.get(Skill, uid)
        if not skill:
            return HTMLResponse("Not found", status_code=404)
        from app.tools.skill_router.services.review_service import run_review
        try:
            result = await run_review(db, uid)
            skill_data = skill.to_dict()
            return render_template("skills/review.html", request, skill=skill_data, review=result, error=None)
        except Exception as e:
            skill_data = skill.to_dict()
            return render_template("skills/review.html", request, skill=skill_data, review=None, error=str(e))


@router.post("/skills/{skill_id}/delete")
async def skill_delete(request: Request, skill_id: str):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)
    async with get_session() as db:
        skill = await db.get(Skill, uuid.UUID(skill_id))
        if skill:
            from sqlalchemy import delete as sa_delete
            await db.execute(sa_delete(SkillFile).where(SkillFile.skill_id == uuid.UUID(skill_id)))
            await db.delete(skill)
            await db.commit()
    return RedirectResponse(url="/skills", status_code=302)


@router.get("/skills/{skill_id}/package")
async def skill_download_package(request: Request, skill_id: str):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)
    uid = _parse_skill_id(skill_id)
    if not uid:
        return HTMLResponse("Invalid ID", status_code=400)
    from app.tools.skill_router.api.routes import api_download_package
    return await api_download_package(str(uid))


@router.get("/rules")
async def rules_page(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)
    async with get_session() as db:
        user = request.session["user"]
        user_id = await _user_id_from_session(user, db=db)
        result = await db.execute(select(Rule).where(Rule.user_id == user_id).order_by(Rule.priority.desc()))
        rules = result.scalars().all()
        from app.tools.skill_router.db.models import RuleGroup
        groups_result = await db.execute(
            select(RuleGroup).where(RuleGroup.user_id == user_id).order_by(RuleGroup.sort_order)
        )
        groups = [g.to_dict() for g in groups_result.scalars().all()]
        groups_map = {g["id"]: g["name"] for g in groups}
        rules_data = []
        for r in rules:
            d = r.to_dict()
            d["group_name"] = groups_map.get(str(d.get("group_id")), "")
            rules_data.append(d)
    return render_template("rules/list.html", request, rules=rules_data, groups=groups)


@router.get("/rules/create")
async def rule_create_page(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)
    return render_template("rules/form.html", request, rule=None)


@router.post("/rules/create")
async def rule_create(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)
    form = await request.form()
    tags = [t.strip() for t in form.get("tags", "").split(",") if t.strip()]
    user = request.session["user"]
    async with get_session() as db:
        user_id = await _user_id_from_session(user, db=db)
        # Check name uniqueness
        name = form["name"].strip()
        existing = await db.execute(select(Rule).where(Rule.user_id == user_id, Rule.name == name))
        if existing.scalar_one_or_none():
            return HTMLResponse(f'<script>alert("{_("Rule name already exists")}");history.back()</script>', status_code=200)
        rule = Rule(name=name, tags=tags, content=form["content"], priority=int(form.get("priority", 0)), user_id=user_id)
        db.add(rule)
        await db.commit()
    return RedirectResponse(url="/rules", status_code=302)


@router.get("/rules/{rule_id}")
async def rule_detail(request: Request, rule_id: str):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)
    async with get_session() as db:
        rule = await db.get(Rule, uuid.UUID(rule_id))
        if not rule:
            return HTMLResponse("Not found", status_code=404)
    return render_template("rules/detail.html", request, rule=rule.to_dict())


@router.get("/rules/{rule_id}/edit")
async def rule_edit_page(request: Request, rule_id: str):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)
    async with get_session() as db:
        rule = await db.get(Rule, uuid.UUID(rule_id))
        if not rule:
            return HTMLResponse("Not found", status_code=404)
    return render_template("rules/form.html", request, rule=rule.to_dict())


@router.post("/rules/{rule_id}/edit")
async def rule_edit(request: Request, rule_id: str):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)
    form = await request.form()
    tags = [t.strip() for t in form.get("tags", "").split(",") if t.strip()]
    async with get_session() as db:
        rule = await db.get(Rule, uuid.UUID(rule_id))
        if rule:
            rule.name = form["name"]
            rule.tags = tags
            rule.content = form["content"]
            rule.priority = int(form.get("priority", 0))
            await db.commit()
    return RedirectResponse(url=f"/rules/{rule_id}", status_code=302)


@router.post("/rules/{rule_id}/delete")
async def rule_delete(request: Request, rule_id: str):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)
    async with get_session() as db:
        rule = await db.get(Rule, uuid.UUID(rule_id))
        if rule:
            await db.delete(rule)
            await db.commit()
    return RedirectResponse(url="/rules", status_code=302)


@router.get("/evolutions")
async def evolutions_page(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)
    async with get_session() as db:
        result = await db.execute(select(Evolution).order_by(Evolution.created_at.desc()).limit(100))
        evolutions = result.scalars().all()
    return render_template("evolutions/list.html", request, evolutions=[e.to_dict() for e in evolutions])


@router.get("/models")
async def models_page(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)
    async with get_session() as db:
        user_id = await _user_id_from_session(request.session["user"], db=db)
        result = await db.execute(select(LLMConfig).where(LLMConfig.user_id == user_id).order_by(LLMConfig.name))
        models = result.scalars().all()
    return render_template("models/list.html", request, models=[m.to_dict() for m in models])


@router.get("/models/create")
async def model_create_page(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)
    return render_template("models/form.html", request, model=None)


@router.post("/models/create")
async def model_create(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)
    form = await request.form()
    user = request.session["user"]
    async with get_session() as db:
        user_id = await _user_id_from_session(user, db=db)
        # Check name uniqueness
        name = form["name"].strip()
        existing = await db.execute(select(LLMConfig).where(LLMConfig.user_id == user_id, LLMConfig.name == name))
        if existing.scalar_one_or_none():
            return HTMLResponse(f'<script>alert("{_("Model name already exists")}");history.back()</script>', status_code=200)
        llm = LLMConfig(
            name=name,
            endpoint=form["endpoint"],
            api_key=form.get("api_key", ""),
            model_name=form.get("model_name", ""),
            role=form.get("role", "intent_analyzer"),
            temperature=float(form.get("temperature", 0.7)),
            max_tokens=int(form.get("max_tokens", 2048)),
            timeout_secs=int(form.get("timeout_secs", 30)),
            is_default=form.get("is_default") == "true",
            is_healthy=True,
            user_id=user_id,
        )
        db.add(llm)
        await db.commit()
    return RedirectResponse(url="/models", status_code=302)


@router.get("/models/{model_id}/edit")
async def model_edit_page(request: Request, model_id: str):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)
    async with get_session() as db:
        result = await db.execute(select(LLMConfig).where(LLMConfig.id == uuid.UUID(model_id)))
        llm = result.scalars().first()
        if not llm:
            return HTMLResponse("Not found", status_code=404)
    return render_template("models/form.html", request, model=llm.to_dict())


@router.post("/models/{model_id}/edit")
async def model_edit(request: Request, model_id: str):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)
    form = await request.form()
    user = request.session["user"]
    async with get_session() as db:
        result = await db.execute(select(LLMConfig).where(LLMConfig.id == uuid.UUID(model_id)))
        llm = result.scalars().first()
        if llm:
            llm.name = form["name"]
            llm.endpoint = form["endpoint"]
            llm.api_key = form.get("api_key", llm.api_key)
            llm.model_name = form.get("model_name", llm.model_name)
            llm.role = form.get("role", llm.role)
            llm.temperature = float(form.get("temperature", llm.temperature))
            llm.max_tokens = int(form.get("max_tokens", llm.max_tokens))
            llm.timeout_secs = int(form.get("timeout_secs", llm.timeout_secs))
            llm.is_default = form.get("is_default") == "true"
            if form.get("is_default") == "true":
                await db.execute(
                    update(LLMConfig).where(
                        LLMConfig.role == llm.role, LLMConfig.id != llm.id
                    ).values(is_default=False)
                )
            await db.commit()
    return RedirectResponse(url="/models", status_code=302)


@router.post("/models/{model_id}/delete")
async def model_delete(request: Request, model_id: str):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)
    async with get_session() as db:
        llm = await db.get(LLMConfig, uuid.UUID(model_id))
        if llm:
            await db.delete(llm)
            await db.commit()
    return RedirectResponse(url="/models", status_code=302)


@router.get("/resolve")
async def resolve_page(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)
    return render_template("resolve/index.html", request, result=None)


@router.post("/resolve")
async def resolve_post(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)
    form = await request.form()
    task_desc = form.get("task", "")
    mode = form.get("mode", "auto")
    hint_tags = [t.strip() for t in form.get("hint_tags", "").split(",") if t.strip()]
    request_id = str(datetime.now(timezone.utc).timestamp())
    user = request.session["user"]
    user_id = await _user_id_from_session(user)
    from app.tools.skill_router.services.rate_limiter import check_rate_limit
    allowed, reason = await check_rate_limit(str(user_id))
    if not allowed:
        t = get_translator(request.session.get("lang", "zh"))
        return render_template("resolve/index.html", request, result={"error": t("Rate limit exceeded"), "limit_reason": reason})
    session_id = request.session.get("id", "") or str(user_id)
    result = await resolve_task(task=task_desc, mode=mode, hint_tags=hint_tags or None, request_id=request_id, user_id=user_id)
    result["session_context"] = {"session_id": session_id, "task": task_desc}
    return render_template("resolve/index.html", request, result=result)


@router.get("/cache")
async def cache_page(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)
    from app.tools.skill_router.services.cache_service import get_redis
    r = await get_redis()
    hash_keys = 0
    session_keys = 0
    try:
        _, hk = await r.scan(match="*")
        hash_keys = len(hk)
        _, sk = await r.scan(match="session_cache:*")
        session_keys = len(sk)
    except: pass
    return render_template("cache/index.html", request, stats={
        "total_keys": hash_keys, "session_keys": session_keys,
        "hit_rate": 0, "memory_usage": 0
    })


@router.post("/cache/flush")
async def cache_flush(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)
    form = await request.form()
    key_hash = form.get("key_hash", "").strip()
    target = form.get("target", "all")
    from app.tools.skill_router.services.cache_service import delete_cache, clear_session_cache
    if target == "session":
        user = request.session["user"]
        await clear_session_cache(str(user["id"]))
    elif target == "all":
        await delete_cache(pattern="*")
    elif key_hash:
        await delete_cache(key_hash=key_hash)
    else:
        await delete_cache(pattern="*")
    return RedirectResponse(url="/cache", status_code=302)


@router.get("/stats")
async def stats_page(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)
    async with get_session() as db:
        resolve_count = (await db.execute(select(func.count()).select_from(OperationLog).where(OperationLog.action == "resolve"))).scalar() or 0
        cache_hits = (await db.execute(select(func.count()).select_from(OperationLog).where(OperationLog.action == "cache_hit"))).scalar() or 0
        total_logs = resolve_count + cache_hits or 1
        cache_hit_rate = cache_hits / total_logs
        llm_fails = (await db.execute(select(func.count()).select_from(OperationLog).where(OperationLog.action == "llm_fail"))).scalar() or 0
        llm_fail_rate = llm_fails / total_logs if total_logs else 0
        
        total_skills = (await db.execute(select(func.count()).select_from(Skill))).scalar() or 0
        total_rules = (await db.execute(select(func.count()).select_from(Rule))).scalar() or 0
        approved_skills = (await db.execute(select(func.count()).select_from(Skill).where(Skill.review_status == "approved"))).scalar() or 0
        
        from app.tools.skill_router.services.cache_service import get_cache_statistics
        cache_stats = await get_cache_statistics()
        
        from app.tools.skill_router.services.rate_limiter import check_system_load
        system_load = await check_system_load()
    
    return render_template("stats/index.html", request, stats={
        "resolve_count": resolve_count,
        "cache_hit_rate": cache_hit_rate,
        "llm_fail_rate": llm_fail_rate,
        "avg_latency_ms": 0,
        "mode_distribution": {"auto": 0, "embedding_only": 0, "llm_only": 0},
        "top_skills": [],
        "top_rules": [],
        "total_skills": total_skills,
        "total_rules": total_rules,
        "approved_skills": approved_skills,
        "cache_stats": cache_stats,
        "system_load": system_load,
    })


@router.get("/logs")
async def logs_page(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)
    async with get_session() as db:
        result = await db.execute(select(OperationLog).order_by(OperationLog.created_at.desc()).limit(200))
        logs = result.scalars().all()
    return render_template("logs/list.html", request, logs=[l.to_dict() for l in logs])


# ------ User Management (admin only) ------

def _is_admin(user: dict) -> bool:
    return user.get("role") == "admin" or user.get("username") == settings.admin_username


@router.get("/users")
async def users_page(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    if not _is_admin(user):
        return HTMLResponse("Forbidden", status_code=403)
    async with get_session() as db:
        result = await db.execute(select(User).order_by(User.created_at))
        users = result.scalars().all()
    return render_template("users/list.html", request, users=[u.to_dict() for u in users])


@router.get("/users/create")
async def user_create_page(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    if not _is_admin(user):
        return HTMLResponse("Forbidden", status_code=403)
    return render_template("users/form.html", request, user_data=None)


@router.post("/users/create")
async def user_create(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    if not _is_admin(user):
        return HTMLResponse("Forbidden", status_code=403)
    form = await request.form()
    username = form.get("username", "").strip()
    password = form.get("password", "")
    role = form.get("role", "user")
    nickname = form.get("nickname", "").strip()
    remark = form.get("remark", "").strip()
    if not username or not password:
        return render_template("users/form.html", request, user_data=None, error="Username and password required")
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    async with get_session() as db:
        existing = await db.execute(select(User).where(User.username == username))
        if existing.scalar_one_or_none():
            return render_template("users/form.html", request, user_data=None, error="Username already exists")
        new_user = User(username=username, password=hashed, role=role, nickname=nickname, remark=remark)
        db.add(new_user)
        await db.commit()
    return RedirectResponse(url="/users", status_code=302)


@router.get("/users/{user_id}/edit")
async def user_edit_page(request: Request, user_id: str):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    if not _is_admin(user):
        return HTMLResponse("Forbidden", status_code=403)
    async with get_session() as db:
        target = await db.get(User, uuid.UUID(user_id))
        if not target:
            return HTMLResponse("Not found", status_code=404)
    return render_template("users/form.html", request, user_data=target.to_dict())


@router.post("/users/{user_id}/edit")
async def user_edit(request: Request, user_id: str):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    if not _is_admin(user):
        return HTMLResponse("Forbidden", status_code=403)
    form = await request.form()
    async with get_session() as db:
        target = await db.get(User, uuid.UUID(user_id))
        if not target:
            return HTMLResponse("Not found", status_code=404)
        target.username = form.get("username", target.username)
        target.role = form.get("role", target.role)
        target.nickname = form.get("nickname", target.nickname or "")
        target.remark = form.get("remark", target.remark or "")
        pwd = form.get("password", "")
        if pwd:
            target.password = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()
        await db.commit()
    return RedirectResponse(url="/users", status_code=302)


@router.post("/users/{user_id}/delete")
async def user_delete(request: Request, user_id: str):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    if not _is_admin(user):
        return HTMLResponse("Forbidden", status_code=403)
    if user.get("id") == user_id:
        return HTMLResponse("Cannot delete yourself", status_code=400)
    async with get_session() as db:
        target = await db.get(User, uuid.UUID(user_id))
        if target:
            await db.delete(target)
            await db.commit()
    return RedirectResponse(url="/users", status_code=302)


@router.post("/users/{user_id}/toggle-active")
async def user_toggle_active(request: Request, user_id: str):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    if not _is_admin(user):
        return HTMLResponse("Forbidden", status_code=403)
    if user.get("id") == user_id:
        return HTMLResponse("Cannot disable yourself", status_code=400)
    async with get_session() as db:
        target = await db.get(User, uuid.UUID(user_id))
        if target:
            target.is_active = not target.is_active
            await db.commit()
    return RedirectResponse(url="/users", status_code=302)


# ------ API Key Management ------
@router.get("/api-keys")
async def api_keys_page(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    async with get_session() as db:
        from app.tools.skill_router.db.models import ApiKey
        result = await db.execute(select(ApiKey).where(ApiKey.user_id == uuid.UUID(user["id"]), ApiKey.is_active == True))
        keys = result.scalars().all()
    return render_template("api_keys/list.html", request, keys=[{"id": str(k.id), "label": k.label, "created_at": str(k.created_at.date()) if k.created_at else "", "last_used": str(k.last_used.date()) if k.last_used else "-"} for k in keys], new_key=request.query_params.get("new_key", ""))


@router.post("/api-keys/create")
async def api_key_create(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    import hashlib, secrets
    form = await request.form()
    label = form.get("label", "").strip() or "default"
    raw_key = "sk-" + secrets.token_hex(24)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    async with get_session() as db:
        from app.tools.skill_router.db.models import ApiKey
        ak = ApiKey(user_id=uuid.UUID(user["id"]), key_hash=key_hash, label=label)
        db.add(ak)
        await db.commit()
    return RedirectResponse(url=f"/api-keys?new_key={raw_key}", status_code=302)


@router.post("/api-keys/{key_id}/revoke")
async def api_key_revoke(request: Request, key_id: str):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    async with get_session() as db:
        from app.tools.skill_router.db.models import ApiKey
        ak = await db.get(ApiKey, uuid.UUID(key_id))
        if ak and str(ak.user_id) == user["id"]:
            ak.is_active = False
            await db.commit()
    return RedirectResponse(url="/api-keys", status_code=302)


@router.get("/profile")
async def profile_page(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    async with get_session() as db:
        from app.tools.skill_router.db.models import User, ApiKey
        u = await db.get(User, uuid.UUID(user["id"]))
        if not u:
            return HTMLResponse("Not found", status_code=404)
        key_count = (await db.execute(select(func.count()).select_from(ApiKey).where(ApiKey.user_id == u.id, ApiKey.is_active == True))).scalar() or 0
        skill_count = (await db.execute(select(func.count()).select_from(Skill).where(Skill.user_id == u.id))).scalar() or 0
    return render_template("profile.html", request, u=u.to_dict(), key_count=key_count, skill_count=skill_count)


# ------ Project Management ------

def _get_user_id(request: Request) -> str:
    return request.session.get("user", {}).get("id", "")


@router.get("/projects")
async def projects_page(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    async with get_session() as db:
        result = await db.execute(
            select(Project).where(Project.user_id == uuid.UUID(_get_user_id(request))).order_by(Project.created_at)
        )
        projects = result.scalars().all()
    return render_template("projects/list.html", request, projects=[p.to_dict() for p in projects])


@router.get("/projects/create")
async def project_create_page(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)
    return render_template("projects/form.html", request, project=None)


import re

@router.post("/projects/create")
async def project_create(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    form = await request.form()
    name = form.get("name", "").strip()
    if not name:
        return render_template("projects/form.html", request, project=None, error="Name required")
    slug = re.sub(r"[^a-zA-Z0-9-_]+", "-", name.lower()).strip("-")
    async with get_session() as db:
        inst = form.get("instruction", "").strip() or None
        p = Project(
            user_id=uuid.UUID(_get_user_id(request)),
            name=name,
            slug=slug,
            title=name,
            description=form.get("description", ""),
            instruction=inst,
        )
        db.add(p)
        await db.commit()
        pid = p.id
    return RedirectResponse(url=f"/projects/{pid}", status_code=302)


@router.get("/projects/{project_id}")
async def project_detail(request: Request, project_id: str):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    async with get_session() as db:
        p = await db.get(Project, uuid.UUID(project_id))
        if not p:
            return HTMLResponse("Not found", status_code=404)
        skills = (await db.execute(
            select(Skill).where(Skill.project_id == uuid.UUID(project_id)).order_by(Skill.created_at)
        )).scalars().all()
        rules = (await db.execute(
            select(Rule).where(Rule.project_id == uuid.UUID(project_id)).order_by(Rule.created_at)
        )).scalars().all()
        # Available skills/rules not linked to this project (user's own + public)
        user_id = uuid.UUID(user["id"])
        available_skills = (await db.execute(
            select(Skill).where(Skill.is_active == True).where(
                (Skill.user_id == user_id) | (Skill.scope == "public")
            ).where(~Skill.id.in_([s.id for s in skills]) if skills else True).order_by(Skill.name)
        )).scalars().all()
        available_rules = (await db.execute(
            select(Rule).where(Rule.is_active == True).where(
                (Rule.user_id == user_id) | (Rule.scope == "public")
            ).where(~Rule.id.in_([r.id for r in rules]) if rules else True).order_by(Rule.name)
        )).scalars().all()
    return render_template("projects/detail.html", request, project=p.to_dict(),
                           skills=[s.to_dict() for s in skills], rules=[r.to_dict() for r in rules],
                           available_skills=[s.to_dict() for s in available_skills],
                           available_rules=[r.to_dict() for r in available_rules])


@router.post("/projects/{project_id}/skills/link")
async def project_link_skill(request: Request, project_id: str):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    form = await request.form()
    skill_id = form.get("skill_id")
    if not skill_id:
        return RedirectResponse(url=f"/projects/{project_id}", status_code=302)
    async with get_session() as db:
        skill = await db.get(Skill, uuid.UUID(skill_id))
        if skill:
            skill.project_id = uuid.UUID(project_id)
            await db.commit()
    return RedirectResponse(url=f"/projects/{project_id}", status_code=302)


@router.post("/projects/{project_id}/skills/{skill_id}/unlink")
async def project_unlink_skill(request: Request, project_id: str, skill_id: str):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    async with get_session() as db:
        skill = await db.get(Skill, uuid.UUID(skill_id))
        if skill and str(skill.project_id) == project_id:
            skill.project_id = None
            await db.commit()
    return RedirectResponse(url=f"/projects/{project_id}", status_code=302)


@router.post("/projects/{project_id}/rules/link")
async def project_link_rule(request: Request, project_id: str):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    form = await request.form()
    rule_id = form.get("rule_id")
    if not rule_id:
        return RedirectResponse(url=f"/projects/{project_id}", status_code=302)
    async with get_session() as db:
        rule = await db.get(Rule, uuid.UUID(rule_id))
        if rule:
            rule.project_id = uuid.UUID(project_id)
            await db.commit()
    return RedirectResponse(url=f"/projects/{project_id}", status_code=302)


@router.post("/projects/{project_id}/rules/{rule_id}/unlink")
async def project_unlink_rule(request: Request, project_id: str, rule_id: str):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    async with get_session() as db:
        rule = await db.get(Rule, uuid.UUID(rule_id))
        if rule and str(rule.project_id) == project_id:
            rule.project_id = None
            await db.commit()
    return RedirectResponse(url=f"/projects/{project_id}", status_code=302)


@router.get("/projects/{project_id}/edit")
async def project_edit_page(request: Request, project_id: str):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    async with get_session() as db:
        p = await db.get(Project, uuid.UUID(project_id))
        if not p:
            return HTMLResponse("Not found", status_code=404)
    return render_template("projects/form.html", request, project=p.to_dict())


@router.post("/projects/{project_id}/edit")
async def project_edit(request: Request, project_id: str):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    form = await request.form()
    async with get_session() as db:
        p = await db.get(Project, uuid.UUID(project_id))
        if not p:
            return HTMLResponse("Not found", status_code=404)
        p.name = form.get("name", p.name)
        p.description = form.get("description", p.description)
        inst = form.get("instruction", "").strip()
        p.instruction = inst or None
        await db.commit()
    return RedirectResponse(url=f"/projects/{project_id}", status_code=302)


@router.post("/projects/{project_id}/delete")
async def project_delete(request: Request, project_id: str):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    async with get_session() as db:
        p = await db.get(Project, uuid.UUID(project_id))
        if not p:
            return HTMLResponse("Not found", status_code=404)
        # unlink before delete
        await db.execute(
            text("UPDATE skills SET project_id=NULL WHERE project_id=:pid"),
            {"pid": uuid.UUID(project_id)},
        )
        await db.execute(
            text("UPDATE rules SET project_id=NULL WHERE project_id=:pid"),
            {"pid": uuid.UUID(project_id)},
        )
        await db.execute(
            text("UPDATE llm_configs SET project_id=NULL WHERE project_id=:pid"),
            {"pid": uuid.UUID(project_id)},
        )
        await db.delete(p)
        await db.commit()
    return RedirectResponse(url="/projects", status_code=302)


# ------ Permission Management (admin only) ------

@router.get("/permissions")
async def permissions_page(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    if not _is_admin(user):
        return HTMLResponse("Forbidden", status_code=403)
    async with get_session() as db:
        skills_result = await db.execute(select(Skill).order_by(Skill.name))
        skills = skills_result.scalars().all()
        
        perms_result = await db.execute(select(SkillPermission))
        perms = perms_result.scalars().all()
        perms_map = {str(p.skill_id): p for p in perms}
        
        permissions = []
        for s in skills:
            p = perms_map.get(str(s.id))
            permissions.append({
                "skill_id": str(s.id),
                "skill_name": s.name,
                "permission_id": str(p.id) if p else None,
                "allowed_roles": p.allowed_roles if p else None,
                "denied_roles": p.denied_roles if p else None,
            })
    
    return render_template("permissions/list.html", request, permissions=permissions)


@router.get("/permissions/{skill_id}/edit")
async def permission_edit_page(request: Request, skill_id: str):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    if not _is_admin(user):
        return HTMLResponse("Forbidden", status_code=403)
    async with get_session() as db:
        skill = await db.get(Skill, uuid.UUID(skill_id))
        if not skill:
            return HTMLResponse("Skill not found", status_code=404)
        
        perm_result = await db.execute(
            select(SkillPermission).where(SkillPermission.skill_id == uuid.UUID(skill_id))
        )
        permission = perm_result.scalar_one_or_none()
    
    return render_template("permissions/form.html", request, skill=skill.to_dict(), permission=permission.to_dict() if permission else None, roles=ROLES)


@router.post("/permissions/{skill_id}/edit")
async def permission_edit(request: Request, skill_id: str):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    if not _is_admin(user):
        return HTMLResponse("Forbidden", status_code=403)
    form = await request.form()
    
    allowed_roles = form.getlist("allowed_roles")
    denied_roles = form.getlist("denied_roles")
    
    if allowed_roles and denied_roles:
        conflict = set(allowed_roles) & set(denied_roles)
        if conflict:
            async with get_session() as db:
                skill = await db.get(Skill, uuid.UUID(skill_id))
            return render_template("permissions/form.html", request, skill=skill.to_dict(), permission=None, roles=ROLES, 
                                   error=f"Roles cannot be both allowed and denied: {', '.join(conflict)}")
    
    async with get_session() as db:
        perm_result = await db.execute(
            select(SkillPermission).where(SkillPermission.skill_id == uuid.UUID(skill_id))
        )
        permission = perm_result.scalar_one_or_none()
        
        if permission:
            permission.allowed_roles = allowed_roles if allowed_roles else None
            permission.denied_roles = denied_roles if denied_roles else None
        else:
            permission = SkillPermission(
                skill_id=uuid.UUID(skill_id),
                allowed_roles=allowed_roles if allowed_roles else None,
                denied_roles=denied_roles if denied_roles else None,
            )
            db.add(permission)
        await db.commit()
    
    return RedirectResponse(url="/permissions", status_code=302)


@router.post("/permissions/{skill_id}/delete")
async def permission_delete(request: Request, skill_id: str):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    if not _is_admin(user):
        return HTMLResponse("Forbidden", status_code=403)
    async with get_session() as db:
        perm_result = await db.execute(
            select(SkillPermission).where(SkillPermission.skill_id == uuid.UUID(skill_id))
        )
        permission = perm_result.scalar_one_or_none()
        if permission:
            await db.delete(permission)
            await db.commit()
    return RedirectResponse(url="/permissions", status_code=302)


# ------ System Settings ------

@router.get("/settings")
async def settings_page(request: Request):
    user = request.session.get("user")
    if not user or not (user.get("role") == "admin" or user.get("username") == settings.admin_username):
        return RedirectResponse(url="/login", status_code=302)
    from app.tools.skill_router.web.settings_utils import get_all_settings
    s = get_all_settings()
    return render_template("settings/index.html", request, settings=s)


@router.post("/settings")
async def settings_save(request: Request):
    user = request.session.get("user")
    if not user or not (user.get("role") == "admin" or user.get("username") == settings.admin_username):
        return RedirectResponse(url="/login", status_code=302)
    form = await request.form()
    from app.tools.skill_router.web.settings_utils import set_setting
    set_setting("allow_registration", form.get("allow_registration") == "on")
    return RedirectResponse(url="/settings", status_code=302)

    return render_template("skills/import.html", request, groups=groups)
