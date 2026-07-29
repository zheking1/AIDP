# Wiki Generation

## WikiGenerator (`wiki_generator.py`)

Generates structured wiki output from documentation pages with optional language and framework filters.

### Constructor

```python
class WikiGenerator:
    def __init__(self, db: AsyncSession)
```

Takes an async SQLAlchemy session for database access.

### `generate_wiki(language=None, framework=None) -> Dict`

Main generation method.

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `language` | string | No | Filter by programming language (e.g., `python`, `javascript`) |
| `framework` | string | No | Filter by framework (e.g., `fastapi`, `react`) |

**Process**:

1. Builds a `select(DocPage)` query
2. Applies optional `language` and `framework` WHERE clauses
3. Fetches all matching pages from the database
4. Iterates over results to build the wiki structure

**Output Structure**:

```json
{
    "pages": [
        {
            "id": 1,
            "title": "Getting Started",
            "summary": "A guide to getting started with the project",
            "url": "/docs/getting-started"
        }
    ],
    "toc": [
        {
            "title": "Getting Started",
            "url": "/wiki/1"
        }
    ]
}
```

**Components**:
- `pages`: Full page records with `id`, `title`, `summary`, and `url`
- `toc`: Table of contents entries with `title` and `/wiki/{id}` URL format

---

## API Endpoints

### `GET /api/wiki`

```
GET /api/wiki?language=python&framework=fastapi
```

Standard REST endpoint exposed via `doc_index.py`:

```python
@router.get("/api/wiki")
async def generate_wiki(language: str = None, framework: str = None, db: AsyncSession = Depends(get_db)):
    generator = WikiGenerator(db)
    wiki = await generator.generate_wiki(language, framework)
    return JSONResponse(content=wiki)
```

### Via Tool Protocol

```python
capability: "doc.wiki"
input: { "language": "python", "framework": "fastapi" }
```

Available as the `doc.wiki` capability in `tool.py` with a 10000ms timeout.

---

## Use Cases

1. **Full documentation site**: Call without filters to get all pages
2. **Language-specific docs**: Filter by `language=python` for Python-only guides
3. **Framework-specific docs**: Filter by `framework=react` for React component docs
4. **Combined filters**: Both `language` and `framework` for precise filtering