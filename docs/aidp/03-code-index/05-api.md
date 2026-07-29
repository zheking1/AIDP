# Code Index — API Reference

Two API layers: the **Tool Invocation Protocol** (6 capabilities via `POST /tool/invoke`) and **REST endpoints** (direct HTTP access).

---

## Tool Capabilities (6)

All invoked via `POST /tool/invoke` with `ToolInvokeRequest`:

```json
{
  "trace_id": "tr_abc123",
  "capability": "code.search",
  "context": {},
  "input": { "query": "handleError", "top_k": 8 }
}
```

Response is always `ToolInvokeResponse`:

```json
{
  "trace_id": "tr_abc123",
  "tool": "code-index",
  "capability": "code.search",
  "success": true,
  "output": [...],
  "error": null,
  "elapsed_ms": 12
}
```

---

### 1. `code.search` — Exact Symbol Search

| Property       | Value                                       |
|----------------|---------------------------------------------|
| **Endpoint**   | `POST /api/symbols/search`                  |
| **Timeout**    | 3000ms                                      |
| **Permission** | `code:read`                                 |

**Input Schema:**
```json
{
  "project_id": 1,
  "query": "handleError",
  "node_type": "function",
  "top_k": 8
}
```
| Param       | Type     | Required | Default | Description                    |
|-------------|----------|----------|---------|--------------------------------|
| `project_id`| int      | No       | 0       | Project ID (0 = all projects)  |
| `query`     | string   | No       | ""      | Search term                    |
| `node_type` | string   | No       | null    | Filter: "file", "class", "function" |
| `top_k`     | int      | No       | 8       | Max results                    |

**Search scope:** `Node.name`, `Node.signature`, `Node.docstring` (ILIKE, OR logic).

**Output:**
```json
[
  {
    "id": 42,
    "node_type": "function",
    "name": "handle_error",
    "qualified_name": "src/app.py::handle_error",
    "file_path": "src/app.py",
    "line_start": 142,
    "language": "python"
  }
]
```

---

### 2. `code.search.semantic` — Fusion Search

| Property       | Value                                       |
|----------------|---------------------------------------------|
| **Endpoint**   | `POST /api/search/semantic`                 |
| **Timeout**    | 5000ms                                      |
| **Permission** | `code:read`                                 |

**Input Schema:**
```json
{
  "project_id": 1,
  "query": "authentication middleware",
  "top_k": 10,
  "node_type": null
}
```
| Param       | Type     | Required | Default | Description                    |
|-------------|----------|----------|---------|--------------------------------|
| `project_id`| int      | No       | 0       | Project ID                     |
| `query`     | string   | Yes      | —       | Natural language query         |
| `top_k`     | int      | No       | 10      | Max results                    |
| `node_type` | string   | No       | null    | Optional type filter           |

**Output:**
```json
[
  {
    "id": 42,
    "node_type": "function",
    "name": "authenticate_user",
    "qualified_name": "src/auth.py::authenticate_user",
    "file_path": "src/auth.py",
    "line_start": 15,
    "language": "python",
    "signature": "def authenticate_user(token: str) -> User",
    "return_type": "User",
    "docstring": "Authenticate a user from a JWT token.",
    "score": 0.8723,
    "score_breakdown": {
      "vector": 0.9120,
      "exact": 0.4000,
      "fuzzy": 0.6667
    }
  }
]
```

**Fallback behavior:** If embeddings are unavailable, `vector=0.0` and scoring degrades to `0.3*exact + 0.2*fuzzy`.

---

### 3. `code.explore` — Code Exploration (9 Actions)

| Property       | Value                                       |
|----------------|---------------------------------------------|
| **Endpoint**   | `POST /api/explore`                         |
| **Timeout**    | 3000ms                                      |
| **Permission** | `code:read`                                 |

**Input Schema:**
```json
{
  "project_id": 1,
  "action": "symbols",
  "params": { "query": "User", "limit": 50 }
}
```

**9 Valid Actions:**

| Action       | Description                                   | Required params               |
|--------------|-----------------------------------------------|-------------------------------|
| `symbols`    | Search symbols by name                        | `query` (str)                 |
| `file`       | Look up a file node                           | `path` (str)                  |
| `calls`      | List all `calls` edges (limited 100)          | —                             |
| `dependents` | Find what depends on a symbol                 | `name` (str)                  |
| `structure`  | List all classes + functions (limited 200)    | —                             |
| `summary`    | Get project metadata (stats, language, etc.)  | —                             |
| `callers`    | Trace upward callers of a function            | `node_id` (int)               |
| `callees`    | Trace downward callees of a function          | `node_id` (int)               |
| `impact`     | Impact analysis with risk level               | `node_id` (int)               |

**Action: `symbols`**
```json
// Input:  {"action": "symbols", "params": {"query": "User", "type": "class"}}
// Output: {"symbols": [{...}], "total": 3}
```

**Action: `file`**
```json
// Input:  {"action": "file", "params": {"path": "src/models.py"}}
// Output: {"found": true, "node": {"id": 10, "node_type": "file", ...}}
```

**Action: `calls`**
```json
// Output: {"calls": [{"source_id": 10, "target_id": 15}, ...]}
```

**Action: `dependents`**
```json
// Input:  {"action": "dependents", "params": {"name": "User"}}
// Output: {"found": true, "node": {...}, "dependents": [{"source_id": 20, "edge_type": "calls"}, ...]}
```

**Action: `structure`**
```json
// Output: {"structure": [{"id": 10, "type": "function", "name": "get_user",
//           "file": "src/api.py", "line": 42}, ...]}
```

**Action: `summary`**
```json
// Output: {"project": {"id": 1, "name": "my-app", "path": "/app",
//           "language": "python", "framework": "fastapi",
//           "file_count": 45, "node_count": 230, "status": "indexed"}}
```

**Action: `callers`**
```json
// Input:  {"action": "callers", "params": {"node_id": 42}}
// Output: {"callers": [{"node_id": 15, "name": "main", "type": "function",
//           "file": "src/main.py", "line": 10, "depth": 0}, ...]}
```

**Action: `callees`** — Same structure as `callers` but traces `source_id → target_id`.

**Action: `impact`**
```json
// Input:  {"action": "impact", "params": {"node_id": 42}}
// Output: {"node": {...}, "direct_callers": 5, "direct_callees": 3,
//           "callers": [...], "callees": [...], "risk_level": "medium"}
```

**Risk levels:** `high` (>10 callers), `medium` (>5), `low` (≤5).

---

### 4. `code.calls` — Call Tracing

| Property       | Value                                       |
|----------------|---------------------------------------------|
| **Endpoint**   | `POST /api/code/calls`                      |
| **Timeout**    | 3000ms                                      |
| **Permission** | `code:read`                                 |

**Input Schema:**
```json
{
  "node_id": 42,
  "project_id": 1,
  "depth": 3
}
```
| Param       | Type     | Required | Default | Description                    |
|-------------|----------|----------|---------|--------------------------------|
| `node_id`   | int      | No       | —       | Starting function node         |
| `project_id`| int      | No       | 0       | Project ID                     |
| `depth`     | int      | No       | 3       | Max recursion depth            |

**Output:**
```json
{
  "callers": [
    { "node_id": 15, "name": "main", "type": "function",
      "file": "src/main.py", "line": 10, "depth": 0 }
  ],
  "callees": [
    { "node_id": 67, "name": "validate_token", "type": "function",
      "file": "src/auth.py", "line": 88, "depth": 0 }
  ]
}
```

Both `callers` and `callees` are capped at 100 results.

---

### 5. `code.index_files` — Batch File Indexing

| Property       | Value                                       |
|----------------|---------------------------------------------|
| **Endpoint**   | `POST /tool/invoke`                         |
| **Timeout**    | 30000ms                                     |
| **Permission** | `code:write`                                |

**Input Schema:**
```json
{
  "project_id": 1,
  "files": [
    {
      "path": "src/main.py",
      "content": "def hello():\n    print('hi')",
      "language": "python"
    },
    {
      "path": "src/models.py",
      "content": "class User:\n    pass",
      "language": "python"
    }
  ]
}
```
| Param          | Type    | Required | Description                      |
|----------------|---------|----------|----------------------------------|
| `project_id`   | int     | Yes      | Target project                   |
| `files`        | array   | Yes      | List of file content dicts       |
| `files[].path` | string  | Yes      | Relative file path               |
| `files[].content` | string | Yes   | Full file content string         |
| `files[].language` | string | No  | "python" / "java" / "typescript" / "javascript" |

**Output:**
```json
{
  "files_indexed": 2,
  "nodes_created": 6,
  "edges_created": 4,
  "errors": []
}
```

Validation: `project_id` and `files` are required. Returns error response if missing.

---

### 6. `code.create_project` — Project Creation

| Property       | Value                                       |
|----------------|---------------------------------------------|
| **Endpoint**   | `POST /tool/invoke`                         |
| **Timeout**    | 5000ms                                      |
| **Permission** | `code:write`                                |

**Input Schema:**
```json
{
  "name": "MyApp",
  "path": "/home/user/projects/myapp"
}
```
| Param  | Type    | Required | Description                    |
|--------|---------|----------|--------------------------------|
| `name` | string  | Yes      | Display name                   |
| `path` | string  | Yes      | Filesystem path (dedup key)    |

**Dedup:** If a project with the same `path` already exists, returns existing project instead of creating a duplicate.

**Output:**
```json
{
  "project_id": 1,
  "name": "MyApp",
  "path": "/home/user/projects/myapp"
}
```

---

## REST Endpoints (Direct HTTP)

All endpoints in `app/api/code_index.py` and `app/api/health.py`:

### Health
| Method | Path         | Auth | Response                                    |
|--------|--------------|------|---------------------------------------------|
| GET    | `/health`    | —    | `{"status":"ok","tool":"code-index","version":"0.1.0"}` |

### Projects
| Method | Path                        | Auth        | Purpose                       |
|--------|-----------------------------|-------------|-------------------------------|
| POST   | `/api/projects`             | `code:write`| Create project                |
| GET    | `/api/projects`             | `code:read` | List all projects             |
| POST   | `/api/projects/{id}/scan`   | `code:write`| Scan & index directory        |

### Search & Explore
| Method | Path                        | Auth        | Purpose                       |
|--------|-----------------------------|-------------|-------------------------------|
| POST   | `/api/explore`              | `code:read` | 9-action exploration          |
| GET    | `/api/search/typed`         | `code:read` | Typed search with filters     |
| POST   | `/api/symbols/search`       | `code:read` | Exact symbol search           |
| POST   | `/api/search/semantic`      | `code:read` | Semantic fusion search        |

### Indexing
| Method | Path                        | Auth        | Purpose                       |
|--------|-----------------------------|-------------|-------------------------------|
| POST   | `/api/index/file`           | `code:write`| Incremental index single file |
| POST   | `/api/index/directory`      | `code:write`| Incremental index directory   |
| POST   | `/api/index/file-content`   | `code:write`| Index from content string     |

### LSP-like
| Method | Path                        | Auth        | Purpose                       |
|--------|-----------------------------|-------------|-------------------------------|
| GET    | `/api/lsp/references`      | `code:read` | Find symbol references        |
| GET    | `/api/lsp/implementation`  | `code:read` | Find interface implementations |
| GET    | `/api/lsp/hover`           | `code:read` | Hover info (file + line)      |

### Tool Manifest
| Method | Path                        | Auth        | Purpose                       |
|--------|-----------------------------|-------------|-------------------------------|
| GET    | `/tool/manifest`            | —           | AIDP tool manifest             |
| GET    | `/tool/capabilities`        | —           | Capability details + schemas   |
| POST   | `/tool/invoke`              | varies      | Unified tool invocation        |

---

## `POST /api/index/file-content` — Detailed Behavior

**File:** `app/api/code_index.py:122`

This endpoint indexes a file from uploaded content (no filesystem access needed). It implements its own inline extraction using regex (does NOT use `Indexer`):

```python
@router.post("/api/index/file-content")
async def index_file_content(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    project_id = body.get("project_id")
    file_path = body.get("file_path", "")
    content = body.get("content", "")
    language = body.get("language", "python")

    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
```

**Extraction logic (inline, not service):**
- Python: `class ClassName` and `def funcName` (excludes `_private`)
- TypeScript/JS: `class ClassName` and `function name` / `const name = ()`
- Creates nodes + `contains` edges for classes and functions
- Creates `imports` edges from regex on import statements
- Creates `calls` edges: for any `name()` in content, if `name` is a function in the file, all other functions get `calls` edges to it
- **No embedding generation** (unlike `_index_file_content`)

---

## `POST /api/index/file` — Incremental Index Entry Point

**File:** `app/api/code_index.py:100`

```python
@router.post("/api/index/file")
async def index_file(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    project_id = body.get("project_id")
    file_path = body.get("file_path")
    indexer = IncrementalIndexer(db)
    return JSONResponse(await indexer.index_file(project_id, file_path))
```

This is the Tree-Sitter based path — requires actual files on disk, resolves paths relative to `project.path`.

---

## `POST /api/index/directory` — Recursive Index

**File:** `app/api/code_index.py:111`

```python
@router.post("/api/index/directory")
async def index_directory(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    project_id = body.get("project_id")
    dir_path = body.get("dir_path")
    indexer = IncrementalIndexer(db)
    return JSONResponse(await indexer.index_directory(project_id, dir_path))
```

Walks directory, calls `IncrementalIndexer.index_file()` for each supported file.