from typing import Optional
from uuid import UUID

import bcrypt
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.skill_router.db.models import Skill, Rule


async def create_skill(
    session: AsyncSession,
    user_id: UUID,
    name: str,
    content: str,
    tags: Optional[list] = None,
    dependencies: Optional[list] = None,
) -> Skill:
    skill = Skill(
        name=name,
        content=content,
        tags=tags or [],
        user_id=user_id,
        dependencies=[UUID(d) for d in dependencies] if dependencies else [],
    )
    session.add(skill)
    await session.commit()
    await session.refresh(skill)
    return skill


SKILL_UPDATE_FIELDS = {"name", "description", "content", "tags", "review_status", "review_report", "is_active", "dependencies"}


async def update_skill(session: AsyncSession, skill_id: UUID, name: str = None, description: str = None, content: str = None, tags: list = None, review_status: str = None, review_report: str = None, is_active: bool = None, dependencies: list = None) -> Optional[Skill]:
    skill = await session.get(Skill, skill_id)
    if not skill:
        return None
    updates = {"name": name, "description": description, "content": content, "tags": tags, "review_status": review_status, "review_report": review_report, "is_active": is_active, "dependencies": dependencies}
    for k, v in updates.items():
        if v is not None:
            if k == "dependencies" and v:
                v = [UUID(d) for d in v]
            setattr(skill, k, v)
    await session.commit()
    await session.refresh(skill)
    return skill


async def delete_skill(session: AsyncSession, skill_id: UUID) -> bool:
    skill = await session.get(Skill, skill_id)
    if not skill:
        return False
    await session.delete(skill)
    await session.commit()
    return True


async def get_skill(session: AsyncSession, skill_id: UUID) -> Optional[Skill]:
    return await session.get(Skill, skill_id)


async def list_skills(
    session: AsyncSession,
    user_id: UUID,
    tags: Optional[list] = None,
    status: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Skill], int]:
    stmt = select(Skill).where(Skill.user_id == user_id, Skill.is_active == True)

    if tags:
        stmt = stmt.where(Skill.tags.overlap(tags))
    if status:
        stmt = stmt.where(Skill.review_status == status)
    if query:
        stmt = stmt.where(
            or_(
                Skill.name.ilike(f"%{query}%"),
                Skill.content.ilike(f"%{query}%"),
            )
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await session.scalar(count_stmt)

    stmt = stmt.order_by(Skill.updated_at.desc()).offset(offset).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all(), total or 0
