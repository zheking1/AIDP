from typing import Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.tools.doc_index.db.models import DocPage, DocSection


class WikiGenerator:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_wiki(self, language: str = None, framework: str = None) -> Dict:
        query = select(DocPage)
        if language:
            query = query.where(DocPage.language == language)
        if framework:
            query = query.where(DocPage.framework == framework)
        result = await self.db.execute(query)
        pages = result.scalars().all()

        wiki = {
            "pages": [],
            "toc": [],
        }
        for p in pages:
            wiki["pages"].append({
                "id": p.id,
                "title": p.title,
                "summary": p.summary,
                "url": p.url,
            })
            wiki["toc"].append({
                "title": p.title,
                "url": f"/wiki/{p.id}",
            })
        return wiki
