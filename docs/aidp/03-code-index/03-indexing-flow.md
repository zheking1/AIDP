# Code Index — Indexing Flow

This document covers the complete indexing pipeline: batch indexing (`index_files`), single-file indexing (`_index_file_content`), and incremental indexing (`IncrementalIndexer`).

---

## 1. `index_files()` — Batch Indexing Flow

**File:** `app/services/indexer.py:258`

```python
async def index_files(self, project_id: int, files: List[Dict]) -> Dict:
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
```

**Input:** `files` is a list of `{"path": str, "content": str, "language": str}` dicts — this is how the orchestrator passes source files for scanning.

**Flow:**
1. Iterate over all file dicts
2. For each, call `_index_file_content()` which handles fingerprint dedup, node creation, and edge creation
3. Aggregate totals
4. Update `Project.file_count`, `Project.node_count`, `Project.status`
5. Return summary dict

---

## 2. `_index_file_content()` — Single File Indexing

**File:** `app/services/indexer.py:297`

```python
async def _index_file_content(self, project_id: int, file_path: str,
                               content: str, language: str) -> Dict:
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]

    # Fingerprint dedup: skip if already indexed with same hash
    existing_fp = await self.db.execute(
        select(FileFingerprint).where(
            FileFingerprint.project_id == project_id,
            FileFingerprint.file_path == file_path,
        )
    )
    fp = existing_fp.scalar_one_or_none()
    if fp and fp.file_hash == checksum:
        return {"nodes": 0, "edges": 0, "skipped": True}

    # Remove old nodes for this file (re-index scenario)
    old_nodes = await self.db.execute(
        select(Node).where(Node.project_id == project_id, Node.file_path == file_path)
    )
    for old_node in old_nodes.scalars().all():
        await self.db.execute(
            text("DELETE FROM edges WHERE project_id = :pid AND (source_id = :nid OR target_id = :nid)"),
            {"pid": project_id, "nid": old_node.id},
        )
        await self.db.delete(old_node)
```

**Steps:**
1. Compute SHA256 checksum (first 16 hex chars)
2. Check `file_fingerprints` table — skip if same hash exists
3. Delete old nodes and their edges (cascade manually since SQLite doesn't support FK cascades)
4. Create `file` node
5. Extract classes, functions, imports
6. Create class and function nodes with `contains` edges from the file node
7. Generate embeddings via `NodeEmbeddingStore.compute_batch()`
8. Extract function calls — create `calls` edges between functions in the same file
9. Update or create `FileFingerprint` record

---

## 3. `_extract_classes()` — Class Extraction

**File:** `app/services/indexer.py:190`

Regex-based extraction, language-specific:

```python
def _extract_classes(self, content: str, language: str) -> List[Dict]:
    if language == "java":
        # Matches: public/private/protected abstract/final class ClassName
        for m in re.finditer(r'(?:public|private|protected)?\s*(?:abstract|final)?\s*class\s+(\w+)', content):
            classes.append({"name": m.group(1), "line": ...})
    elif language == "python":
        # Matches: class ClassName (at line start with optional indent)
        for m in re.finditer(r'^\s*class\s+(\w+)', content, re.MULTILINE):
            classes.append({"name": m.group(1), "line": ...})
    elif language in ("typescript", "javascript"):
        # Matches: class ClassName
        for m in re.finditer(r'class\s+(\w+)', content):
            classes.append({"name": m.group(1), "line": ...})
    return classes
```

Returns `List[Dict]` with `{"name": str, "line": int}`.

---

## 4. `_extract_functions()` — Function Extraction

**File:** `app/services/indexer.py:203`

```python
def _extract_functions(self, content: str, language: str) -> List[Dict]:
    if language == "python":
        # Matches: def function_name (excludes private _methods)
        for m in re.finditer(r'^\s*def\s+(\w+)', content, re.MULTILINE):
            name = m.group(1)
            if not name.startswith('_'):
                functions.append({"name": name, "line": ...})
    elif language == "java":
        # Matches: access_modifier return_type method_name(
        # Excludes keywords: if, else, while, for, switch, catch, return
        for m in re.finditer(r'(?:public|private|protected|static|\s)+\s+\w+\s+(\w+)\s*\(', content):
            if name not in ("if", "else", "while", "for", "switch", "catch", "return"):
                functions.append(...)
    elif language in ("typescript", "javascript"):
        # Matches: function name(...), name = (...) =>, const name = () =>
        for m in re.finditer(r'(?:function\s+(\w+)|(\w+)\s*=\s*(?:async\s*)?\(?|const\s+\w+\s*=\s*(?:async\s*)?\()?', content):
            if name and name not in ("if", "else", "while", "for", "switch", "const", "let", "var", "return"):
                functions.append(...)
    return functions
```

Python: filters out private functions (starting with `_`). Java: filters out reserved keywords that match the pattern.

---

## 5. `_extract_imports()` — Import Extraction

**File:** `app/services/indexer.py:243`

```python
def _extract_imports(self, content: str, language: str) -> List[str]:
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
```

Returns `List[str]` of module names. These create `imports` edges from the file node to `target_id=0`.

---

## 6. `_extract_function_calls()` — Call Extraction

**File:** `app/services/indexer.py:222`

```python
def _extract_function_calls(self, content: str, language: str) -> List[str]:
    calls = set()
    if language == "python":
        for m in re.finditer(r'([\w]+)\s*\(', content):
            if not (name[0].isupper() or name in ("if", "for", "while", ...)):
                calls.add(name)
        # Also detect self.method() calls
        for m in re.finditer(r'self\.(\w+)\s*\(', content):
            calls.add(m.group(1))
    elif language == "java":
        for m in re.finditer(r'(\w+)\s*\(', content):
            if name[0].islower() and name not in ("if", "for", "while", ...):
                calls.add(name)
    elif language in ("typescript", "javascript"):
        for m in re.finditer(r'(\w+)\s*\(', content):
            if name[0].islower() and name not in ("if", "for", "while", ...):
                calls.add(name)
    return list(calls)
```

Filters: excludes uppercase-starting names (likely classes), language keywords, and common builtins (`print`, `len`, `int`, `str`, `list`, `dict`, `set`, `range`, `isinstance`, `hasattr`, `getattr`, `setattr`, `super`, `self`, `cls`).

---

## 7. Fingerprint-Based Dedup

The `FileFingerprint` model stores per-file hashes:

```python
class FileFingerprint(Base):
    __tablename__ = "file_fingerprints"
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, nullable=False)
    file_path = Column(String(1024), nullable=False)
    file_hash = Column(String(64), nullable=False)       # SHA256 hex
    last_indexed_at = Column(DateTime, nullable=False)
    node_count = Column(Integer, default=0)
    __table_args__ = (UniqueConstraint("project_id", "file_path"),)
```

When re-indexing:
1. Compute new SHA256 hash of file content (first 16 chars)
2. Query `file_fingerprints` by `(project_id, file_path)`
3. If found and hash matches → skip file entirely
4. Otherwise → delete old nodes/edges, create new ones, update fingerprint

---

## 8. Node Creation

Three node types are created during indexing:

| Node Type | Record                                    | Edge                       |
|-----------|-------------------------------------------|----------------------------|
| `file`    | name=basename, qualified_name=full_path   | —                          |
| `class`   | name=ClassName, qualified_name=path::Name | `contains` from file       |
| `function`| name=funcName, qualified_name=path::name  | `contains` from file       |

Additional fields set on nodes:
- `line_start`, `line_end` (from extraction)
- `language` (detected or specified)
- `checksum` (SHA256[0:16] of content)

---

## 9. Edge Creation

Three edge types:

| Edge Type  | Source       | Target          | Metadata                   |
|------------|--------------|-----------------|----------------------------|
| `contains` | file node    | class/function  | —                          |
| `calls`    | caller func  | callee func     | —                          |
| `imports`  | file node    | 0 (virtual)     | `{"import_name": "..."}`   |

Call edges: only created when file has 2+ functions. For each detected `name()` call in the content, if `name` matches a function in the same file, all other functions get `calls` edges to that function. This is intentionally broad — it creates N×(N-1) edges for N functions (all-but-self).

Import edges: target_id is always 0 (virtual root), metadata carries the module name.

---

## 10. Embedding Generation

Embeddings are generated inline during `_index_file_content()`:

```python
if nodes_to_embed:
    try:
        from app.services.node_embedding_store import NodeEmbeddingStore
        store = NodeEmbeddingStore(self.db)
        await store.compute_batch(nodes_to_embed)
    except Exception as e:
        logger.warning(f"Failed to generate embeddings for {file_path}: {e}")
```

`nodes_to_embed` includes all class and function nodes created in the file (file nodes themselves are not embedded). Embedding failures are logged but don't block indexing.

---

## 11. Incremental Indexer (`IncrementalIndexer`)

**File:** `app/services/incremental_indexer.py`

Separate from `Indexer` — uses Tree-Sitter for richer AST parsing:

```python
class IncrementalIndexer:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.parser = TreeSitterParser()
```

### `index_file(project_id, file_path, language=None)`
1. Resolves absolute path via `os.path.join(project.path, file_path)`
2. Computes `sha256` hash of file bytes
3. Checks `FileFingerprint` — skip if unchanged
4. Deletes old nodes + edges for this file
5. Parses with Tree-Sitter (primary) or regex fallback
6. Creates nodes with richer metadata: `signature`, `return_type`, `params`, `file_hash`
7. Updates fingerprint record
8. Returns `{"success": True, "symbols_found": N, "checksum": "...", "nodes_created": N}`

### `index_directory(project_id, dir_path, language=None)`
1. Walks directory tree (skips dot-prefixed dirs)
2. Filters files by `TreeSitterParser.LANGUAGES` extensions
3. Calls `index_file()` for each eligible file
4. Returns aggregate `{"files_indexed", "files_skipped", "symbols_found"}`

Returned `Symbol` objects from Tree-Sitter are richer than regex extraction:
```python
@dataclass
class Symbol:
    name: str
    kind: str          # "class", "function", "method"
    file_path: str
    line: int
    end_line: Optional[int] = None
    params: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    access_modifier: Optional[str] = None
    annotations: List[str] = field(default_factory=list)
    code: str = ""     # First line of the definition
```

---

## 12. Scan-and-Index Flow (`Indexer.scan_and_index`)

**File:** `app/services/indexer.py:31`

End-to-end flow for directory-based indexing:
```
Scanner.scan_directory(path)
  ├── Walks directory tree
  ├── Detects language, framework
  ├── Computes SHA256 fingerprints
  └── Returns: {files: [...], modules: [...]}

Scanner.compute_fingerprints(files)
  └── Sets file["hash"] for each file

Indexer.scan_and_index(project_id, path):
  ├── For each file in scan result:
  │   ├── Query FileFingerprint by (project_id, file_path)
  │   ├── If match → skip (increment skipped_files)
  │   └── Else → call _index_file()
  ├── Update project stats
  └── Return summary
```

Key difference from `index_files()`: this operates on actual filesystem paths, not uploaded content strings. The `Indexer._index_file()` method reads files from disk, while `_index_file_content()` takes content directly.