import hashlib
import logging
import os
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.tools.code_index.db.models import Project, Node, Edge, FileFingerprint

logger = logging.getLogger(__name__)


class Indexer:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_project(self, name: str, path: str) -> Project:
        result = await self.db.execute(
            select(Project).where(Project.path == path)
        )
        project = result.scalar_one_or_none()
        if project:
            return project
        project = Project(name=name, path=path)
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def scan_and_index(self, project_id: int, path: str, language: str = None) -> Dict:
        from app.tools.code_index.services.scanner import Scanner
        scanner = Scanner()
        scan_result = scanner.scan_directory(path)

        project = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        proj = project.scalar_one_or_none()
        if proj:
            proj.file_count = len(scan_result["files"])
            proj.language = scan_result.get("language", language)
            proj.framework = scan_result.get("framework", "unknown")
            proj.status = "indexed"
            proj.last_scan_at = None
            await self.db.commit()

        scanner.compute_fingerprints(scan_result["files"])

        changed_files = []
        skipped_files = 0
        for file_info in scan_result["files"]:
            result = await self.db.execute(
                select(FileFingerprint).where(
                    FileFingerprint.project_id == project_id,
                    FileFingerprint.file_path == file_info["path"],
                )
            )
            fp_record = result.scalar_one_or_none()
            if fp_record and fp_record.file_hash == file_info.get("hash", ""):
                skipped_files += 1
                continue
            changed_files.append(file_info)

        nodes_added = 0
        for file_info in changed_files:
            file_nodes = await self._index_file(project_id, file_info, language or scan_result.get("language"))
            nodes_added += file_nodes

            existing = await self.db.execute(
                select(FileFingerprint).where(
                    FileFingerprint.project_id == project_id,
                    FileFingerprint.file_path == file_info["path"],
                )
            )
            fp = existing.scalar_one_or_none()
            now = datetime.now(timezone.utc)
            if fp:
                fp.file_hash = file_info.get("hash", "")
                fp.last_indexed_at = now
            else:
                self.db.add(FileFingerprint(
                    project_id=project_id,
                    file_path=file_info["path"],
                    file_hash=file_info.get("hash", ""),
                    last_indexed_at=now,
                    node_count=file_nodes,
                ))

        if proj:
            proj.node_count = nodes_added
            await self.db.commit()

        return {
            "project_id": project_id,
            "file_count": len(scan_result["files"]),
            "changed_files": len(changed_files),
            "skipped_files": skipped_files,
            "node_count": nodes_added,
            "modules": scan_result.get("modules", []),
        }

    async def _index_file(self, project_id: int, file_info: Dict, language: str) -> int:
        file_path = file_info["full_path"]
        if not os.path.exists(file_path):
            return 0

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return 0

        checksum = hashlib.sha256(content.encode()).hexdigest()[:16]

        file_node = Node(
            project_id=project_id,
            node_type="file",
            name=os.path.basename(file_path),
            qualified_name=file_info["path"],
            file_path=file_info["path"],
            language=language,
            checksum=checksum,
        )
        self.db.add(file_node)
        await self.db.flush()

        classes = self._extract_classes(content, language)
        functions = self._extract_functions(content, language)

        for cls in classes:
            node = Node(
                project_id=project_id,
                node_type="class",
                name=cls["name"],
                qualified_name=f"{file_info['path']}::{cls['name']}",
                file_path=file_info["path"],
                line_start=cls["line"],
                line_end=cls.get("end_line"),
                language=language,
            )
            self.db.add(node)
            await self.db.flush()
            self.db.add(Edge(project_id=project_id, source_id=file_node.id, target_id=node.id, edge_type="contains"))

        for fn in functions:
            node = Node(
                project_id=project_id,
                node_type="function",
                name=fn["name"],
                qualified_name=f"{file_info['path']}::{fn['name']}",
                file_path=file_info["path"],
                line_start=fn["line"],
                line_end=fn.get("end_line"),
                language=language,
            )
            self.db.add(node)
            await self.db.flush()
            self.db.add(Edge(project_id=project_id, source_id=file_node.id, target_id=node.id, edge_type="contains"))
            fn["_node_id"] = node.id

        imports = self._extract_imports(content, language)
        for imp in imports:
            self.db.add(Edge(
                project_id=project_id,
                source_id=file_node.id,
                target_id=0,
                edge_type="imports",
                metadata_={"import_name": imp},
            ))

        func_node_ids = {fn["name"]: fn["_node_id"] for fn in functions if "_node_id" in fn}
        if len(func_node_ids) > 1:
            calls = self._extract_function_calls(content, language)
            for call_name in calls:
                if call_name in func_node_ids:
                    target_id = func_node_ids[call_name]
                    for caller_name, caller_id in func_node_ids.items():
                        if caller_name != call_name:
                            self.db.add(Edge(
                                project_id=project_id,
                                source_id=caller_id,
                                target_id=target_id,
                                edge_type="calls",
                            ))

        await self.db.commit()
        return 1 + len(classes) + len(functions)

    def _extract_classes(self, content: str, language: str) -> List[Dict]:
        classes = []
        if language == "java":
            for m in re.finditer(r'(?:public|private|protected)?\s*(?:abstract|final)?\s*class\s+(\w+)', content):
                classes.append({"name": m.group(1), "line": content[:m.start()].count('\n') + 1})
        elif language == "python":
            for m in re.finditer(r'^\s*class\s+(\w+)', content, re.MULTILINE):
                classes.append({"name": m.group(1), "line": content[:m.start()].count('\n') + 1})
        elif language in ("typescript", "javascript"):
            for m in re.finditer(r'class\s+(\w+)', content):
                classes.append({"name": m.group(1), "line": content[:m.start()].count('\n') + 1})
        return classes

    def _extract_functions(self, content: str, language: str) -> List[Dict]:
        functions = []
        if language == "java":
            for m in re.finditer(r'(?:public|private|protected|static|\s)+\s+\w+\s+(\w+)\s*\(', content):
                name = m.group(1)
                if name not in ("if", "else", "while", "for", "switch", "catch", "return"):
                    functions.append({"name": name, "line": content[:m.start()].count('\n') + 1})
        elif language == "python":
            for m in re.finditer(r'^\s*def\s+(\w+)', content, re.MULTILINE):
                name = m.group(1)
                if not name.startswith('_'):
                    functions.append({"name": name, "line": content[:m.start()].count('\n') + 1})
        elif language in ("typescript", "javascript"):
            for m in re.finditer(r'(?:function\s+(\w+)|(\w+)\s*=\s*(?:async\s*)?\(?|const\s+\w+\s*=\s*(?:async\s*)?\()?', content):
                name = m.group(1) or m.group(2)
                if name and name not in ("if", "else", "while", "for", "switch", "const", "let", "var", "return"):
                    functions.append({"name": name, "line": content[:m.start()].count('\n') + 1})
        return functions

    def _extract_function_calls(self, content: str, language: str) -> List[str]:
        calls = set()
        if language == "python":
            for m in re.finditer(r'([\w]+)\s*\(', content):
                name = m.group(1)
                if not (name[0].isupper() or name in ("if", "for", "while", "return", "print", "len", "int", "str", "list", "dict", "set", "range", "isinstance", "hasattr", "getattr", "setattr", "super", "self", "cls")):
                    calls.add(name)
            for m in re.finditer(r'self\.(\w+)\s*\(', content):
                calls.add(m.group(1))
        elif language == "java":
            for m in re.finditer(r'(\w+)\s*\(', content):
                name = m.group(1)
                if name[0].islower() and name not in ("if", "for", "while", "switch", "catch", "return", "new", "throw"):
                    calls.add(name)
        elif language in ("typescript", "javascript"):
            for m in re.finditer(r'(\w+)\s*\(', content):
                name = m.group(1)
                if name[0].islower() and name not in ("if", "for", "while", "switch", "catch", "return", "console", "require"):
                    calls.add(name)
        return list(calls)

    def _extract_imports(self, content: str, language: str) -> List[str]:
        imports = []
        if language == "python":
            for m in re.finditer(r'from\s+([\w.]+)\s+import', content):
                imports.append(m.group(1))
            for m in re.finditer(r'import\s+([\w.]+)', content):
                imports.append(m.group(1))
        elif language == "java":
            for m in re.finditer(r'import\s+([\w.]+);', content):
                imports.append(m.group(1))
        elif language in ("typescript", "javascript"):
            for m in re.finditer(r'(?:import|require)\s*\(?[\'\"](\S+)[\'\"]\)?', content):
                imports.append(m.group(1))
        return imports

    async def index_files(self, project_id: int, files: List[Dict]) -> Dict:
        """Batch index files with content from local scanning."""
        nodes_total = 0
        edges_total = 0
        files_indexed = 0
        errors = []

        for file_info in files:
            file_path = file_info.get("path", "")
            content = file_info.get("content", "")
            language = file_info.get("language", "unknown")

            if not file_path or not content:
                continue

            try:
                result = await self._index_file_content(project_id, file_path, content, language)
                nodes_total += result.get("nodes", 0)
                edges_total += result.get("edges", 0)
                files_indexed += 1
            except Exception as e:
                errors.append({"file": file_path, "error": str(e)})

        # Update project stats
        project = await self.db.execute(select(Project).where(Project.id == project_id))
        proj = project.scalar_one_or_none()
        if proj:
            proj.file_count = (proj.file_count or 0) + files_indexed
            proj.node_count = (proj.node_count or 0) + nodes_total
            proj.status = "indexed"
            await self.db.commit()

        return {
            "files_indexed": files_indexed,
            "nodes_created": nodes_total,
            "edges_created": edges_total,
            "errors": errors,
        }

    async def _index_file_content(self, project_id: int, file_path: str, content: str, language: str) -> Dict:
        """Index a single file from content string."""
        import os

        checksum = hashlib.sha256(content.encode()).hexdigest()[:16]

        # Check if file already indexed with same hash
        existing_fp = await self.db.execute(
            select(FileFingerprint).where(
                FileFingerprint.project_id == project_id,
                FileFingerprint.file_path == file_path,
            )
        )
        fp = existing_fp.scalar_one_or_none()
        if fp and fp.file_hash == checksum:
            return {"nodes": 0, "edges": 0, "skipped": True}

        # Remove old nodes for this file
        old_nodes = await self.db.execute(
            select(Node).where(Node.project_id == project_id, Node.file_path == file_path)
        )
        for old_node in old_nodes.scalars().all():
            await self.db.execute(
                text("DELETE FROM edges WHERE project_id = :pid AND (source_id = :nid OR target_id = :nid)"),
                {"pid": project_id, "nid": old_node.id},
            )
            await self.db.delete(old_node)

        file_node = Node(
            project_id=project_id, node_type="file",
            name=os.path.basename(file_path), qualified_name=file_path,
            file_path=file_path, language=language, checksum=checksum,
        )
        self.db.add(file_node)
        await self.db.flush()

        classes = self._extract_classes(content, language)
        functions = self._extract_functions(content, language)

        func_node_ids = {}
        nodes_to_embed = []
        
        for cls in classes:
            node = Node(project_id=project_id, node_type="class", name=cls["name"],
                        qualified_name=f"{file_path}::{cls['name']}", file_path=file_path,
                        line_start=cls["line"], language=language)
            self.db.add(node)
            await self.db.flush()
            self.db.add(Edge(project_id=project_id, source_id=file_node.id, target_id=node.id, edge_type="contains"))
            nodes_to_embed.append(node)

        for fn in functions:
            node = Node(project_id=project_id, node_type="function", name=fn["name"],
                        qualified_name=f"{file_path}::{fn['name']}", file_path=file_path,
                        line_start=fn["line"], language=language)
            self.db.add(node)
            await self.db.flush()
            func_node_ids[fn["name"]] = node.id
            self.db.add(Edge(project_id=project_id, source_id=file_node.id, target_id=node.id, edge_type="contains"))
            nodes_to_embed.append(node)

        # Generate embeddings for nodes
        if nodes_to_embed:
            try:
                from app.tools.code_index.services.node_embedding_store import NodeEmbeddingStore
                store = NodeEmbeddingStore(self.db)
                await store.compute_batch(nodes_to_embed)
            except Exception as e:
                logger.warning(f"Failed to generate embeddings for {file_path}: {e}")

        imports = self._extract_imports(content, language)
        for imp in imports:
            self.db.add(Edge(project_id=project_id, source_id=file_node.id, target_id=0,
                             edge_type="imports", metadata_={"import_name": imp}))

        if len(func_node_ids) > 1:
            calls = self._extract_function_calls(content, language)
            for call_name in calls:
                if call_name in func_node_ids:
                    for caller_name, caller_id in func_node_ids.items():
                        if caller_name != call_name:
                            self.db.add(Edge(project_id=project_id, source_id=caller_id,
                                             target_id=func_node_ids[call_name], edge_type="calls"))

        # Update fingerprint
        if fp:
            fp.file_hash = checksum
            fp.last_indexed_at = datetime.now(timezone.utc)
        else:
            self.db.add(FileFingerprint(project_id=project_id, file_path=file_path,
                                        file_hash=checksum, node_count=1 + len(classes) + len(functions)))

        await self.db.flush()
        return {"nodes": 1 + len(classes) + len(functions), "edges": len(classes) + len(functions) + len(imports)}
