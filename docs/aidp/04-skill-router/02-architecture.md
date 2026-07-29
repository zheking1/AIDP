# Skill Router — Architecture

## Directory Layout

```
tools/skill-router/
├── app/
│   ├── main.py                    # FastAPI app + MCP server mount
│   ├── config.py                  # Pydantic settings (Settings class)
│   ├── model_client.py            # Controller model config fetcher
│   ├── exceptions.py              # Typed exceptions + error handling helpers
│   ├── api/
│   │   ├── tool.py                # /tool/manifest, /tool/capabilities, /tool/invoke
│   │   └── routes.py              # REST API: skills CRUD, skill groups, rule groups, import
│   ├── mcp/
│   │   └── tools.py               # 25+ MCP tools registered via FastMCP
│   ├── db/
│   │   ├── models.py              # 12 SQLAlchemy ORM models
│   │   ├── database.py            # AsyncEngine + session factory
│   │   └── init_db.py             # Schema migration + seed data
│   ├── services/
│   │   ├── resolve_service.py     # Core resolve pipeline
│   │   ├── skill_service.py       # Skill CRUD
│   │   ├── rule_service.py        # Rule CRUD
│   │   ├── model_service.py       # LLM config CRUD + health check
│   │   ├── vector_service.py      # Embedding + intent analysis + rerank
│   │   ├── ranker_service.py      # Dedicated reranker (RankerService class)
│   │   ├── classification_service.py  # Auto-classify skills/rules
│   │   ├── cache_service.py       # Redis cache: request + session + stats
│   │   ├── evolution_service.py   # Versioned evolution + rollback
│   │   ├── review_service.py      # Pattern-based content review
│   │   ├── import_service.py      # GitHub / ClawHub skill import
│   │   ├── validation_service.py  # Output validation + param validation
│   │   ├── rate_limiter.py        # Tiered rate limiting
│   │   └── intent_parser_v2.py    # Rule-based intent parser (3-layer)
│   ├── web/                       # Web UI routes + auth
│   │   ├── auth.py                # Login/logout/session
│   │   ├── routes.py              # Admin web pages
│   │   ├── auth_utils.py          # Auth helpers
│   │   ├── i18n_utils.py          # I18n helpers
│   │   └── settings_utils.py      # Settings helpers
│   └── i18n/                      # I18n translations
├── cli/
│   └── srcli.py                   # CLI client tool
└── tests/
    ├── conftest.py                # Test fixtures
    └── test_integration.py        # Integration tests
```

## Application Entrypoint (`main.py`)

```python
# 1. Lifespan: init_database() → register MCP tools → yield
# 2. FastMCP: FastMCP("SkillRouter") with streamable-http transport at /mcp
# 3. SessionMiddleware with 86400s max_age
# 4. Router mounts:
#    - auth_router (prefix "")     → /login, /logout, /register
#    - web_router (prefix "")      → Web UI pages
#    - api_router (prefix "")      → /api/* (REST endpoints)
#    - tool_router                 → /tool/* (capability endpoints)
#    - _mcp_app at "/mcp"          → MCP streamable-http transport
# 5. GET /health → {"status": "ok"}
# 6. GET /       → RedirectResponse to /login
```

## Request Flow: `POST /tool/invoke`

```
Client request (ToolInvokeRequest)
    │
    ▼
[tool.py] invoke_tool()
    │   1. Parse trace_id, capability, context, input
    │   2. Resolve user_id from api_key (SHA-256 hash lookup)
    │   3. Public fallback: resolve_task/analyze_intent → default to admin user
    │
    ▼
Capability dispatch (switch on req.capability):
    │
    ├── resolve_task ──────────► resolve_service.resolve_skills()
    ├── skill_register ────────► skill_service.create_skill() + vector_service.generate_embedding()
    ├── skill_update/delete/get► skill_service update/delete/get
    ├── skill_list ────────────► direct SQLAlchemy select
    ├── rule_create ───────────► rule_service.create_rule()
    ├── rule_list ─────────────► direct SQLAlchemy select
    ├── model_add ─────────────► model_service.add_model()
    ├── model_list ────────────► model_service.list_models()
    ├── cache_flush ───────────► cache_service.delete_cache()
    ├── evolution_submit ──────► evolution_service.submit_evolution()
    ├── evolution_rollback ────► evolution_service.rollback_evolution()
    ├── analyze_intent ────────► classification_service.analyze_intent_for_retrieval()
    └── skill_run ─────────────► resolve_service.resolve_task()
    │
    ▼
ToolInvokeResponse { trace_id, tool, capability, success, output, elapsed_ms }
```

## MCP Tools (registered in `mcp/tools.py`)

All MCP tools follow `ok()/fail()` response format:

```python
ok(data=None, msg="ok", trace_id="")   → {"success": True,  "code": "OK", "msg": ..., "data": {...}, "trace_id": "..."}
fail(code, msg, trace_id="")           → {"success": False, "code": "...", "msg": ..., "data": {}, "trace_id": "..."}
```

| MCP Tool                  | Description                                   |
|---------------------------|-----------------------------------------------|
| `resolve_task`            | Core: task → matching skills + rules          |
| `skill_register`          | Register skill with auto-classification       |
| `skill_update`            | Update skill fields                           |
| `skill_delete`            | Delete skill                                  |
| `skill_get`               | Get skill with files                          |
| `skill_get_script`        | Get entry executable script content           |
| `skill_run`               | Resolve task return skills with instructions  |
| `skill_list`              | List skills with filters                      |
| `skill_review`            | Run review on a skill                         |
| `skill_approve`           | Approve a skill (set status=approved)         |
| `skill_reject`            | Reject a skill with reason                    |
| `skill_pre_review`        | Pre-review content without saving             |
| `skill_batch_ops`         | Batch register/delete/submit_review           |
| `skill_batch_review`      | Batch approve/reject skills                   |
| `rule_create`             | Create rule with auto-classification          |
| `rule_update`             | Update rule fields                            |
| `rule_delete`             | Delete rule                                   |
| `rule_list`               | List rules with filters                       |
| `evolution_submit`        | Submit version evolution                      |
| `evolution_rollback`      | Rollback evolution                            |
| `evolution_list`          | List evolutions with filters                  |
| `cache_flush`             | Flush cache by key_hash                       |
| `cache_flush_by_target`   | Flush cache by pattern on resource_id         |
| `tag_global_manage`       | Global tag management                         |
| `embedding_model_detect`  | Auto-detect embedding dimension from endpoint |
| `review_pattern_manage`   | CRUD for review patterns                      |
| `model_add`               | Add LLM model configuration                   |
| `model_list`              | List LLM model configurations                 |
| `stats_get`               | System statistics + monitoring                |
| `operation_log_list`      | Query operation logs                          |
| `validate_skill_params`   | Validate params against skill schema          |
| `resource_export`         | Export skill/rule as markdown                 |

## Auth Flow

1. **API Key lookup:** Client sends `api_key` (plaintext). Server SHA-256 hashes it, queries `ApiKey` table where `key_hash == hash AND is_active == true`, gets associated `User`.
2. **Public bypass:** `resolve_task` and `analyze_intent` fall back to the admin user if no API key is provided.
3. **Web auth:** Session-based via `SessionMiddleware` + bcrypt password verification for login pages.

## Exception Hierarchy (`exceptions.py`)

```
SkillRouterException (base: error_code + message + details)
├── ConfigurationError    (CONFIG_ERROR)
├── ValidationError       (VALIDATION_ERROR)
├── DatabaseError         (DB_ERROR)
├── NotFoundError         (NOT_FOUND)
├── DuplicateError        (DUPLICATE)
├── PermissionDeniedError (PERMISSION_DENIED)
├── AuthenticationError   (AUTH_ERROR)
├── LLMError              (LLM_ERROR)
│   ├── LLMTimeoutError   (LLM_TIMEOUT)
│   └── EmbeddingError    (EMBEDDING_ERROR)
├── CacheError            (CACHE_ERROR)
├── RateLimitError        (RATE_LIMIT)
│   ├── QPSExceededError
│   └── QuotaExceededError
```

Helpers: `handle_exception()`, `safe_execute()`, `safe_execute_async()`, `@catch_and_log`, `@catch_and_log_async`.

## Model Config Fetching (`model_client.py`)

Fetches per-task model configuration from the Controller at `http://localhost:8883`:

```python
get_model_for_task(task_type) → GET /api/models/for-task/{task_type}
get_embedding_model()         → get_model_for_task("embedding")
get_chat_model()              → get_model_for_task("chat")
get_rerank_model()            → get_model_for_task("rerank")
```

Returns `{"api_base", "model_name", "api_key"}` or `None` on failure (gracefully falls back to `config.py` defaults).