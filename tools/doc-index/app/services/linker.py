from typing import Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import DocPage, CodeLink


class CodeLinker:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def link_document_to_code(self, doc_id: int, code_nodes: List[Dict]) -> List[CodeLink]:
        links = []
        for node in code_nodes:
            link = CodeLink(
                doc_id=doc_id,
                node_type=node.get("type", "class"),
                node_name=node.get("name", ""),
                file_path=node.get("file_path", ""),
                line_start=node.get("line_start"),
                line_end=node.get("line_end"),
                language=node.get("language", "unknown"),
                confidence=node.get("confidence", 0.5),
            )
            self.db.add(link)
            links.append(link)
        await self.db.commit()
        return links

    async def get_code_links(self, doc_id: int) -> List[CodeLink]:
        result = await self.db.execute(
            select(CodeLink).where(CodeLink.doc_id == doc_id)
        )
        return result.scalars().all()
