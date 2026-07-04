from typing import Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import DocPage, DocDrift


class DriftDetector:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def detect_drift(self, doc_id: int, code_changes: List[Dict]) -> List[DocDrift]:
        drifts = []
        for change in code_changes:
            doc = await self.db.execute(
                select(DocPage).where(DocPage.id == doc_id)
            )
            page = doc.scalar_one_or_none()
            if page and change.get("affected_sections"):
                for section in change["affected_sections"]:
                    drift = DocDrift(
                        doc_id=doc_id,
                        section_heading=section,
                        drift_score=change.get("score", 0.5),
                        status="detected",
                    )
                    self.db.add(drift)
                    drifts.append(drift)
        if drifts:
            await self.db.commit()
        return drifts

    async def get_drifts(self, doc_id: int) -> List[DocDrift]:
        result = await self.db.execute(
            select(DocDrift).where(
                DocDrift.doc_id == doc_id,
                DocDrift.status == "detected"
            ).order_by(DocDrift.detected_at.desc())
        )
        return result.scalars().all()
