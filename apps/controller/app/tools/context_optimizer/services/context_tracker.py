import hashlib
from typing import Optional, Dict, List
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.tools.context_optimizer.db.models import ContextRecord


class ContextTracker:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.sessions: Dict[str, List[str]] = {}

    async def add_content(self, session_id: str, content: str) -> int:
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].append(content)
        token_count = max(1, len(content) // 4)
        record = ContextRecord(
            session_id=session_id,
            content=content,
            token_count=token_count,
        )
        self.db.add(record)
        await self.db.commit()
        return token_count

    async def get_content(self, session_id: str) -> List[str]:
        if session_id in self.sessions:
            return self.sessions[session_id]
        result = await self.db.execute(
            select(ContextRecord).where(ContextRecord.session_id == session_id)
        )
        records = result.scalars().all()
        self.sessions[session_id] = [r.content for r in records]
        return self.sessions[session_id]

    async def get_total_tokens(self, session_id: str) -> int:
        content = await self.get_content(session_id)
        return sum(max(1, len(c) // 4) for c in content)

    async def is_duplicate(self, session_id: str, content: str, threshold: float = 0.8) -> bool:
        existing = self.sessions.get(session_id, [])
        for item in existing:
            if self._similarity(content, item) > threshold:
                return True
        return False

    def _similarity(self, a: str, b: str) -> float:
        a_set = set(a.split())
        b_set = set(b.split())
        if not a_set or not b_set:
            return 0.0
        intersection = a_set & b_set
        union = a_set | b_set
        return len(intersection) / len(union)
