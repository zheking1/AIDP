# Doc Index Tool - Overview

## Purpose

Doc Index Tool is an AIDP platform component for documentation management, code linking, drift detection, and wiki generation. It uses SQLite for storage.

## Configuration (`app/config.py`)

| Config | Default | Description |
|--------|---------|-------------|
| `APP_NAME` | `Doc Index Tool` | Application name |
| `APP_VERSION` | `0.1.0` | Version |
| `PORT` | `18087` | Service port |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/doc_index.db` | SQLite database path |

## Capabilities

| # | Capability | Description | Permission |
|---|------------|-------------|------------|
| 1 | `doc.create` | Create a documentation page | `doc:write` |
| 2 | `doc.search` | Search documentation pages | `doc:read` |
| 3 | `doc.get` | Get a page by ID | `doc:read` |
| 4 | `doc.list` | List all documentation pages | `doc:read` |
| 5 | `doc.wiki` | Generate wiki with filters | `doc:read` |

## Architecture

```
User/Agent → API Layer (FastAPI)
    ├── POST /api/docs           → create_doc (parser + DocPage)
    ├── GET /api/docs            → list all pages
    ├── GET /api/docs/{id}       → get single page
    ├── POST /api/docs/{id}/link → link code references
    ├── POST /api/docs/{id}/drift → detect doc drift
    └── GET /api/wiki            → generate wiki (language/framework filters)
         ↓
    Services: parser / search_service / linker / drift_detector / wiki_generator
         ↓
    Storage: SQLite via aiosqlite
```

## Key Features

- **Markdown Parsing**: Extracts title, summary, word count from markdown content
- **Code Linking**: Maps documentation to code nodes (class/function/method references)
- **Drift Detection**: Monitors code changes that may invalidate documentation sections
- **Wiki Generation**: Creates structured wiki output with language/framework filtering
- **Search**: Text-based search over documentation pages