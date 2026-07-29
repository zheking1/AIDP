# Doc Index Database Schema

All tables use SQLite via `aiosqlite` with SQLAlchemy async engine.

---

## `doc_pages` - Documentation Pages

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment primary key |
| `title` | String(512) | Page title (NOT NULL) |
| `url` | String(1024) UNIQUE | Source URL or slug |
| `content` | Text | Full markdown/page content |
| `summary` | String(2048) | Extracted summary |
| `language` | String(32) | Programming language (e.g., `python`) |
| `framework` | String(64) | Framework (e.g., `fastapi`) |
| `source` | String(64) | Source type: `wiki`, `markdown`, `github`, `api` |
| `word_count` | Integer | Word count (default 0) |
| `created_at` | DateTime | Creation time (server default `func.now()`) |
| `updated_at` | DateTime | Last update (auto-updated on change) |

**Primary key**: Auto-increment integer.

**Unique constraint**: `url` must be unique.

---

## `doc_sections` - Document Sections

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment primary key |
| `doc_id` | Integer | Foreign key to `doc_pages.id` |
| `heading` | String(256) | Section heading text |
| `content` | Text | Section content |
| `level` | Integer | Heading level (1-6, default 1) |
| `parent_id` | Integer | Parent section ID (hierarchical) |
| `created_at` | DateTime | Creation time |

Sections represent the hierarchical structure of a document, parsed from markdown headings.

---

## `code_links` - Code References

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment primary key |
| `doc_id` | Integer | Foreign key to `doc_pages.id` |
| `node_type` | String(32) | Code entity type: `class`, `function`, `method` |
| `node_name` | String(512) | Entity name |
| `file_path` | String(1024) | Source file path |
| `line_start` | Integer | Starting line number |
| `line_end` | Integer | Ending line number |
| `language` | String(32) | Programming language |
| `confidence` | Float | Match confidence 0.0-1.0 (default 0.0) |
| `created_at` | DateTime | Creation time |

Links documentation to specific code entities for traceability.

---

## `doc_drifts` - Documentation Drift Records

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment primary key |
| `doc_id` | Integer | Foreign key to `doc_pages.id` |
| `section_heading` | String(256) | Name of the outdated section |
| `drift_score` | Float | Severity score 0.0-1.0 (default 0.0) |
| `status` | String(32) | Status: `detected` (default) |
| `detected_at` | DateTime | Detection timestamp (default `func.now()`) |
| `resolved_at` | DateTime | Resolution timestamp (nullable) |

Tracks when code changes make documentation sections outdated.

---

## ER Diagram

```
doc_pages (1) ──< (N) doc_sections   [hierarchical via parent_id]
doc_pages (1) ──< (N) code_links     [code entity references]
doc_pages (1) ──< (N) doc_drifts     [stale section tracking]
```

All tables are linked to `doc_pages` via `doc_id` foreign key (integer, not constrained as formal FK in schema but used as logical reference).

---

## Database Engine

```python
DATABASE_URL = "sqlite+aiosqlite:///./data/doc_index.db"
```

- **Engine**: SQLite via `aiosqlite` async driver
- **Storage**: Local file at `./data/doc_index.db`
- **Auto-creation**: Tables created by `init_db.py` on startup
- **Timestamps**: All use `server_default=func.now()` for automatic generation