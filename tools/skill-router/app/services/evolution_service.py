from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Evolution, Skill, Rule

EVOLUTION_STATUSES = ("pending", "applied", "rejected", "rolled_back")
TARGET_TYPES = ("skill", "rule")


async def submit_evolution(
    session: AsyncSession,
    user_id: UUID,
    target_id: UUID,
    target_type: str,
    new_content: str,
    trigger_reason: str,
) -> Evolution:
    target_type = target_type.lower()
    if target_type == "skill":
        target = await session.get(Skill, target_id)
    else:
        target = await session.get(Rule, target_id)

    if not target:
        raise ValueError(f"{target_type} not found: {target_id}")

    old_content = target.content
    old_version = target.version

    target.content = new_content
    target.version += 1

    evolution = Evolution(
        target_type=target_type,
        target_id=target_id,
        target_name=target.name,
        old_version=old_version,
        old_content=old_content,
        new_content=new_content,
        trigger_reason=trigger_reason,
        status="applied",
        user_id=user_id,
    )
    session.add(evolution)
    await session.commit()
    await session.refresh(evolution)
    return evolution


async def rollback_evolution(
    session: AsyncSession,
    evolution_id: UUID,
    trigger_reason: str,
) -> Evolution:
    evo = await session.get(Evolution, evolution_id)
    if not evo:
        raise ValueError(f"evolution not found: {evolution_id}")

    if evo.target_type == "skill":
        target = await session.get(Skill, evo.target_id)
    else:
        target = await session.get(Rule, evo.target_id)

    if not target:
        raise ValueError(f"{evo.target_type} not found: {evo.target_id}")

    old_content = target.content
    old_version = target.version

    target.content = evo.old_content
    target.version += 1

    new_evo = Evolution(
        target_type=evo.target_type,
        target_id=evo.target_id,
        target_name=evo.target_name,
        old_version=old_version,
        old_content=old_content,
        new_content=evo.old_content,
        trigger_reason=trigger_reason,
        status="rolled_back",
        user_id=evo.user_id,
        rollback_to=evolution_id,
    )
    session.add(new_evo)
    await session.commit()
    await session.refresh(new_evo)
    return new_evo


async def list_evolutions(
    session: AsyncSession,
    user_id: UUID,
    target_id: Optional[UUID] = None,
    target_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Evolution], int]:
    stmt = select(Evolution).where(Evolution.user_id == user_id)
    if target_id:
        stmt = stmt.where(Evolution.target_id == target_id)
    if target_type:
        stmt = stmt.where(Evolution.target_type == target_type)
    if status:
        stmt = stmt.where(Evolution.status == status)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await session.scalar(count_stmt)

    stmt = stmt.order_by(Evolution.created_at.desc()).offset(offset).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all(), total or 0
