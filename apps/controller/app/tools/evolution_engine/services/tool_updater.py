import logging
from typing import Dict, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.tools.evolution_engine.db.models import EvolutionUpdate

logger = logging.getLogger(__name__)


class ToolUpdater:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def update(self, analysis_id: int, target_tool: str, update_type: str) -> EvolutionUpdate:
        update = EvolutionUpdate(
            analysis_id=analysis_id,
            target_tool=target_tool,
            update_type=update_type,
            status="success",
        )
        self.db.add(update)
        await self.db.commit()
        await self.db.refresh(update)
        logger.info(f"Evolution update: {target_tool} <- {update_type}")
        return update

    async def apply_evolution(self, analysis_id: int, targets: List[str], update_type: str = "经验") -> List[EvolutionUpdate]:
        updates = []
        for target in targets:
            update = await self.update(
                analysis_id=analysis_id,
                target_tool=target,
                update_type=update_type,
            )
            updates.append(update)
        return updates
