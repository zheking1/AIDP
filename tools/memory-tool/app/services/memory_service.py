from typing import Optional
from sqlalchemy import select, func
from app.db.models import MemoryEntry, async_session
from app.config import settings


async def create_memory(
    project: str,
    category: str,
    title: str,
    content: str,
    tags: Optional[str] = None,
    pinned: bool = False,
    user_id: Optional[int] = None,
) -> dict:
    async with async_session() as session:
        entry = MemoryEntry(
            project=project,
            user_id=user_id,
            category=category,
            title=title,
            content=content,
            tags=tags,
            pinned=pinned,
        )
        session.add(entry)
        await session.commit()
        await session.refresh(entry)
        return _to_dict(entry)


async def search_memory(
    project: str,
    query: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    user_id: Optional[int] = None,
) -> list:
    async with async_session() as session:
        q = select(MemoryEntry).where(MemoryEntry.project == project)

        if category:
            q = q.where(MemoryEntry.category == category)
        if user_id:
            q = q.where(MemoryEntry.user_id == user_id)
        if query:
            q = q.where(
                MemoryEntry.title.ilike(f"%{query}%") |
                MemoryEntry.content.ilike(f"%{query}%") |
                MemoryEntry.tags.ilike(f"%{query}%")
            )

        q = q.order_by(MemoryEntry.pinned.desc(), MemoryEntry.id.desc()).limit(min(limit, settings.MEMORY_MAX_LIMIT))
        result = await session.execute(q)
        return [_to_dict(r) for r in result.scalars().all()]


async def get_memory(memory_id: int) -> Optional[dict]:
    async with async_session() as session:
        result = await session.execute(select(MemoryEntry).where(MemoryEntry.id == memory_id))
        entry = result.scalar_one_or_none()
        return _to_dict(entry) if entry else None


async def update_memory(memory_id: int, **kwargs) -> Optional[dict]:
    async with async_session() as session:
        result = await session.execute(select(MemoryEntry).where(MemoryEntry.id == memory_id))
        entry = result.scalar_one_or_none()
        if not entry:
            return None
        for key, value in kwargs.items():
            if hasattr(entry, key) and value is not None:
                setattr(entry, key, value)
        await session.commit()
        await session.refresh(entry)
        return _to_dict(entry)


async def delete_memory(memory_id: int) -> bool:
    async with async_session() as session:
        result = await session.execute(select(MemoryEntry).where(MemoryEntry.id == memory_id))
        entry = result.scalar_one_or_none()
        if not entry:
            return False
        await session.delete(entry)
        await session.commit()
        return True


async def get_context_package(project: str, query: str, limit: int = 10) -> dict:
    memories = await search_memory(project, query=query, limit=limit)
    return {
        "project": project,
        "query": query,
        "memories": memories,
        "count": len(memories),
    }


def _to_dict(entry: MemoryEntry) -> dict:
    return {
        "id": entry.id,
        "project": entry.project,
        "userId": entry.user_id,
        "category": entry.category,
        "title": entry.title,
        "content": entry.content,
        "tags": entry.tags,
        "pinned": entry.pinned,
        "createdAt": entry.created_at.isoformat() if entry.created_at else None,
        "updatedAt": entry.updated_at.isoformat() if entry.updated_at else None,
    }
