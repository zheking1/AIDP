import re
from typing import Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Node, Edge, Project
from app.services.tree_sitter_parser import TreeSitterParser


class IncrementalIndexer:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.parser = TreeSitterParser()

    async def index_file(self, project_id: int, file_path: str, language: str = None) -> Dict:
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            return {"success": False, "error": "Project not found"}
        abs_path = os.path.join(project.path, file_path)
        if not os.path.exists(abs_path):
            return {"success": False, "error": "File not found"}

        symbols = self.parser.parse_file(abs_path)
        checksum = hashlib.md5(open(abs_path, "rb").read()).hexdigest()

        await self.db.execute(
            Node.__table__.delete().where(Node.project_id == project_id, Node.file_path == file_path)
        )

        nodes_created = 0
        for sym in symbols:
            node = Node(
                project_id=project_id, node_type=sym.kind, name=sym.name,
                qualified_name=f"{file_path}::{sym.name}", file_path=file_path,
                line_start=sym.line, line_end=sym.end_line,
                language=sym.kind == "import" and "import" or language or sym.kind,
                checksum=checksum,
            )
            self.db.add(node)
            nodes_created += 1

        await self.db.commit()
        project.file_count = project.file_count + 1
        project.node_count = (project.node_count or 0) + nodes_created
        await self.db.commit()

        return {"success": True, "file_path": file_path, "symbols_found": len(symbols), "checksum": checksum}

    async def index_directory(self, project_id: int, dir_path: str, language: str = None) -> Dict:
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            return {"error": "Project not found"}
        total_files = 0
        total_symbols = 0
        for root, dirs, files in os.walk(dir_path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in self.parser.LANGUAGES:
                    rel_path = os.path.relpath(os.path.join(root, f), project.path)
                    sym_result = await self.index_file(project_id, rel_path, language)
                    if sym_result.get("success"):
                        total_files += 1
                        total_symbols += sym_result.get("symbols_found", 0)
        return {"files_indexed": total_files, "symbols_found": total_symbols}

    import os
    import hashlib
