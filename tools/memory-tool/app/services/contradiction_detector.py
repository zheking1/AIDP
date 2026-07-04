from typing import List, Dict, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import MemoryEntry


class ContradictionDetector:
    def detect(self, new_title: str, new_content: str, existing: List[MemoryEntry]) -> List[Dict]:
        contradictions = []
        new_keywords = set(new_content.lower().split()[:50])

        for mem in existing:
            existing_keywords = set(mem.content.lower().split()[:50])
            overlap = len(new_keywords & existing_keywords) / max(len(new_keywords), 1)

            if overlap > 0.6 and mem.title.lower() != new_title.lower():
                contradictions.append({
                    "memory_id": mem.id,
                    "title": mem.title,
                    "overlap_score": round(overlap, 3),
                    "potential_conflict": True,
                })

        return contradictions
