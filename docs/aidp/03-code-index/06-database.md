# Code Index — SQLite Database Schema

5 tables in `data/code_index.db`, managed by SQLAlchemy ORM with async SQLite (WAL mode).

---

## Database Configuration

```python
# app/db/database.py
engine = create_async_engine("sqlite+aiosqlite:///./data/code_index.db", echo=False, pool_pre_ping=True)

# On connect: enable WAL mode + 5s busy timeout
PRAGMA journal_mode=WAL
PRAGMA busy_timeout=5000

# Session: auto-commit on success, auto-rollback on exception
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
```

---

## Table 1: `projects`

Stores registered project metadata.

```python
class Project(Base):
    __tablename__ = "projects"
```

| Column        | Type          | Default      | Nullable | Description                          |
|---------------|---------------|--------------|----------|--------------------------------------|
| `id`          | INTEGER       | autoincrement| NOT NULL | Primary key                          |
| `name`        | VARCHAR(256)  | —            | NOT NULL | Project display name                 |
| `path`        | VARCHAR(1024) | —            | NOT NULL | Filesystem path (UNIQUE constraint)  |
| `language`    | VARCHAR(32)   | NULL         | Yes      | Detected language (e.g. "python")    |
| `framework`   | VARCHAR(64)   | NULL         | Yes      | Detected framework (e.g. "fastapi")  |
| `status`      | VARCHAR(32)   | "scanning"   | Yes      | "scanning" / "indexed"               |
| `file_count`  | INTEGER       | 0            | Yes      | Number of files in project           |
| `node_count`  | INTEGER       | 0            | Yes      | Cumulative node count                |
| `last_scan_at`| DATETIME      | NULL         | Yes      | Last scan timestamp                  |
| `created_at`  | DATETIME      | now()        | Yes      | Auto-set on creation                 |
| `updated_at`  | DATETIME      | now()        | Yes      | Auto-updated on change               |

**Constraints:**
- `UNIQUE(path)` — prevents duplicate projects by path

**Creation flow:**
```python
# Dedup by path
project = await db.execute(select(Project).where(Project.path == path))
if existing:
    return existing  # Return existing project
project = Project(name=name, path=path)
db.add(project)
await db.commit()
```

---

## Table 2: `nodes`

The core table — every code symbol, file, and class is a node.

```python
class Node(Base):
    __tablename__ = "nodes"
```

| Column            | Type          | Default      | Nullable | Description                             |
|-------------------|---------------|--------------|----------|-----------------------------------------|
| `id`              | INTEGER       | autoincrement| NOT NULL | Primary key                             |
| `project_id`      | INTEGER       | —            | NOT NULL | FK-like reference to projects           |
| `node_type`       | VARCHAR(32)   | —            | NOT NULL | "file" / "class" / "function" / "method"|
| `name`            | VARCHAR(512)  | —            | NOT NULL | Simple name (e.g. "handle_error")       |
| `qualified_name`  | VARCHAR(1024) | NULL         | Yes      | Scoped name (e.g. "src/app.py::handle_error") |
| `file_path`       | VARCHAR(1024) | NULL         | Yes      | Relative file path                      |
| `line_start`      | INTEGER       | NULL         | Yes      | Starting line number (1-indexed)        |
| `line_end`        | INTEGER       | NULL         | Yes      | Ending line number                      |
| `language`        | VARCHAR(32)   | NULL         | Yes      | "python" / "java" / "typescript" / ...  |
| `framework`       | VARCHAR(64)   | NULL         | Yes      | Detected framework                      |
| `metadata`        | JSON          | {}           | Yes      | Arbitrary JSON metadata (column alias: `metadata_`) |
| `parent_id`       | INTEGER       | NULL         | Yes      | Pointer to parent node (for nesting)    |
| `checksum`        | VARCHAR(64)   | NULL         | Yes      | SHA256[0:16] of file content            |
| `signature`       | TEXT          | NULL         | Yes      | Function/method signature string         |
| `docstring`       | TEXT          | NULL         | Yes      | Documentation string                     |
| `return_type`     | VARCHAR(256)  | NULL         | Yes      | Return type annotation                   |
| `params_json`     | TEXT          | NULL         | Yes      | JSON-serialized parameter list           |
| `file_hash`       | VARCHAR(64)   | NULL         | Yes      | SHA256 hex of file bytes (full hash)     |
| `created_at`      | DATETIME      | now()        | Yes      | Auto-set on creation                     |
| `updated_at`      | DATETIME      | now()        | Yes      | Auto-updated on change                   |

**Indexes:**
```python
__table_args__ = (
    Index("idx_node_project", "project_id", "node_type"),   # Fast lookup by project + type
    Index("idx_node_file", "project_id", "file_path"),       # Fast lookup by project + file
)
```

**Node Type Values:**
- `"file"` — Represents a source file
- `"class"` — A class definition
- `"function"` — A function or method definition
- `"method"` — (Used by IncrementalIndexer)

**Qualified Name Format:**
```
{file_path}::{name}
```
Example: `src/services/auth.py::authenticate_user`

---

## Table 3: `edges`

Directed graph edges connecting nodes.

```python
class Edge(Base):
    __tablename__ = "edges"
```

| Column        | Type          | Default      | Nullable | Description                             |
|---------------|---------------|--------------|----------|-----------------------------------------|
| `id`          | INTEGER       | autoincrement| NOT NULL | Primary key                             |
| `project_id`  | INTEGER       | —            | NOT NULL | FK-like reference to projects           |
| `source_id`   | INTEGER       | —            | NOT NULL | Source node ID (tail of arrow)          |
| `target_id`   | INTEGER       | —            | NOT NULL | Target node ID (head of arrow)          |
| `edge_type`   | VARCHAR(32)   | —            | NOT NULL | Edge type (see below)                   |
| `metadata`    | JSON          | {}           | Yes      | Arbitrary JSON metadata (column alias: `metadata_`) |
| `created_at`  | DATETIME      | now()        | Yes      | Auto-set on creation                    |

**No DB-level FK constraints** — foreign keys are handled at the application level due to SQLite+SQLAlchemy async limitations.

**Edge Types:**

| Type         | Source       | Target       | Meaning                                |
|--------------|--------------|--------------|----------------------------------------|
| `contains`   | file node    | class/func   | File contains this symbol              |
| `calls`      | function A   | function B   | A calls B (intra-file only for batch index) |
| `imports`    | file node    | 0 (virtual)  | File imports a module                  |
| `extends`    | class A      | class B      | A extends B                            |
| `implements` | class A      | interface B  | A implements B                         |
| `references` | node A       | node B       | General reference                      |

**Migration:** All edge_type values are normalized to lowercase (`UPDATE edges SET edge_type = LOWER(edge_type)`) at startup.

**Import edges special case:** `target_id = 0` is a virtual root node. `metadata` carries `{"import_name": "os.path"}`.

---

## Table 4: `file_fingerprints`

Tracks which files have been indexed and their content hashes.

```python
class FileFingerprint(Base):
    __tablename__ = "file_fingerprints"
```

| Column            | Type          | Default      | Nullable | Description                          |
|-------------------|---------------|--------------|----------|--------------------------------------|
| `id`              | INTEGER       | autoincrement| NOT NULL | Primary key                          |
| `project_id`      | INTEGER       | —            | NOT NULL | FK-like reference to projects        |
| `file_path`       | VARCHAR(1024) | —            | NOT NULL | Relative file path                   |
| `file_hash`       | VARCHAR(64)   | —            | NOT NULL | SHA256 hash of file content          |
| `last_indexed_at` | DATETIME      | now()        | NOT NULL | When file was last indexed           |
| `node_count`      | INTEGER       | 0            | Yes      | Number of nodes from this file       |

**Constraints:**
```python
UniqueConstraint("project_id", "file_path", name="uq_fingerprint_file")
```

**Dedup Logic:**
```python
fp = await db.execute(
    select(FileFingerprint).where(
        FileFingerprint.project_id == project_id,
        FileFingerprint.file_path == file_path,
    )
)
if fp and fp.file_hash == new_checksum:
    return {"skipped": True}  # Skip indexing
```

**Update flow:**
```python
if fp:
    fp.file_hash = checksum
    fp.last_indexed_at = datetime.now(timezone.utc)
    fp.node_count = nodes_created
else:
    db.add(FileFingerprint(
        project_id=project_id,
        file_path=file_path,
        file_hash=checksum,
        last_indexed_at=datetime.now(timezone.utc),
        node_count=nodes_created,
    ))
```

---

## Table 5: `node_embeddings`

Stores vector embeddings for nodes, supporting semantic search.

```python
class NodeEmbedding(Base):
    __tablename__ = "node_embeddings"
```

| Column            | Type          | Default      | Nullable | Description                          |
|-------------------|---------------|--------------|----------|--------------------------------------|
| `id`              | INTEGER       | autoincrement| NOT NULL | Primary key                          |
| `node_id`         | INTEGER       | —            | NOT NULL | FK-like reference to nodes           |
| `project_id`      | INTEGER       | —            | NOT NULL | FK-like reference to projects        |
| `embedding`       | TEXT          | —            | NOT NULL | JSON-serialized float array          |
| `embedding_model` | VARCHAR(64)   | —            | NOT NULL | Model name (e.g. "BAAI/bge-m3")      |
| `content_hash`    | VARCHAR(64)   | —            | NOT NULL | Hash of the embedding input text     |
| `created_at`      | DATETIME      | now()        | Yes      | Auto-set on creation                 |

**Constraints:**
```python
UniqueConstraint("node_id", "embedding_model", name="uq_node_embedding")
```
Each node can have at most one embedding per model. Switching models creates new rows (not updates) due to the unique constraint — though in practice, the current code always inserts without checking for existing.

**Embedding Format:**
The `embedding` column stores a JSON string:
```json
[0.0123, -0.0456, 0.0789, ...]
```
For BGE-M3: 1024 dimensions. For local all-MiniLM-L6-v2: 384 dimensions.

**In practice:**
- Embeddings are created by `NodeEmbeddingStore.compute_batch()` during `_index_file_content()`
- Only class and function nodes get embeddings (file nodes do not)
- Embeddings are loaded into memory by `vector_search()` via a full table scan:
  ```python
  result = await self.db.execute(
      select(NodeEmbedding).where(NodeEmbedding.project_id == project_id)
  )
  embeddings = result.scalars().all()
  ```
  This means vector search runs as a linear scan in Python, not via SQLite vector extensions.

---

## Migration Scripts

### `migrate_add_columns.py`
Adds 5 columns to `nodes` table (if not already present):
```python
NEW_NODE_COLUMNS = [
    ("signature", "TEXT"),
    ("docstring", "TEXT"),
    ("return_type", "VARCHAR(256)"),
    ("params_json", "TEXT"),
    ("file_hash", "VARCHAR(64)"),
]
```
Idempotent — silently skips columns that already exist.

### `migrate_edge_types.py`
Normalizes all `edge_type` values to lowercase:
```sql
UPDATE edges SET edge_type = LOWER(edge_type) WHERE edge_type != LOWER(edge_type)
```

---

## Entity Relationship Diagram

```
projects (1) ──────< nodes (N)
    │                   │
    │                   ├── node_embeddings (1:1)
    │                   │
    │                   ├── edges [source_id] (N)
    │                   │       └── target_id → nodes.id
    │                   │
    │                   └── file_fingerprints (1:1 per file_path)
    │
    └──────< edges (by project_id)
    └──────< file_fingerprints (by project_id)
    └──────< node_embeddings (by project_id)
```

Note: All relationships are soft (no DB-enforced foreign keys). Cascading deletes and referential integrity are handled at the application layer.