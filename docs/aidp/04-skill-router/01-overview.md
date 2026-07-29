# Skill Router — Overview

## What It Is

Skill Router is the **core routing engine** in the AIDP platform. It matches user tasks to the most relevant skills (executable code/scripts) and rules (guidance/constraints) using a hybrid approach: LLM-based intent analysis, vector similarity search via pgvector, keyword boosting, and a dedicated LLM reranker. It also manages the full lifecycle of skills and rules — registration, review, evolution, import/export, and caching.

**Port:** `8788`

## Tech Stack

| Layer           | Technology                              |
|-----------------|-----------------------------------------|
| Runtime         | Python 3.13                             |
| Web Framework   | FastAPI (async)                         |
| MCP Protocol    | FastMCP (streamable-http)               |
| Database        | PostgreSQL 16 + pgvector (HNSW index)   |
| Cache           | Redis (connection pooling)              |
| ORM             | SQLAlchemy 2.0 (async, `asyncpg`)       |
| Embeddings      | Configurable (default: text-embedding-3-small, 1024-dim) |
| LLM             | Configurable (default: deepseek-v4-flash-free) |
| Auth            | bcrypt passwords + API key (SHA-256 hash) |

## Core Capabilities (14)

| #  | Capability             | Permission       | Description                                      |
|----|------------------------|------------------|--------------------------------------------------|
| 1  | `resolve_task`         | `skill:resolve`  | Resolve a task to matching skills + rules        |
| 2  | `skill_register`       | `skill:write`    | Register a new skill with auto-classification    |
| 3  | `skill_update`         | `skill:write`    | Update an existing skill's fields                |
| 4  | `skill_delete`         | `skill:write`    | Delete a skill by ID                             |
| 5  | `skill_get`            | `skill:read`     | Get full skill details with files                |
| 6  | `skill_run`            | `skill:execute`  | Run a skill by task matching (returns instructions) |
| 7  | `skill_list`           | `skill:read`     | List skills with tag/query filters               |
| 8  | `rule_create`          | `rule:write`     | Create a new rule with auto-classification       |
| 9  | `rule_list`            | `rule:read`      | List rules with filters                          |
| 10 | `model_add`            | `model:write`    | Register an LLM model configuration              |
| 11 | `model_list`           | `model:read`     | List LLM model configurations                    |
| 12 | `cache_flush`          | `cache:write`    | Flush resolve cache (by key or pattern)          |
| 13 | `evolution_submit`     | `evolution:write`| Submit a version evolution for skill/rule        |
| 14 | `evolution_rollback`   | `evolution:write`| Rollback an evolution to previous version        |
| +  | `analyze_intent`       | `skill:resolve`  | Stage 1 of AIDP pipeline: intent → retrieval plan |

## Core Services (in `app/services/`)

| Service                     | File                      | Role                                           |
|-----------------------------|---------------------------|------------------------------------------------|
| `resolve_skills`            | `resolve_service.py`      | Full resolution pipeline: intent → embedding → search → score → rank → cache |
| `create_skill / create_rule` | `skill_service.py / rule_service.py` | CRUD operations for skills and rules       |
| `generate_embedding`        | `vector_service.py`       | Embedding generation + LLM intent analysis + rerank |
| `ClassificationService`     | `classification_service.py` | Auto-tagging, auto-description, group suggestions |
| `RankerService`             | `ranker_service.py`       | Dedicated small-model reranker with fallback    |
| `ImportService`             | `import_service.py`       | Import skills from GitHub or ClawHub            |
| `run_review / pre_review`   | `review_service.py`       | Static pattern-based skill content review       |
| `submit_evolution`          | `evolution_service.py`    | Versioned content updates with rollback         |
| `get_cached / set_cache`    | `cache_service.py`        | Redis-based resolve cache + session cache       |
| `check_rate_limit`          | `rate_limiter.py`         | Tiered rate limiting: QPS + daily quota + concurrency |
| `validate_resolve_result`   | `validation_service.py`   | Output validation: sensitive data, dangerous ops, placeholders |

## Configuration (`app/config.py`)

```python
# LLM
llm_endpoint: str = "http://localhost:8000/v1"
llm_api_key: str = "sk-xxx"
llm_model: str = "deepseek-v4-flash-free"
llm_timeout: int = 30        # seconds (1–300)

# Embedding
embedding_endpoint: str = "http://localhost:8000/v1"
embedding_api_key: str = "sk-xxx"
embedding_model: str = "text-embedding-3-small"
embedding_dim: int = 1024    # 1–1536, must match model
embedding_timeout: int = 15  # seconds (1–60)

# Database
database_url: str = ""       # Full PG URL (overrides default)
db_password: str = "change_me"

# Redis
redis_url: str = "redis://localhost:6379/0"

# Resolve
resolve_top_k_default: int = 5   # 1–10
cache_ttl_seconds: int = 3600    # 1–86400

# Auth
admin_username: str = "admin"
admin_password: str = ""    # min 6 chars
skill_manager_api_key: str = ""

# GitHub
github_token: str = ""      # For higher rate limits (5000/hr)
```