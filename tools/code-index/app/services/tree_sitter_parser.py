import os
import re
import hashlib
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class Symbol:
    name: str
    kind: str
    file_path: str
    line: int
    end_line: Optional[int] = None
    params: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    access_modifier: Optional[str] = None
    annotations: List[str] = field(default_factory=list)
    code: str = ""


@dataclass
class Dependency:
    source_file: str
    target_file: str
    dependency_type: str
    source_symbol: Optional[str] = None
    target_symbol: Optional[str] = None


class TreeSitterParser:
    def __init__(self):
        self._parsers = {}
        self._try_init_ts()

    def _try_init_ts(self):
        try:
            import tree_sitter_java
            import tree_sitter_python
            import tree_sitter_typescript
            import tree_sitter
            self._has_ts = True
            self._ts = tree_sitter
            self._parsers = {
                "java": tree_sitter.Language(tree_sitter_java.language()),
                "python": tree_sitter.Language(tree_sitter_python.language()),
                "typescript": tree_sitter.Language(tree_sitter_typescript.language("ts")),
                "javascript": tree_sitter.Language(tree_sitter_typescript.language("js")),
            }
        except ImportError:
            self._has_ts = False

    def parse_file(self, file_path: str) -> List[Symbol]:
        if not self._has_ts:
            return self._regex_parse(file_path)

        ext = os.path.splitext(file_path)[1].lower()
        lang_map = {".java": "java", ".py": "python", ".ts": "typescript", ".tsx": "typescript", ".js": "javascript", ".jsx": "javascript"}
        lang = lang_map.get(ext)
        if not lang or lang not in self._parsers:
            return self._regex_parse(file_path)

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return []

        parser = self._ts.Parser(self._parsers[lang])
        tree = parser.parse(content.encode())
        return self._extract_symbols(tree, content, file_path)

    def _extract_symbols(self, tree, content: str, file_path: str) -> List[Symbol]:
        symbols = []
        self._walk_tree(tree.root_node, content, file_path, symbols)
        return symbols

    def _walk_tree(self, node, content: str, file_path: str, symbols: List[Symbol]):
        node_type = node.type
        if node_type in ("class_declaration", "class"):
            name_node = node.child_by_field_name("name") or (node.children[1] if len(node.children) > 1 else None)
            if name_node:
                symbols.append(Symbol(name=name_node.text.decode(), kind="class", file_path=file_path, line=node.start_point[0] + 1, end_line=node.end_point[0] + 1))
        elif node_type in ("function_definition", "function_declaration", "method_definition"):
            name_node = node.child_by_field_name("name") or node.children[1] if len(node.children) > 1 else None
            if name_node:
                params_node = node.child_by_field_name("parameters")
                params = []
                if params_node:
                    for child in params_node.children:
                        if child.type != "(" and child.type != ")":
                            params.append(child.text.decode())
                symbols.append(Symbol(name=name_node.text.decode(), kind="function", file_path=file_path, line=node.start_point[0] + 1, end_line=node.end_point[0] + 1, params=params))
        for child in node.children:
            self._walk_tree(child, content, file_path, symbols)

    def _regex_parse(self, file_path: str) -> List[Symbol]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return []
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".java":
            return self._parse_java_regex(content, file_path)
        elif ext == ".py":
            return self._parse_python_regex(content, file_path)
        elif ext in (".ts", ".tsx", ".js", ".jsx"):
            return self._parse_ts_regex(content, file_path)
        return []

    def _parse_java_regex(self, content: str, fp: str) -> List[Symbol]:
        syms = []
        for m in re.finditer(r'(?:public|private|protected)?\s*(?:abstract|final)?\s*class\s+(\w+)', content):
            syms.append(Symbol(name=m.group(1), kind="class", file_path=fp, line=content[:m.start()].count('\n') + 1))
        for m in re.finditer(r'(?:public|private|protected)\s+(?:static\s+)?(?:final\s+)?(\w+(?:<[^>]+>)?)\s+(\w+)\s*\(([^)]*)\)', content):
            syms.append(Symbol(name=m.group(2), kind="method", file_path=fp, line=content[:m.start()].count('\n') + 1, params=[p.strip() for p in m.group(3).split(',') if p.strip()], return_type=m.group(1)))
        return syms

    def _parse_python_regex(self, content: str, fp: str) -> List[Symbol]:
        syms = []
        for m in re.finditer(r'^\s*class\s+(\w+)', content, re.MULTILINE):
            syms.append(Symbol(name=m.group(1), kind="class", file_path=fp, line=content[:m.start()].count('\n') + 1))
        for m in re.finditer(r'^\s*def\s+(\w+)\s*\(([^)]*)\)', content, re.MULTILINE):
            name = m.group(1)
            if not name.startswith('_'):
                params = [p.strip().split(':')[0].split('=')[0].strip() for p in m.group(2).split(',') if p.strip() and p.strip() != 'self']
                syms.append(Symbol(name=name, kind="function", file_path=fp, line=content[:m.start()].count('\n') + 1, params=params))
        return syms

    def _parse_ts_regex(self, content: str, fp: str) -> List[Symbol]:
        syms = []
        for m in re.finditer(r'class\s+(\w+)', content):
            syms.append(Symbol(name=m.group(1), kind="class", file_path=fp, line=content[:m.start()].count('\n') + 1))
        for m in re.finditer(r'(?:function\s+(\w+)|(\w+)\s*=\s*(?:async\s*)?\(?|const\s+\w+\s*=\s*(?:async\s*)?\()', content):
            name = m.group(1) or m.group(2)
            if name and name not in ("if", "else", "while", "for", "switch", "const", "let", "var"):
                syms.append(Symbol(name=name, kind="function", file_path=fp, line=content[:m.start()].count('\n') + 1))
        return syms

    def extract_dependencies(self, symbols: List[Symbol], file_path: str) -> List[Dependency]:
        return [Dependency(source_file=file_path, target_file="", dependency_type="import", target_symbol=s.name) for s in symbols if s.kind == "import"]
