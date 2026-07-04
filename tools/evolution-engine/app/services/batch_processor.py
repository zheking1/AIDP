from typing import Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.pattern_analyzer import PatternAnalyzer
from app.services.llm_pattern_analyzer import LLMPatternAnalyzer
from app.services.evolution_router import EvolutionRouter
from app.services.tool_updater import ToolUpdater
from app.db.models import EvolutionEvent, EvolutionAnalysis, EvolutionUpdate


class BatchProcessor:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm_analyzer = LLMPatternAnalyzer(db)
        self.router = EvolutionRouter()
        self.updater = ToolUpdater(db)

    async def process_batch(self, events: List[Dict]) -> Dict:
        analyses = []
        updates = []
        for event_data in events:
            event = await self._create_event(event_data)
            if event:
                analysis = await self._analyze_event(event)
                if analysis:
                    analyses.append(analysis)
                    targets = self.router.route(analysis)
                    update_list = await self.updater.apply_evolution(
                        analysis["id"], targets, analysis.get("update_type", "经验")
                    )
                    updates.extend(update_list)

        return {
            "processed": len(analyses),
            "analyses": analyses,
            "updates": len(updates),
        }

    async def _create_event(self, data: Dict):
        from app.db.models import EvolutionEvent
        event = EvolutionEvent(
            event_type=data.get("type", "error"),
            source=data.get("source", "unknown"),
            content=data.get("content"),
            result=data.get("result"),
            metadata_=data.get("metadata", {}),
            status="pending",
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def _analyze_event(self, event: EvolutionEvent) -> Optional[Dict]:
        analyzer = LLMPatternAnalyzer(self.db)
        analysis = await analyzer.analyze(
            event.event_type, event.content or "", event.result, event.metadata_
        )
        analysis["id"] = event.id
        return analysis
