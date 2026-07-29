# AIDP Controller Configuration Reference

All configuration is managed through environment variables, loaded by Pydantic `BaseSettings` in `app/_config.py` with fallback to the `.env` file.

## Application Settings

| Variable | Default | Description | Used In |
|----------|---------|-------------|---------|
| APP_NAME | `aidp-controller` | Application display name | `main.py` FastAPI title |
| APP_VERSION | `0.1.0` | Application version string | `main.py`, `/health` endpoint |
| DEBUG | `false` | Debug mode (not heavily used) | `_config.py` |
| HOST | `0.0.0.0` | Uvicorn bind address | `main.py` uvicorn.run |
| PORT | `8883` | Uvicorn bind port | `main.py` uvicorn.run |
| DATABASE_URL | *(empty)* | Async PostgreSQL connection string | `database.py` create_async_engine |
| DATABASE_ECHO | `false` | Log all SQL queries | `database.py` engine echo |
| SECRET_KEY | *(empty)* | Application secret for session signing | `_config.py` |
| INVOCATION_TIMEOUT | `30` | Timeout for tool invocations (seconds) | `_config.py` |
| NAS_PATH | `/home/docker/projects` | Base path for project file storage | `nas_storage_service.py` |

## Environment File (`.env.example`)

```
APP_NAME=AIDP Controller
APP_VERSION=0.1.0
DEBUG=false
HOST=0.0.0.0
PORT=8883
DATABASE_URL=postgresql+asyncpg://novel_os:jygame_postgres_01@127.0.0.1:5432/novel_os
DATABASE_ECHO=false
SECRET_KEY=aidp-controller-secret-change-in-production
```

## Runtime Environment Variables (via `os.environ`)

These are read directly from environment, NOT from Pydantic settings:

| Variable | Default | Description | Used In |
|----------|---------|-------------|---------|
| CONTROLLER_SESSION_KEY | `change-me` | Secret for Starlette SessionMiddleware | `main.py` |
| CONTROLLER_URL | `http://localhost:8883` | Self-referencing URL for tool invocation from init tasks | `projects_new.py` `_run_code_index`, `_run_local_setup` |

## Tool Endpoint Environment Variables (in `tool_invoker.py`)

These configure where the controller finds each tool. Used as fallback when the tool is not found in the tool_registry database:

| Variable | Default | Tool |
|----------|---------|------|
| SKILLROUTER_URL | `http://localhost:8788` | skill-router |
| KNOWLEDGE_URL | `http://localhost:18081` | knowledge-tool |
| MEMORY_URL | `http://localhost:18085` | memory-tool |
| ASSET_URL | `http://localhost:18082` | asset-tool |
| SANDBOX_URL | `http://localhost:18083` | sandbox-tool |
| QUALITY_URL | `http://localhost:18084` | quality-tool |

## Database Connection Pool

Configured in `database.py`:

| Parameter | Value |
|-----------|-------|
| pool_size | `5` |
| max_overflow | `10` |
| expire_on_commit | `false` |

The connection string format is: `postgresql+asyncpg://user:password@host:port/database`

## Context Pipeline Configuration

These are hardcoded defaults in `context_pipeline.py` and `context_assembly.py`:

| Parameter | Value | Location |
|-----------|-------|----------|
| Context cache TTL | 300 seconds (5 min) | `ContextCache(ttl_seconds=300)` |
| Max context tokens | 8000 | `ContextAssembler(max_tokens=8000)` |
| Retry max attempts | 3 | `RetryConfig(max_retries=3)` |
| Retry strategy | Exponential backoff | `RetryStrategy.EXPONENTIAL` |
| Memory retrieval limit | 5 | Hardcoded in pipeline |
| Knowledge retrieval top_k | 5 | Hardcoded in pipeline |
| Asset retrieval top_k | 3 | Hardcoded in pipeline |
| Skill matching top_k | 6 | Hardcoded in pipeline |

## In-Memory System Settings

The `/api/settings` endpoint uses in-memory storage (not the DB `system_settings` table):

| Key | Default | Description |
|-----|---------|-------------|
| siteName | `AIDP` | Site display name |
| siteDescription | `AI DevOps Platform` | Site description |
| allowRegistration | `false` | Allow public registration |
| requireApproval | `true` | Require admin approval |

## MCP Session Manager

| Parameter | Value |
|-----------|-------|
| Session timeout | 30 minutes |
| Default session ID | `"default"` (when no session_id provided) |

## Init Task Definitions

Defined in `models/project_new.py` as `INIT_TASKS`:

| Task ID | Name | Phase | Dependencies |
|---------|------|-------|-------------|
| code_index | Code indexing | 1 | none |
| tech_analysis | Tech stack analysis | 1 | none |
| mcp_register | MCP registration check | 1 | none |
| doc_import | Document import | 2 | code_index |
| official_docs | Official docs import | 2 | tech_analysis |
| rules_extract | Rule extraction | 2 | doc_import |
| agent_setup | Agent creation | 2 | none |
| file_watcher | File watcher install | 3 | none |
| git_hook | Git hook install | 3 | none |

## Port Map (Defaults)

| Component | Port |
|-----------|------|
| Controller | 8883 |
| skill-router | 8788 |
| knowledge-tool | 18081 |
| asset-tool | 18082 |
| sandbox-tool | 18083 |
| quality-tool | 18084 |
| memory-tool | 18085 |
| code-index | 18086 (health only) |
| doc-index | 18087 |