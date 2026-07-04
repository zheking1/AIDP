import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import CacheEntry
from app.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, query: str) -> Optional[Dict]:
        if not settings.CACHE_ENABLED:
            return None
        query_hash = hashlib.sha256(query.encode()).hexdigest()[:64]
        result = await self.db.execute(
            select(CacheEntry).where(CacheEntry.query_hash == query_hash)
        )
        entry = result.scalar_one_or_none()
        if entry and entry.expires_at and entry.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            await self.db.delete(entry)
            await self.db.commit()
            return None
        if entry:
            return entry.result
        return None

    async def set(self, query: str, result: Dict, tokens: int):
        if not settings.CACHE_ENABLED:
            return
        query_hash = hashlib.sha256(query.encode()).hexdigest()[:64]
        ttl = timedelta(seconds=settings.CACHE_TTL)
        expires_at = datetime.now(timezone.utc) + ttl
        entry = CacheEntry(
            query_hash=query_hash,
            query=query,
            result=result,
            tokens=tokens,
            expires_at=expires_at,
        )
        existing = await self.db.execute(
            select(CacheEntry).where(CacheEntry.query_hash == query_hash)
        )
        old = existing.scalar_one_or_none()
        if old:
            old.result = result
            old.tokens = tokens
            old.expires_at = expires_at
        else:
            self.db.add(entry)
        await self.db.commit()

    async def cleanup(self):
        now = datetime.now(timezone.utc)
        stale = await self.db.execute(
            select(CacheEntry).where(CacheEntry.expires_at < now)
        )
        for entry in stale.scalars().all():
            await self.db.delete(entry)
        await self.db.commit()
