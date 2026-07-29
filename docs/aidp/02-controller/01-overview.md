# Controller Overview

## What It Is

AIDP Controller (`apps/controller/`) is the central orchestrator of the AIDP platform. It serves as:

1. **Central Orchestrator** -- Coordinates all AIDP tools (sandbox, quality, memory, knowledge, skill-router, asset, code-index, doc-index) through a unified interface.
2. **API Gateway** -- Exposes a REST API and WebSocket endpoint for tool registration, invocation, project management, auth, and audit.
3. **MCP Server** -- Implements the Model Context Protocol (MCP) via `fastmcp`, allowing AI agents to discover and call tools through a structured session-aware interface.

## Key Services

| Service | Description |
|---------|-------------|
| **Tool Registry** | Register, discover, health-check, enable/disable, and sync capabilities of distributed tools. |
| **Tool Invoker** | Route invocation requests to the correct tool endpoint via HTTP with retry and fallback. |
| **5-Stage Context Pipeline** | Assemble rich context for LLM calls: Load Instructions → Intent Analysis → Staged Retrieval → Skill Matching → Context Assembly. |
| **Project Management** | CRUD projects, members, settings, init tasks, access logs, ID mappings, and verify health checks across tools. |
| **Authentication & Authorization** | User management (CRUD, roles, status), session-based web login, API keys, JWT auth, RBAC permissions. |
| **Knowledge Base** | Manage knowledge bases, documents, chunks, search logs, bindings, and document templates. |
| **Memory System** | Store and retrieve project memories with relations, access tracking, and context packages. |
| **Skills & Rules** | Registry of AI skills and coding rules with scope (global/personal/project), versioning, review, and promotion. |
| **Agents** | Agent definitions combining skills, rules, and knowledge bases. |
| **Assets** | Code snippet / template asset management with tagging. |
| **Workflows** | Workflow definitions, steps, executions, and step execution tracking. |
| **Models** | Unified LLM model registry shared across all tools. |
| **NAS Storage** | Project file storage, listing, reading, writing, and Git sync. |
| **Document Classification** | Auto-classify imported documents into knowledge/rules/skills/agents. |
| **Reviews** | Submit, list, approve, and reject review items. |
| **Audit Logging** | Track all important operations with structured audit trail. |
| **Metrics** | Prometheus metrics endpoint for request counts, latencies, tool invocations. |

## File Structure

```
apps/controller/
├── app/
│   ├── main.py                    # FastAPI app entry point, lifespan, router registration
│   ├── _config.py                 # Settings (Pydantic BaseSettings)
│   ├── api/                       # REST API route modules
│   │   ├── health.py              # GET /health
│   │   ├── tools.py               # /api/tools/* (CRUD, health, sync, invoke)
│   │   ├── auth.py                # /api/auth/* (login, logout, users, API keys)
│   │   ├── metrics.py             # GET /metrics (Prometheus)
│   │   ├── audit.py               # /api/audit/*
│   │   ├── models.py              # /api/models/* (LLM model CRUD)
│   │   ├── settings.py            # /api/settings/*
│   │   ├── configs.py             # /api/projects/{id}/configs/*
│   │   ├── reviews.py             # /api/reviews/*
│   │   ├── nas_storage.py         # /api/projects/{id}/code-path, files/*
│   │   ├── instructions.py        # /api/instructions/* (5-stage pipeline)
│   │   ├── classification.py      # /api/classification/classify, import
│   │   ├── ws_logs.py             # /ws/logs (WebSocket)
│   │   └── projects.py            # (legacy)
│   ├── routers/
│   │   └── projects_new.py        # /api/projects/* (new unified API)
│   ├── mcp/
│   │   ├── server.py              # FastMCP server with 6 tools
│   │   └── session_manager.py     # Enforces aidp_context-first ordering
│   ├── modules/                   # Domain module models & routes
│   │   ├── knowledge/             # Knowledge base, documents, chunks, templates
│   │   ├── memory/                # Memory entries, relations, context packages
│   │   ├── skills/                # Skills, skill groups, evolutions
│   │   ├── rules/                 # Rules, rule groups
│   │   ├── agents/                # Agent definitions + M2M joins
│   │   ├── assets/                # Assets + tags
│   │   ├── workflows/             # Workflows, steps, executions
│   │   ├── sandbox/               # Code execution records
│   │   ├── quality/               # Quality check results
│   │   └── example/               # Example module
│   ├── models/                    # SQLAlchemy models (non-module)
│   │   ├── project.py             # Legacy app_projects/app_project_*
│   │   ├── project_new.py         # New aidp_projects + members + init tasks
│   │   ├── review.py              # review_queue
│   │   └── instructions.py        # agent_instructions
│   ├── db/
│   │   ├── database.py            # Async engine, session factory, Base
│   │   ├── models.py              # ToolRegistry, ToolInvocation
│   │   ├── auth_models.py         # User, Session, API keys, AuditLog, Permissions
│   │   └── init_db.py             # DB initialization
│   ├── services/
│   │   ├── tool_registry.py       # Tool CRUD, health, sync
│   │   ├── tool_invoker.py        # HTTP invocation + history
│   │   ├── tool_retry.py          # Retry logic + fallback
│   │   ├── context_pipeline.py    # 5-stage pipeline orchestration
│   │   ├── context_cache.py       # LRU TTL cache for context
│   │   ├── context_assembly.py    # Priority/dedup/compress context
│   │   ├── auth_service.py        # Authentication service
│   │   ├── permission_service.py  # Permission checks
│   │   ├── model_service.py       # LLM model CRUD
│   │   ├── project_service.py     # Project operations
│   │   ├── project_init_service.py # Project init logic
│   │   ├── review_service.py      # Review workflow
│   │   ├── config_service.py      # Project config service
│   │   ├── nas_storage_service.py # File storage operations
│   │   ├── doc_classifier.py      # Document classification
│   │   ├── semantic_search.py     # Embedding generation
│   │   └── seed_data.py           # Template seeding
│   ├── security/
│   │   ├── jwt_auth.py            # JWT token handling
│   │   ├── secret_manager.py      # Secret encryption
│   │   ├── validation.py          # Input validation
│   │   ├── concurrency.py         # Concurrency control
│   │   └── call_stats.py          # Call statistics
│   ├── core/
│   │   ├── utils.py               # gen_uuid, utcnow
│   │   ├── permissions.py         # RBAC permission decorators
│   │   ├── menu.py                # Menu configuration
│   │   ├── context.py             # Context helpers
│   │   └── config_loader.py       # Config file loader
│   └── web/
│       ├── routes.py              # Web UI routes
│       ├── auth.py                # Web auth endpoints
│       └── static/                # Static assets
├── tests/
├── migrations/
└── .env / .env.example
```

## How It Connects

```
                          ┌──────────────────────┐
                          │   AI Agent / Client   │
                          └──────┬───────┬───────┘
                                 │ HTTP  │ MCP (streamable-http)
                                 ▼       ▼
                    ┌────────────────────────────┐
                    │     AIDP Controller        │
                    │  (FastAPI + FastMCP)       │
                    │                            │
                    │  REST:   /api/tools/*      │
                    │          /api/projects/*    │
                    │          /api/auth/*        │
                    │          /api/knowledge/*   │
                    │          /api/skills/*      │
                    │          /api/rules/*       │
                    │          /api/agents/*      │
                    │          /api/workflows/*   │
                    │          /api/assets/*      │
                    │          /api/models/*      │
                    │          /api/memory/*      │
                    │                            │
                    │  MCP:    aidp_context       │
                    │          invoke_tool_mcp    │
                    │          list_registered_   │
                    │          check_tool_health  │
                    │          sync_tool_cap*     │
                    │          aidp_init          │
                    │          aidp_instructions  │
                    │          manage_models      │
                    └───┬───┬───┬───┬───┬───┬───┘
               ┌────────┘   │   │   │   │   └────────┐
               ▼            ▼   ▼   ▼   ▼            ▼
     ┌──────────────┐   ┌────────────────────┐  ┌──────────┐
     │  PostgreSQL   │   │  Tool Endpoints    │  │  NAS     │
     │  (all data)   │   │  - sandbox-tool    │  │  Storage │
     └──────────────┘   │  - quality-tool     │  └──────────┘
                        │  - memory-tool      │
                        │  - knowledge-tool   │
                        │  - skill-router     │
                        │  - asset-tool       │
                        │  - code-index       │
                        │  - doc-index        │
                        └────────────────────┘
```

- **Controller ↔ Tools**: HTTP-based invocation through the tool registry. Tools register their endpoints; controller health-checks and invokes them.
- **Controller ↔ Agents**: MCP protocol (`streamable-http`) mounted at `/mcp`. Agents call `aidp_context` first, then use `invoke_tool_mcp` for operations.
- **Controller ↔ Database**: Async PostgreSQL via SQLAlchemy async engine. All project data, knowledge, memory, skills, rules, agents, workflows, and operational logs stored here.
- **Controller ↔ NAS**: File-based project storage at configurable `NAS_PATH`, used for code browsing and Git sync.