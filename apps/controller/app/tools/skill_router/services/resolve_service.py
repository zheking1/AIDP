import time
import uuid
import asyncio
from typing import Optional
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.skill_router.db.models import Skill, Rule
from app.tools.skill_router.services.cache_service import make_cache_key, get_cached, set_cache, get_session_cache, set_session_cache
from app.tools.skill_router.services.vector_service import generate_embedding, analyze_intent
from app.tools.skill_router.services.ranker_service import ranker_service
from app.tools.skill_router.config import settings


async def detect_cycle(skill_id: UUID, deps: list[UUID], visited: set = None, path: set = None) -> tuple[bool, list]:
    if visited is None:
        visited = set()
    if path is None:
        path = set()
    if skill_id in path:
        return True, list(path)
    if skill_id in visited:
        return False, []
    visited.add(skill_id)
    path.add(skill_id)
    for dep_id in deps:
        has_cycle, cycle_path = await detect_cycle(dep_id, [], visited, path)
        if has_cycle:
            return True, cycle_path
    path.discard(skill_id)
    return False, []


KEYWORD_WEIGHTS = {
    "programming|code|script|debug|bug|error|fix": 0.15,
    "api|rest|endpoint|route|graphql": 0.12,
    "database|sql|query|migration|schema": 0.12,
    "frontend|ui|react|vue|component|html|css": 0.10,
    "backend|server|service|middleware": 0.10,
    "deploy|docker|kubernetes|ci|cd|pipeline": 0.12,
    "security|auth|login|permission|encrypt": 0.15,
    "test|testing|unit|integration|e2e": 0.10,
    "data|analytics|ml|ai|pipeline|etl": 0.12,
    "financial|payment|accounting|invoice|billing": 0.08,
}


def compute_keyword_boost(task: str, skill_tags: list[str]) -> float:
    import re
    task_lower = task.lower()
    boost = 0.0
    for pattern, weight in KEYWORD_WEIGHTS.items():
        if re.search(pattern, task_lower):
            if skill_tags and any(t.lower() in pattern for t in skill_tags):
                boost = max(boost, weight)
    return boost


def compute_tag_score(tags_needed: list[str], skill_tags: list[str]) -> float:
    if not tags_needed or not skill_tags:
        return 0.0
    set_needed = set(t.lower() for t in tags_needed)
    set_skill = set(t.lower() for t in skill_tags)
    if not set_needed:
        return 0.0
    overlap = len(set_needed & set_skill)
    return overlap / len(set_needed)


async def resolve_skills(
    session: AsyncSession,
    task: str,
    user_id: UUID,
    mode: str = "auto",
    hint_tags: Optional[list] = None,
    top_k: int = 5,
    exclude_skill_ids: Optional[list] = None,
    exclude_tags: Optional[list] = None,
    role: Optional[str] = None,
) -> dict:
    # P0: 硬约束 Top 2-6，确保上下文不会过载
    top_k = max(2, min(top_k, 6))
    start = time.time()
    resolve_id = str(uuid.uuid4())
    degrade_info = {"degraded": False, "reason": ""}

    cache_key = make_cache_key(task, user_id, mode)
    cached = await get_cached(cache_key)
    if cached:
        return {**cached, "cache_hit": True, "cache_source": "request", "resolve_id": resolve_id}

    query_embedding_for_cache = None
    _sc = None  # session cache

    intent = None
    if mode in ("auto", "llm_only"):
        intent = await analyze_intent(task)
        if intent is None:
            if mode == "auto":
                degrade_info = {"degraded": True, "reason": "llm_timeout -> embedding_only"}
                mode = "embedding_only"
            else:
                degrade_info = {"degraded": True, "reason": "llm_timeout -> tag_only"}
                mode = "tag_only"

    query_embedding = None
    if mode in ("auto", "embedding_only"):
        query_embedding = await generate_embedding(task)
        if query_embedding is None:
            degrade_info = {"degraded": True, "reason": "embedding_fail -> tag_only"}
            mode = "tag_only"
        else:
            sc = await get_session_cache(str(user_id), query_embedding)
            if sc:
                return {**sc, "cache_hit": True, "cache_source": "session", "resolve_id": resolve_id, "session_cache_hit": True}

    tags_needed = (intent or {}).get("tags_needed", hint_tags or [])
    tag_filter = tags_needed or hint_tags or []

    base_skill = select(Skill).options(joinedload(Skill.project)).where(Skill.is_active == True).where(
        (Skill.user_id == user_id) | (Skill.scope == "public")
    )

    if exclude_skill_ids:
        base_skill = base_skill.where(~Skill.id.in_(exclude_skill_ids))
    if exclude_tags:
        for tag in exclude_tags:
            base_skill = base_skill.where(~Skill.tags.any(tag))

    # Count skills before permission filtering for permission_filtered metric
    # Include tag_filter to match the same base as post-permission count
    pre_permission_count = 0
    if role:
        count_query = select(Skill.id).where(Skill.is_active == True).where(
            (Skill.user_id == user_id) | (Skill.scope == "public")
        )
        if exclude_skill_ids:
            count_query = count_query.where(~Skill.id.in_(exclude_skill_ids))
        if exclude_tags:
            for tag in exclude_tags:
                count_query = count_query.where(~Skill.tags.any(tag))
        # Include tag_filter for accurate permission-only diff
        if mode == "tag_only" and tag_filter:
            from sqlalchemy import or_
            ors = [Skill.tags.any(t) for t in tag_filter]
            count_query = count_query.where(or_(*ors))
        elif query_embedding:
            count_query = count_query.where(Skill.embedding.isnot(None))
        count_result = await session.execute(count_query)
        pre_permission_count = len(count_result.scalars().all())

    if role:
        base_skill = base_skill.where(
            (Skill.allowed_roles.is_(None)) | (Skill.allowed_roles.any(role))
        )

    if mode == "tag_only":
        if tag_filter:
            from sqlalchemy import or_
            ors = [Skill.tags.any(t) for t in tag_filter]
            base_skill = base_skill.where(or_(*ors))
        base_skill = base_skill.order_by(Skill.updated_at.desc()).limit(top_k * 3)
        result = await session.execute(base_skill)
        skills = [(s, 0.0) for s in result.scalars().all()]
    elif query_embedding:
        emb_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
        
        async def fetch_skills():
            skill_sql = base_skill.add_columns(
                (1 - Skill.embedding.cosine_distance(text(f"'{emb_str}'::vector"))).label("vec_score")
            ).where(
                Skill.embedding.isnot(None)
            ).order_by(text("vec_score DESC")).limit(top_k * 2)
            skill_rows = await session.execute(skill_sql)
            return [(row[0], float(row[1] or 0)) for row in skill_rows]
        
        async def fetch_rules():
            rule_sql = select(Rule).where(Rule.is_active == True, Rule.embedding.isnot(None)).where(
                (Rule.user_id == user_id) | (Rule.scope == "public")
            )
            if role:
                rule_sql = rule_sql.where(
                    (Rule.allowed_roles.is_(None)) | (Rule.allowed_roles.any(role))
                )
            rule_sql = rule_sql.add_columns(
                (1 - Rule.embedding.cosine_distance(text(f"'{emb_str}'::vector"))).label("vec_score")
            ).order_by(text("vec_score DESC")).limit(top_k * 2)
            rule_rows = await session.execute(rule_sql)
            return [(row[0], float(row[1] or 0)) for row in rule_rows]
        
        skills_future = asyncio.create_task(fetch_skills())
        rules_future = asyncio.create_task(fetch_rules())
        
        skills = await skills_future
        rules = await rules_future
    else:
        result = await session.execute(base_skill.order_by(Skill.updated_at.desc()).limit(top_k * 3))
        skills = [(s, 0.0) for s in result.scalars().all()]
        rules = []

    if not query_embedding:
        rule_sql = select(Rule).where(Rule.is_active == True).where(
            (Rule.user_id == user_id) | (Rule.scope == "public")
        )
        if role:
            rule_sql = rule_sql.where(
                (Rule.allowed_roles.is_(None)) | (Rule.allowed_roles.any(role))
            )
        rule_sql = rule_sql.order_by(Rule.priority.desc()).limit(top_k * 2)
        rule_rows = await session.execute(rule_sql)
        rules = [(r, 0.0) for r in rule_rows.scalars().all()]

    seen_content = set()
    skill_list = []
    for s, vec_score in skills[:top_k]:
        tag_score = compute_tag_score(tags_needed, s.tags or [])
        kw_boost = compute_keyword_boost(task, s.tags or [])
        dep_boost = 0.0
        if s.dependencies:
            dep_boost = 0.05

        final_score = (vec_score * 0.6) + (tag_score * 0.3) + kw_boost + dep_boost

        content_key = s.content[:100]
        if content_key in seen_content:
            continue
        seen_content.add(content_key)

        _, cycle_path = await detect_cycle(s.id, s.dependencies or [])
        has_cycle = len(cycle_path) > 0

        skill_list.append({
            "id": str(s.id),
            "name": s.name,
            "content": s.content,
            "score": round(final_score, 4),
            "score_detail": {
                "vector_score": round(vec_score, 4),
                "tag_score": round(tag_score, 4),
                "keyword_boost": round(kw_boost, 4),
                "dep_boost": dep_boost,
                "final_score": round(final_score, 4),
            },
            "version": s.version,
            "tags": s.tags or [],
            "sensitive": getattr(s, "sensitive", False),
            "instruction": s.instruction or None,
            "project_instruction": (s.project.instruction if s.project and s.project.instruction else None),
            "review_status": s.review_status,
            "dependencies": [str(d) for d in (s.dependencies or [])],
            "has_cycle_dep": has_cycle,
        })

    rule_list = []
    for r, vec_score in rules[:top_k]:
        tag_score = compute_tag_score(tags_needed, r.tags or [])
        final_score = (vec_score * 0.6) + (tag_score * 0.3)
        rule_list.append({
            "id": str(r.id),
            "name": r.name,
            "content": r.content,
            "score": round(final_score, 4),
            "score_detail": {
                "vector_score": round(vec_score, 4),
                "tag_score": round(tag_score, 4),
                "final_score": round(final_score, 4),
            },
            "priority": r.priority,
        })

    rerank_result = await ranker_service.rerank(session, task, skill_list)
    if rerank_result:
        id_to_score = {r["id"]: r.get("score", r.get("relevance", 0.5)) for r in rerank_result}
        id_to_primary = {r["id"]: r.get("is_primary", True) for r in rerank_result}
        for s in skill_list:
            rr_score = id_to_score.get(s["id"], 0.3)
            is_primary = id_to_primary.get(s["id"], True)
            vec = s["score_detail"]["vector_score"]
            tag = s["score_detail"]["tag_score"]
            kw = s["score_detail"].get("keyword_boost", 0)
            s["score_detail"]["rerank_score"] = round(rr_score, 4)
            s["score_detail"]["is_primary"] = is_primary
            # Compound intent: weight primary skills higher (P1优化)
            if intent and intent.get("is_compound"):
                if is_primary:
                    # Primary技能：70%权重预算
                    # 给primary技能更高的权重，确保其绝对分数更高
                    s["score"] = round((vec * 0.35) + (tag * 0.15) + (kw * 0.05) + (rr_score * 0.45), 4)
                    s["score_detail"]["weight_budget"] = "primary_70%"
                else:
                    # Secondary技能：30%权重预算
                    # 给secondary技能较低的权重，确保其绝对分数相对较小
                    s["score"] = round((vec * 0.20) + (tag * 0.10) + (kw * 0.05) + (rr_score * 0.15), 4)
                    s["score_detail"]["weight_budget"] = "secondary_30%"
            else:
                s["score"] = round((vec * 0.4) + (tag * 0.2) + (kw * 0.1) + (rr_score * 0.3), 4)
            s["score_detail"]["final_score"] = s["score"]
        skill_list.sort(key=lambda x: x["score"], reverse=True)

    # For compound intent, ensure secondary skills are included (not just top_k primary)
    if intent and intent.get("is_compound"):
        primary_skills = [s for s in skill_list if s["score_detail"].get("is_primary", True)]
        secondary_skills = [s for s in skill_list if not s["score_detail"].get("is_primary", True)]
        # Keep top primary + up to 2 secondary
        skill_list = primary_skills[:max(2, top_k - 2)] + secondary_skills[:2]
    else:
        skill_list = skill_list[:top_k]

    rule_list.sort(key=lambda x: x["priority"], reverse=True)

    elapsed = int((time.time() - start) * 1000)

    cache_source = "request"
    ranker_used = rerank_result is not None
    rule_boosts_applied = []
    for pat, wt in KEYWORD_WEIGHTS.items():
        import re
        if re.search(pat, task.lower()):
            rule_boosts_applied.append({"pattern": pat[:30], "weight": wt})

    # Count skills after role filter but before tag filter and top_k limit
    post_permission_count = 0
    if role:
        count_query = select(Skill.id).where(Skill.is_active == True).where(
            (Skill.user_id == user_id) | (Skill.scope == "public")
        ).where(
            (Skill.allowed_roles.is_(None)) | (Skill.allowed_roles.any(role))
        )
        if exclude_skill_ids:
            count_query = count_query.where(~Skill.id.in_(exclude_skill_ids))
        if exclude_tags:
            for tag in exclude_tags:
                count_query = count_query.where(~Skill.tags.any(tag))
        if mode == "tag_only" and tag_filter:
            from sqlalchemy import or_
            ors = [Skill.tags.any(t) for t in tag_filter]
            count_query = count_query.where(or_(*ors))
        elif query_embedding:
            count_query = count_query.where(Skill.embedding.isnot(None))
        count_result = await session.execute(count_query)
        post_permission_count = len(count_result.scalars().all())

    permission_filtered = max(0, pre_permission_count - post_permission_count) if role else 0

    output = {
        "intent_analysis": intent or {
            "intent": "", "domain": "",
            "tags_needed": tags_needed or [],
            "complexity": "unknown",
        },
        "skills": [{**s, "match_score": s["score"], "require_approval": s.get("sensitive", False)} for s in skill_list],
        "rules": rule_list,
        "cache_hit": False,
        "cache_source": cache_source,
        "meta": {
            "cache_source": cache_source,
            "latency_ms": elapsed,
            "resolve_id": resolve_id,
            "degrade_info": degrade_info,
            "ranker_used": ranker_used,
            "rule_boosts_applied": rule_boosts_applied,
            "permission_filtered": permission_filtered,
            "mode": mode,
            "top_k": top_k,
        },
    }

    if query_embedding:
        await set_session_cache(str(user_id), query_embedding, output)
    await set_cache(cache_key, output)
    
    # P4增强：记录详细的操作日志
    from app.tools.skill_router.db.models import OperationLog
    log = OperationLog(
        user_id=user_id,
        resource_type="resolve",
        action="resolve",
        detail={
            "task": task[:200],  # 截断避免过长
            "mode": mode,
            "skills_count": len(skill_list),
            "rules_count": len(rule_list),
            "latency_ms": elapsed,
            "cache_hit": False,
            "cache_source": cache_source,
            "degrade_info": degrade_info,
            "ranker_used": ranker_used,
            "permission_filtered": permission_filtered,
            "resolve_id": resolve_id,
            "matched_skill_ids": [s["id"] for s in skill_list[:3]],  # 只记录前3个
            "matched_rule_ids": [r["id"] for r in rule_list[:3]],
        },
        trace_id=resolve_id,
    )
    session.add(log)
    await session.commit()
    
    from app.tools.skill_router.services.validation_service import validate_resolve_result
    return validate_resolve_result(output)


async def resolve_task(
    task: str,
    mode: str = "auto",
    hint_tags: list = None,
    request_id: str = None,
    role: str = None,
    user_id: Optional[UUID] = None,
) -> dict:
    from app.tools.skill_router.db.init_db import get_session
    async with get_session() as session:
        result = await resolve_skills(
            session=session,
            task=task,
            user_id=user_id or uuid.UUID(int=1),
            mode=mode,
            hint_tags=hint_tags,
            role=role,
        )
    result["request_id"] = request_id
    return result
