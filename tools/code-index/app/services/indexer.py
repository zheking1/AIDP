import hashlib
import os
import re
from typing import Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Project, Node, Edge


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
        from app.services.scanner import Scanner
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

        nodes_added = 0
        for file_info in scan_result["files"]:
            file_nodes = await self._index_file(project_id, file_info, language or scan_result.get("language"))
            nodes_added += file_nodes

        if proj:
            proj.node_count = nodes_added
            await self.db.commit()

        return {
            "project_id": project_id,
            "file_count": len(scan_result["files"]),
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
            self.db.add(Edge(project_id=project_id, source_id=file_node.id, target_id=node.id, edge_type="CONTAINS"))

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
            self.db.add(Edge(project_id=project_id, source_id=file_node.id, target_id=node.id, edge_type="CONTAINS"))

        imports = self._extract_imports(content, language)
        for imp in imports:
            self.db.add(Edge(
                project_id=project_id,
                source_id=file_node.id,
                target_id=0,
                edge_type="IMPORTS",
                metadata_={"import_name": imp},
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
