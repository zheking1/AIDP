from typing import List, Dict, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.tools.memory_tool.db.models import MemoryEntry
from app.tools.memory_tool.services.privacy_filter import PrivacyFilter, sanitize
from app.tools.memory_tool.services.decay_scorer import DecayScorer
from app.tools.memory_tool.services.contradiction_detector import ContradictionDetector
from datetime import datetime, timedelta


class MemoryConsolidationService:
    TIERS = ["working", "episodic", "semantic", "procedural"]

    def __init__(self, db: AsyncSession):
        self.db = db
        self.privacy_filter = PrivacyFilter()
        self.decay_scorer = DecayScorer()
        self.contradiction_detector = ContradictionDetector()

    async def create_memory(self, title: str, content: str, project: str = None,
                           user_id: int = None, category: str = "general",
                           source_type: str = "manual", source_ref: str = None,
                           memory_tier: str = "episodic") -> Dict:
        content = sanitize(content)
        privacy_result = self.privacy_filter.filter(content)

        existing = await self.db.execute(
            select(MemoryEntry).where(
                MemoryEntry.project == project,
                MemoryEntry.deleted_at.is_(None)
            )
        )
        existing_memories = existing.scalars().all()
        contradictions = self.contradiction_detector.detect(title, content, existing_memories)

        entry = MemoryEntry(
            title=title,
            content=content,
            project=project or "default",
            user_id=user_id,
            category=category,
            source_type=source_type,
            source_ref=source_ref,
            memory_tier=memory_tier,
            confidence=1.0,
        )
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)

        return {
            "id": entry.id,
            "title": entry.title,
            "project": entry.project,
            "tier": entry.memory_tier,
            "privacy_findings": privacy_result.get("findings", []),
            "contradictions": contradictions,
        }

    async def get_memories(self, project: str = None, tier: str = None,
                          user_id: int = None, limit: int = 50) -> List[Dict]:
        query = select(MemoryEntry).where(MemoryEntry.deleted_at.is_(None))
        if project:
            query = query.where(MemoryEntry.project == project)
        if tier:
            query = query.where(MemoryEntry.memory_tier == tier)
        if user_id:
            query = query.where(MemoryEntry.user_id == user_id)
        query = query.order_by(MemoryEntry.updated_at.desc()).limit(limit)

        result = await self.db.execute(query)
        entries = result.scalars().all()

        memories = []
        for e in entries:
            days_since = (datetime.utcnow() - e.updated_at).days if e.updated_at else 0
            decay = self.decay_scorer.calculate_decay(e.access_count or 0, days_since)
            effective = self.decay_scorer.get_effective_importance(e.confidence or 1.0, decay)

            memories.append({
                "id": e.id,
                "title": e.title,
                "content": e.content,
                "project": e.project,
                "category": e.category,
                "tier": e.memory_tier,
                "source_type": e.source_type,
                "source_ref": e.source_ref,
                "confidence": e.confidence,
                "decay_score": decay,
                "effective_importance": effective,
                "access_count": e.access_count or 0,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            })

        return memories

    async def increment_access(self, memory_id: int):
        result = await self.db.execute(
            select(MemoryEntry).where(MemoryEntry.id == memory_id)
        )
        entry = result.scalar_one_or_none()
        if entry:
            entry.access_count = (entry.access_count or 0) + 1
            entry.last_accessed_at = datetime.utcnow()
            await self.db.commit()

    async def promote_tier(self, memory_id: int, new_tier: str) -> Optional[Dict]:
        result = await self.db.execute(
            select(MemoryEntry).where(MemoryEntry.id == memory_id)
        )
        entry = result.scalar_one_or_none()
        if entry and new_tier in self.TIERS:
            current_idx = self.TIERS.index(entry.memory_tier)
            new_idx = self.TIERS.index(new_tier)
            if new_idx > current_idx:
                entry.memory_tier = new_tier
                entry.parent_id = memory_id
                await self.db.commit()
                await self.db.refresh(entry)
                return {"id": entry.id, "tier": entry.memory_tier}
        return None

    async def delete_memory(self, memory_id: int):
        result = await self.db.execute(
            select(MemoryEntry).where(MemoryEntry.id == memory_id)
        )
        entry = result.scalar_one_or_none()
        if entry:
            entry.deleted_at = datetime.utcnow()
            await self.db.commit()
