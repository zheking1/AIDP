from typing import Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import EvolutionEvent, EvolutionAnalysis, EvolutionUpdate


class StatsAnalyzer:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_stats(self) -> Dict:
        events_result = await self.db.execute(select(EvolutionEvent))
        all_events = events_result.scalars().all()

        total = len(all_events)
        error_events = sum(1 for e in all_events if e.event_type == "error")
        success_events = sum(1 for e in all_events if e.event_type == "success")
        opt_events = sum(1 for e in all_events if e.event_type == "optimization")

        analyses_result = await self.db.execute(select(EvolutionAnalysis))
        all_analyses = analyses_result.scalars().all()

        updates_result = await self.db.execute(select(EvolutionUpdate))
        all_updates = updates_result.scalars().all()

        by_tool = {}
        for u in all_updates:
            by_tool[u.target_tool] = by_tool.get(u.target_tool, 0) + 1

        return {
            "total_events": total,
            "error_events": error_events,
            "success_events": success_events,
            "optimization_events": opt_events,
            "total_updates": len(all_updates),
            "by_tool": by_tool,
        }
