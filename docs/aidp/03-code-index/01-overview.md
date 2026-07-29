# Code Index — Overview

## What It Is

Code Index is the **AST+vector+graph hybrid code intelligence tool** in the AIDP platform. It parses source code (Python, Java, TypeScript/JavaScript) to build a queryable graph of symbols, traces call chains, and enables semantic code search powered by embeddings.

It serves as the **central code knowledge store** that all other tools (DEBUG, UNIT-TEST, WEB-SERVER, etc.) query to understand codebases.

## Tech Stack

| Layer        | Technology                         |
|--------------|------------------------------------|
| Runtime      | Python 3.10+                       |
| Web Framework| FastAPI (async)                    |
| Database     | SQLite via SQLAlchemy (async)      |
| AST Parsing  | Tree-Sitter (primary) + regex (fallback) |
| Embeddings   | BGE-M3 (1024-dim, via 3-tier priority) |
| Port         | `18086`                            |

## Capabilities (6)

| Capability             | What It Does                                      |
|------------------------|---------------------------------------------------|
| `code.search`          | Exact/ILIKE symbol search across name, signature, docstring |
| `code.search.semantic` | Fusion search: vector + exact + fuzzy scoring     |
| `code.explore`         | 9 actions to navigate code structure              |
| `code.calls`           | Bidirectional call chain tracing (callers + callees) |
| `code.index_files`     | Batch index files from uploaded content           |
| `code.create_project`  | Register a new project in the database            |

## Core Services (in `app/services/`)

| Service                  | File                     | Role                                    |
|--------------------------|--------------------------|-----------------------------------------|
| `Indexer`                | `indexer.py`             | Batch file indexing, AST extraction      |
| `IncrementalIndexer`     | `incremental_indexer.py` | Single-file/directory indexing with Tree-Sitter |
| `SearchService`          | `search_service.py`      | Exact + semantic fusion search          |
| `CodeExploreService`     | `code_explore.py`        | 9-action code navigation                |
| `CallTracer`             | `call_tracer.py`         | Recursive call/caller tracing            |
| `ImpactAnalyzer`         | `call_tracer.py`         | Impact & risk assessment                |
| `EmbeddingService`       | `embedding_service.py`   | 3-tier embedding: controller → local → mock |
| `NodeEmbeddingStore`     | `node_embedding_store.py`| Embedding persistence, batch compute, vector search |
| `TreeSitterParser`       | `tree_sitter_parser.py`  | AST parsing with Tree-Sitter + regex fallback |
| `Scanner`                | `scanner.py`             | Directory scanning, language/framework detection |
| `LSPClient`              | `lsp_client.py`          | LSP-like queries (references, hover, implementation) |

## Configuration

```python
# app/config.py
APP_NAME: str = "Code Index Tool"
APP_VERSION: str = "0.1.0"
PORT: int = 18086
DATABASE_URL: str = "sqlite+aiosqlite:///./data/code_index.db"
```

Database uses **SQLite WAL mode** for concurrency, with a 5-second busy timeout (`PRAGMA busy_timeout=5000`).