from typing import Dict, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.tools.evolution_engine.db.models import EvolutionEvent


class EventCollector:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def collect(self, event_type: str, source: str, content: str = None, result: str = None, metadata: Optional[Dict] = None) -> EvolutionEvent:
        event = EvolutionEvent(
            event_type=event_type,
            source=source,
            content=content,
            result=result,
            metadata_=metadata or {},
            status="pending",
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def get_pending_events(self, limit: int = 10) -> list:
        result = await self.db.execute(
            select(EvolutionEvent).where(EvolutionEvent.status == "pending").limit(limit)
        )
        return result.scalars().all()

    async def get_event(self, event_id: int) -> Optional[EvolutionEvent]:
        result = await self.db.execute(
            select(EvolutionEvent).where(EvolutionEvent.id == event_id)
        )
        return result.scalar_one_or_none()

    async def mark_processed(self, event_id: int):
        result = await self.db.execute(
            select(EvolutionEvent).where(EvolutionEvent.id == event_id)
        )
        event = result.scalar_one_or_none()
        if event:
            event.status = "processed"
            await self.db.commit()

    async def collect_batch(self, events: list) -> list:
        collected = []
        for e in events:
            event = EvolutionEvent(
                event_type=e.get("type", "error"),
                source=e.get("source", "unknown"),
                content=e.get("content"),
                result=e.get("result"),
                metadata_=e.get("metadata", {}),
                status="pending",
            )
            self.db.add(event)
            collected.append(event)
        await self.db.commit()
        for event in collected:
            await self.db.refresh(event)
        return collected
