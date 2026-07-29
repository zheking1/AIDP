# Doc Index API Reference

## Tool Protocol (`tool.py`)

### `GET /tool/manifest`

Returns tool manifest with 5 capabilities.

### `GET /tool/capabilities`

Returns all capabilities with schemas.

### `POST /tool/invoke`

Unified capability invocation endpoint. Request:

```json
{
    "trace_id": "tr_abc",
    "capability": "doc.create",
    "context": {},
    "input": { "title": "...", "content": "# Markdown..." }
}
```

---

## Capability Reference

### 1. `doc.create`

- **Timeout**: 10000ms
- **Permission**: `doc:write`

**Required inputs**: `title`, `content`

**Optional inputs**: `url`, `source` (default `manual`), `language`, `framework`

**Process**:
1. Validates `title` and `content` are non-empty
2. Uses `DocParser` to parse markdown content:
   - Extracts parsed title (H1), summary, word count
3. Creates `DocPage` record:
   - `title`: parsed title or provided title
   - `url`: optional URL
   - `content`: full markdown content
   - `summary`: extracted from parser
   - `word_count`: from parser
   - `source`: source type
   - `language` / `framework`: optional
4. Commits and refreshes the record

**Response**:
```json
{
    "id": 1,
    "title": "Getting Started",
    "language": "python",
    "framework": "fastapi"
}
```

### 2. `doc.search`

- **Timeout**: 5000ms
- **Permission**: `doc:read`

**Required inputs**: `query`

**Optional inputs**: `limit` (default 20)

Uses `SearchService.search()` for text-based search.

### 3. `doc.get`

- **Timeout**: 3000ms
- **Permission**: `doc:read`

**Required inputs**: `doc_id` (integer)

Returns full document data or `NOT_FOUND` error.

### 4. `doc.list`

- **Timeout**: 5000ms
- **Permission**: `doc:read`

No required inputs. Returns all documentation pages via `SearchService.get_all_pages()`.

### 5. `doc.wiki`

- **Timeout**: 10000ms
- **Permission**: `doc:read`

**Optional inputs**: `language`, `framework`

Generates wiki with pages + table of contents, filtered by language/framework.

---

## REST API (`doc_index.py`)

### Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/docs` | Create a documentation page |
| `GET` | `/api/docs` | List all documentation pages |
| `GET` | `/api/docs/{doc_id}` | Get a single page by ID |

### Code Linking

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/docs/{doc_id}/link` | Link doc to code entities |
| `GET` | `/api/docs/{doc_id}/links` | Get all code links for a doc |

### Drift Detection

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/docs/{doc_id}/drift` | Submit code changes for drift analysis |
| `GET` | `/api/docs/{doc_id}/drifts` | Get active drifts for a doc |

### Wiki

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/wiki` | Generate wiki with optional `language` and `framework` query params |

---

## DocParser (`parser.py`)

Used internally by `doc.create`:

```python
class DocParser:
    def parse_markdown(content: str, url: str = None) -> dict:
        # Returns { "title": str, "summary": str, "word_count": int }
```

- Extracts H1 heading as title
- Generates summary from first non-heading content
- Counts total words in content

---

## Error Responses

All invoke endpoints return:

```json
{
    "trace_id": "tr_xxx",
    "tool": "doc-index",
    "success": false,
    "error": {
        "code": "INVALID_INPUT | NOT_FOUND | INTERNAL_ERROR",
        "message": "..."
    },
    "elapsed_ms": 42
}
```

REST endpoints return standard HTTP status codes:
- `400`: Invalid input (missing title/content, missing code_nodes)
- `404`: Document not found