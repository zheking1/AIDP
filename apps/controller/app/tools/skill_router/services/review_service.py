import re
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.skill_router.db.models import ReviewPattern, Skill


async def get_active_patterns(session: AsyncSession) -> list[ReviewPattern]:
    result = await session.execute(
        select(ReviewPattern).where(ReviewPattern.is_active == True)
    )
    return result.scalars().all()


async def static_scan(content: str, patterns: list[ReviewPattern]) -> list[dict]:
    hits = []
    for p in patterns:
        if re.search(p.pattern, content, re.IGNORECASE):
            hits.append({
                "pattern_id": str(p.id),
                "name": p.name,
                "risk_level": p.risk_level,
                "matched": True,
            })
    return hits


async def pre_review(
    session: AsyncSession,
    content: str,
    allow_risk_patterns: Optional[list] = None,
) -> dict:
    patterns = await get_active_patterns(session)
    hits = await static_scan(content, patterns)
    allowed = set(allow_risk_patterns or [])
    filtered_hits = [h for h in hits if h["pattern_id"] not in allowed]
    pass_scan = len(filtered_hits) == 0
    return {
        "static_hits": filtered_hits,
        "pass": pass_scan,
    }


async def run_review(session: AsyncSession, skill_id: UUID) -> dict:
    skill = await session.get(Skill, skill_id)
    if not skill:
        raise ValueError(f"skill not found: {skill_id}")

    result = await pre_review(session, skill.content, skill.allow_risk_patterns)

    high_risk = any(h["risk_level"] in ("high", "critical") for h in result["static_hits"])
    if high_risk:
        skill.review_status = "rejected"
    elif result["pass"]:
        skill.review_status = "approved"
    else:
        skill.review_status = "pending"

    skill.review_report = str(result)
    await session.commit()
    return {"review_status": skill.review_status, "hits": result["static_hits"]}
