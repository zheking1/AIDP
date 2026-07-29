import os
import hashlib
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Node, Edge, Project, FileFingerprint
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

        with open(abs_path, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

        fp_result = await self.db.execute(
            select(FileFingerprint).where(
                FileFingerprint.project_id == project_id,
                FileFingerprint.file_path == file_path,
            )
        )
        existing_fp = fp_result.scalar_one_or_none()
        if existing_fp and existing_fp.file_hash == file_hash:
            return {"success": True, "file_path": file_path, "skipped": True, "reason": "file_unchanged"}

        symbols = self.parser.parse_file(abs_path)
        checksum = hashlib.md5(open(abs_path, "rb").read()).hexdigest()

        old_nodes = await self.db.execute(
            select(Node).where(Node.project_id == project_id, Node.file_path == file_path)
        )
        old_node_ids = []
        for old_node in old_nodes.scalars().all():
            old_node_ids.append(old_node.id)
            await self.db.delete(old_node)

        if old_node_ids:
            await self.db.execute(
                Edge.__table__.delete().where(
                    (Edge.source_id.in_(old_node_ids)) | (Edge.target_id.in_(old_node_ids))
                )
            )

        nodes_created = 0
        for sym in symbols:
            node = Node(
                project_id=project_id,
                node_type=sym.kind,
                name=sym.name,
                qualified_name=f"{file_path}::{sym.name}",
                file_path=file_path,
                line_start=sym.line,
                line_end=sym.end_line,
                language=sym.kind == "import" and "import" or language or sym.kind,
                checksum=checksum,
                signature=sym.code if sym.code else None,
                return_type=sym.return_type,
                params_json=str(sym.params) if sym.params else None,
                file_hash=file_hash,
            )
            self.db.add(node)
            nodes_created += 1

        await self.db.flush()

        if existing_fp:
            existing_fp.file_hash = file_hash
            existing_fp.last_indexed_at = datetime.now(timezone.utc)
            existing_fp.node_count = nodes_created
        else:
            self.db.add(FileFingerprint(
                project_id=project_id,
                file_path=file_path,
                file_hash=file_hash,
                last_indexed_at=datetime.now(timezone.utc),
                node_count=nodes_created,
            ))

        await self.db.commit()

        return {"success": True, "file_path": file_path, "symbols_found": len(symbols), "checksum": file_hash, "nodes_created": nodes_created}

    async def index_directory(self, project_id: int, dir_path: str, language: str = None) -> Dict:
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            return {"error": "Project not found"}
        total_files = 0
        total_symbols = 0
        skipped = 0
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
                        if sym_result.get("skipped"):
                            skipped += 1
        return {"files_indexed": total_files, "files_skipped": skipped, "symbols_found": total_symbols}