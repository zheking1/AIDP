from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.skill_router.db.models import Rule


async def create_rule(
    session: AsyncSession,
    user_id: UUID,
    name: str,
    content: str,
    tags: Optional[list] = None,
    priority: int = 0,
) -> Rule:
    rule = Rule(
        name=name,
        content=content,
        tags=tags or [],
        priority=priority,
        user_id=user_id,
    )
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    return rule


RULE_UPDATE_FIELDS = {"name", "content", "tags", "priority", "is_active"}


async def update_rule(session: AsyncSession, rule_id: UUID, name: str = None, content: str = None, tags: list = None, priority: int = None, is_active: bool = None) -> Optional[Rule]:
    rule = await session.get(Rule, rule_id)
    if not rule:
        return None
    updates = {"name": name, "content": content, "tags": tags, "priority": priority, "is_active": is_active}
    for k, v in updates.items():
        if v is not None:
            setattr(rule, k, v)
    await session.commit()
    await session.refresh(rule)
    return rule


async def delete_rule(session: AsyncSession, rule_id: UUID) -> bool:
    rule = await session.get(Rule, rule_id)
    if not rule:
        return False
    await session.delete(rule)
    await session.commit()
    return True


async def get_rule(session: AsyncSession, rule_id: UUID) -> Optional[Rule]:
    return await session.get(Rule, rule_id)


async def list_rules(
    session: AsyncSession,
    user_id: UUID,
    tags: Optional[list] = None,
    query: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Rule], int]:
    stmt = select(Rule).where(Rule.user_id == user_id, Rule.is_active == True)

    if tags:
        stmt = stmt.where(Rule.tags.overlap(tags))
    if query:
        stmt = stmt.where(
            or_(Rule.name.ilike(f"%{query}%"), Rule.content.ilike(f"%{query}%"))
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await session.scalar(count_stmt)

    stmt = stmt.order_by(Rule.priority.desc(), Rule.updated_at.desc()).offset(offset).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all(), total or 0
