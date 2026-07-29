from typing import Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import DocPage, DocSection, CodeLink, DocDrift


class SearchService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search(self, query: str, limit: int = 20) -> List[Dict]:
        pattern = f"%{query}%"
        result = await self.db.execute(
            select(DocPage).where(
                DocPage.title.ilike(pattern) |
                DocPage.summary.ilike(pattern) |
                DocPage.content.ilike(pattern)
            ).limit(limit)
        )
        pages = result.scalars().all()
        return [{
            "id": p.id,
            "title": p.title,
            "url": p.url,
            "summary": p.summary,
            "language": p.language,
            "framework": p.framework,
            "word_count": p.word_count,
        } for p in pages]

    async def get_page(self, doc_id: int) -> Optional[Dict]:
        result = await self.db.execute(select(DocPage).where(DocPage.id == doc_id))
        page = result.scalar_one_or_none()
        if page:
            return {
                "id": page.id,
                "title": page.title,
                "url": page.url,
                "content": page.content,
                "summary": page.summary,
                "language": page.language,
                "framework": page.framework,
                "word_count": page.word_count,
            }
        return None

    async def get_all_pages(self) -> List[Dict]:
        result = await self.db.execute(select(DocPage).order_by(DocPage.id.desc()))
        pages = result.scalars().all()
        return [{
            "id": p.id,
            "title": p.title,
            "url": p.url,
            "language": p.language,
            "framework": p.framework,
            "word_count": p.word_count,
        } for p in pages]
