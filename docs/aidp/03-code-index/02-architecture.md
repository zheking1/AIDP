# Code Index — Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Application                         │
│                       (port 18086)                               │
├──────────────────────────────────────────────────────────────────┤
│  API Layer (app/api/)                                            │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │
│  │ health.py    │ │ code_index.py│ │ tool.py                  │ │
│  │ GET /health  │ │ 11 REST      │ │ Tool invoke dispatcher   │ │
│  │              │ │ endpoints    │ │ (6 capabilities)         │ │
│  └──────────────┘ └──────────────┘ └──────────────────────────┘ │
├──────────────────────────────────────────────────────────────────┤
│  Service Layer (app/services/)                                   │
│  ┌─────────────┐ ┌──────────────┐ ┌───────────────────────────┐ │
│  │ Indexer     │ │ SearchService│ │ CodeExploreService        │ │
│  │             │ │              │ │                           │ │
│  │ IncrIndexer │ │              │ │                           │ │
│  ├─────────────┤ ├──────────────┤ ├───────────────────────────┤ │
│  │ CallTracer  │ │ Scanner      │ │ LSPClient                 │ │
│  ├─────────────┤ ├──────────────┤ ├───────────────────────────┤ │
│  │ EmbeddingSvc│ │NodeEmbStore  │ │ TreeSitterParser          │ │
│  └─────────────┘ └──────────────┘ └───────────────────────────┘ │
├──────────────────────────────────────────────────────────────────┤
│  Data Layer (app/db/)                                            │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │
│  │ models.py    │ │ database.py  │ │ init_db.py               │ │
│  │ 5 ORM models │ │ SQLAlchemy   │ │ Create tables + migrate  │ │
│  │              │ │ async engine │ │                          │ │
│  └──────────────┘ └──────────────┘ └──────────────────────────┘ │
│  ┌────────────────────┐ ┌──────────────────────────────────────┐ │
│  │ migrate_add_cols   │ │ migrate_edge_types                   │ │
│  │ (signature,        │ │ (edge_type → lowercase)             │ │
│  │  docstring, etc.)  │ │                                      │ │
│  └────────────────────┘ └──────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────┤
│  Storage                                                         │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  SQLite Database (data/code_index.db) — WAL mode            │ │
│  │  Tables: projects, nodes, edges, file_fingerprints,         │ │
│  │          node_embeddings                                    │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘

                    ┌──────────────────────┐
                    │  Model Controller     │
                    │  (localhost:8883)    │
                    │  /api/models/        │
                    │  for-task/embedding  │
                    └──────────────────────┘
```

## Application Entry Point (`app/main.py`)

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_database()   # Create tables + run migrations
    yield

app = FastAPI(title="Code Index Tool", version="0.1.0", lifespan=lifespan)
app.include_router(health_router)       # GET /health
app.include_router(code_index_router)   # REST endpoints
app.include_router(tool_router)         # Tool invocation (6 capabilities)
```

Database initialization (`app/db/init_db.py`):
1. Create all tables via `Base.metadata.create_all`
2. Run `migrate_edge_types()` — normalize edge_type to lowercase
3. Run `migrate_add_node_columns()` — add signature, docstring, return_type, params_json, file_hash columns

## API Layer Detail

### `app/api/health.py`
Single endpoint: `GET /health` returns `{"status": "ok", "tool": "code-index", "version": "0.1.0"}`.

### `app/api/code_index.py` — 11 REST Endpoints
| Method | Path                         | Purpose                          |
|--------|------------------------------|----------------------------------|
| POST   | `/api/projects`              | Create project                   |
| POST   | `/api/projects/{id}/scan`    | Scan & index directory           |
| GET    | `/api/projects`              | List all projects                |
| POST   | `/api/explore`               | 9-action code exploration        |
| GET    | `/api/search/typed`          | Typed search with filters        |
| POST   | `/api/index/file`            | Index single file (IncrementalIndexer) |
| POST   | `/api/index/directory`       | Index directory (IncrementalIndexer) |
| POST   | `/api/index/file-content`    | Index from content string        |
| GET    | `/api/lsp/references`        | Find symbol references           |
| GET    | `/api/lsp/implementation`    | Find interface implementations    |
| GET    | `/api/lsp/hover`             | Hover info for file+line          |

### `app/api/tool.py` — Tool Invocation Protocol
Three endpoints:
- `GET /tool/manifest` — Returns AIDP tool manifest with all 6 capabilities
- `GET /tool/capabilities` — Returns capability details with JSON schemas
- `POST /tool/invoke` — Unified dispatch: reads `capability` from request body, instantiates the correct service, and returns `ToolInvokeResponse`

The `POST /tool/invoke` dispatcher:
```python
if req.capability == "code.search":
    svc = SearchService(db)
    results = await svc.search_symbols(...)
elif req.capability == "code.search.semantic":
    svc = SearchService(db)
    results = await svc.semantic_search(...)
elif req.capability == "code.explore":
    svc = CodeExploreService(db)
    results = await svc.explore(...)
elif req.capability == "code.create_project":
    indexer = Indexer(db)
    project = await indexer.create_project(...)
elif req.capability == "code.index_files":
    indexer = Indexer(db)
    result = await indexer.index_files(project_id, files)
elif req.capability == "code.calls":
    tracer = CallTracer(db)
    callers = await tracer.get_callers(...)
    callees = await tracer.get_callees(...)
```

### `ToolInvokeRequest` / `ToolInvokeResponse`
```python
class ToolInvokeRequest(BaseModel):
    trace_id: Optional[str] = None
    capability: str               # e.g. "code.search"
    context: dict = {}
    input: dict = {}              # parameters for the capability

class ToolInvokeResponse(BaseModel):
    trace_id: str
    tool: str                     # always "code-index"
    capability: str
    success: bool
    output: Any = None
    error: Optional[dict] = None
    elapsed_ms: int = 0
```

## Service Layer Detail

### Indexing Pipeline
```
Scanner.scan_directory(path)
  → detects language, framework
  → walks directory tree
  → computes SHA256 fingerprints
  → returns file list with metadata

Indexer.scan_and_index(project_id, path)
  → iterates files
  → compares fingerprints → skip unchanged
  → calls _index_file() for changed files
  → updates project stats

IncrementalIndexer.index_file(project_id, file_path)
  → reads file, computes hash
  → compares with FileFingerprint
  → parses with TreeSitterParser (AST or regex)
  → creates Node records
  → updates fingerprint
```

### Search Pipeline
```
SearchService.search_symbols()
  → ILIKE matching on name, signature, docstring

SearchService.semantic_search()
  → Step 1: vector_search() via NodeEmbeddingStore
  → Step 2: ILIKE exact search
  → Step 3: Union of vector + exact results
  → Step 4: Score fusion: 0.5*vector + 0.3*exact + 0.2*fuzzy
  → Step 5: Rank and return top_k

  Fallback: if vector search fails → uses exact only (vector_score=0)
```

### Embedding Pipeline
```
EmbeddingService.embed(text)
  → Priority 1: Controller API (BGE-M3 via /embeddings endpoint)
  → Priority 2: Local sentence-transformers (all-MiniLM-L6-v2)
  → Priority 3: Mock (deterministic SHA256+sin hash)

NodeEmbeddingStore.compute_batch(nodes)
  → Build embedding input string per node (name, type, signature, docstring, etc.)
  → Call embed_batch() with all texts
  → Store NodeEmbedding records (JSON-serialized vectors)

NodeEmbeddingStore.vector_search(query, project_id, top_k)
  → Embed query
  → Load all embeddings for project
  → Linear scan with cosine similarity
  → Return top-k (node_id, score) pairs
```

## Model Client (`app/model_client.py`)

Queries the Model Controller at `http://localhost:8883`:
```python
async def get_model_for_task(task_type: str) -> Optional[Dict]:
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{CONTROLLER_URL}/api/models/for-task/{task_type}")
        if resp.status_code == 200:
            return resp.json().get("model")

async def get_embedding_model() -> Optional[Dict]:
    return await get_model_for_task("embedding")
```

## Request/Response Flow

```
Agent/Orchestrator
    │
    ▼
POST /tool/invoke  ──►  tool.py:invoke_tool()
    │                       │
    │                       ├── code.search      → SearchService.search_symbols()
    │                       ├── code.search.semantic → SearchService.semantic_search()
    │                       ├── code.explore     → CodeExploreService.explore()
    │                       ├── code.calls        → CallTracer (callers + callees)
    │                       ├── code.create_project → Indexer.create_project()
    │                       └── code.index_files  → Indexer.index_files()
    │
    ▼
ToolInvokeResponse (JSON)
```

## Database Session Management

```python
# app/db/database.py
engine = create_async_engine("sqlite+aiosqlite:///...", echo=False, pool_pre_ping=True)

async def get_db():
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

Key behaviors:
- Auto-commit on success (in `get_db()`)
- Auto-rollback on exception
- WAL journal mode for concurrent reads
- 5-second busy timeout
- `expire_on_commit=False` to keep objects usable after commit