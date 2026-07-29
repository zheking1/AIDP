# Skill Router — LLM Integration

Skill Router uses LLMs at **4 stages** in the resolve pipeline, each with its own dedicated role, configurable via the `llm_configs` table or Controller API.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    LLM Config Sources                    │
│                                                         │
│  Priority: Controller API → llm_configs DB → config.py  │
│                                                         │
│  model_client.py: GET /api/models/for-task/{task_type}  │
│  vector_service.py: chat + embedding config fetch        │
│  ranker_service.py: DB query (role="Ranker")             │
│  classification_service.py: DB query (role="Intent")     │
└─────────────────────────────────────────────────────────┘
```

## LLM Roles (4)

| Role              | Used By                 | Purpose                                 |
|-------------------|------------------------|-----------------------------------------|
| **Intent Analyzer** | `vector_service.analyze_intent()` | Parse task → intents, tags, complexity |
| **Embedding**      | `vector_service.generate_embedding()` | Generate 1024-dim vector for similarity search |
| **Review**         | (reserved)             | Future: LLM-based content review       |
| **Ranker**         | `ranker_service.rerank()` | Re-score skill candidates by relevance |

## Model Configuration Loading

### Source 1: Controller API (`model_client.py`)

```python
# Attempts to fetch model config from Controller at localhost:8883
async def get_model_for_task(task_type: str) -> Optional[Dict]:
    resp = await client.get(f"{CONTROLLER_URL}/api/models/for-task/{task_type}")
    if resp.status_code == 200:
        return data.get("model")  # {"api_base", "model_name", "api_key"}

# Specialized fetchers
get_embedding_model() → get_model_for_task("embedding")
get_chat_model()      → get_model_for_task("chat")
get_rerank_model()    → get_model_for_task("rerank")
```

Returns `None` on failure → falls back to next source.

### Source 2: DB `llm_configs` table

```python
class LLMConfig(Base):
    id, name, endpoint, api_key, model_name
    role: "Intent Analyzer" | "Embedding" | "Review" | "Ranker"
    temperature, max_tokens, timeout_secs
    is_healthy, is_default
```

- **RankerService** queries for `role="Ranker" AND is_healthy=True` (prefers `is_default=True`).
- **ClassificationService** queries for `role="Intent Analyzer" AND is_healthy=True`.
- **LLM-based rerank fallback** (`_rerank_with_llm`) queries for `role="ranker" AND is_healthy=True`.

### Source 3: `config.py` defaults

```python
llm_endpoint:  str = "http://localhost:8000/v1"
llm_api_key:   str = "sk-xxx"
llm_model:     str = "deepseek-v4-flash-free"
llm_timeout:   int = 30  # seconds

embedding_endpoint: str = "http://localhost:8000/v1"
embedding_api_key:  str = "sk-xxx"
embedding_model:    str = "text-embedding-3-small"
embedding_dim:      int = 1024
embedding_timeout:  int = 15
```

## Stage 1: Intent Analysis (LLM)

```python
# vector_service.py:56
async def analyze_intent(task: str, chat_history: Optional[list] = None) -> Optional[dict]:
    cfg = await _get_chat_config()  # Controller → config.py fallback

    system_prompt = (
        "Analyze the following task. Output JSON with keys: "
        "primary_intent (str), secondary_intent (str or null), domain (str), "
        "tags_needed (list of str), secondary_tags (list of str), complexity (low/medium/high), "
        "is_compound (bool). "
        "If the task has multiple distinct goals, set is_compound=true..."
    )

    resp = await client.post(
        f"{cfg['endpoint']}/chat/completions",
        json={"model": cfg["model"], "messages": [...], "temperature": 0.3, "max_tokens": 500},
        headers={"Authorization": f"Bearer {cfg['api_key']}"},
        timeout=settings.llm_timeout  # default 30s
    )
    return json.loads(content)
```

**Timeout behavior:**
- `settings.llm_timeout` (default 30s, range 1–300)
- On timeout: returns `None` → triggers degradation in `resolve_skills()`

**Degradation path:**
```
analyze_intent() returns None
    ├── mode="auto"       → degrade to "embedding_only" (skip LLM intent, use embedding + tags)
    └── mode="llm_only"   → degrade to "tag_only"       (skip both LLM and embedding)
```

## Stage 2: Embedding Generation

```python
# vector_service.py:39
async def generate_embedding(text: str) -> Optional[list[float]]:
    cfg = await _get_embedding_config()  # Controller → config.py fallback
    if not cfg:
        return None  # Controller returned None/no endpoint configured

    resp = await client.post(
        f"{cfg['endpoint']}/embeddings",
        json={"model": cfg["model"], "input": text},
        headers={"Authorization": f"Bearer {cfg['api_key']}"},
        timeout=settings.embedding_timeout  # default 15s
    )
    return resp.json()["data"][0]["embedding"]  # list[float] of dim 1024
```

**Timeout behavior:**
- `settings.embedding_timeout` (default 15s, range 1–60)
- On failure: returns `None` → degrade to `tag_only` mode

**Auto-detect embedding dimension:**
```python
async def detect_embedding_dim(endpoint, api_key, model) -> Optional[int]:
    # Sends test embedding request with "test", returns len(data[0]["embedding"])
    # Exposed as MCP tool: embedding_model_detect
```

## Stage 3: Reranking

### Attempt 1: Cross-encoder API (Controller)

```python
# vector_service.py:110 (_rerank_with_api)
async def _rerank_with_api(task, skills, intent):
    model = await get_rerank_model()  # Controller API
    docs = [f"[{name}] {content[:500]}" for s in skills]
    resp = await client.post(
        ep, json={"model": ..., "query": task, "documents": docs},
        timeout=15
    )
    # Returns [{"id": ..., "relevance": float, "is_primary": bool}]
```

### Attempt 2: LLM prompt (fallback)

```python
# vector_service.py:142 (_rerank_with_llm)
async def _rerank_with_llm(task, skills, intent):
    model = await db.execute(select(LLMConfig).where(role=="ranker", is_healthy))
    # Falls back to _get_chat_config() if no DB config

    # Sends all skill info + intent summary with RE_RANK_PROMPT
    resp = await client.post(
        endpoint, json={"messages": [...], "temperature": 0.1, "max_tokens": 2000},
        timeout=30
    )
    return json.loads(content)  # [{id, relevance, reason, is_primary}]
```

### Attempt 3: RankerService (dedicated small model)

```python
# ranker_service.py:75
class RankerService:
    async def rerank(self, db_session, user_query, skills):
        config = await self.get_ranker_config(db_session)
        # Queries llm_configs WHERE role="Ranker" AND is_healthy
        prompt = self._build_rerank_prompt(user_query, skills)
        response = await self._call_llm(config, prompt)
        return self._parse_rerank_response(response, skills)
```

**Ranker prompt scoring criteria:**
1. Direct Relevance (40%): Does this skill directly address the main goal?
2. Instruction Match (30%): How well does instruction match intent?
3. Tag Relevance (20%): Do tags match query keywords?
4. Example Match (10%): Do examples show similar use cases?

**Fallback chain:**
```
RankerService.rerank()
    ├── No config available → return None (skip rerank)
    ├── LLM timeout (asyncio.TimeoutError) → return None (fall through)
    ├── LLM call fails → return None
    └── Success → merge rerank scores into skill_list
```

## Stage 4: Classification (Auto-tagging)

```python
# classification_service.py:68
async def classify_skill(db_session, name, content, existing_tags, existing_description):
    config = await self.get_classifier_config(db_session)
    # Priority: Intent Analyzer (default) → Ranker (fallback)
    prompt = self._build_skill_classify_prompt(name, content, ...)
    response = await self._call_llm(config, prompt)  # temperature=0.3, max_tokens=500
    return {tags, description, suggested_group, category}
```

## Config Validation (production safety)

```python
# config.py:74
def validate_production_safety(self) -> list[str]:
    # Warns on:
    # - db_password == "change_me"
    # - admin_password == "admin123"
    # - llm_api_key == "sk-xxx"
    # - embedding_api_key == "sk-xxx"
```

## Timeout Summary

| Operation          | Timeout Config          | Default | Range    | On Failure                  |
|--------------------|-------------------------|---------|----------|-----------------------------|
| Intent analysis    | `llm_timeout`           | 30s     | 1–300    | Degrade to embedding_only   |
| Embedding gen      | `embedding_timeout`     | 15s     | 1–60     | Degrade to tag_only         |
| Ranker (Controller)| 15s (hardcoded)         | 15s     | -        | Fall to LLM rerank          |
| Ranker (LLM prompt)| 30s (hardcoded)         | 30s     | -        | Fall to embedding scores    |
| Classification     | `llm_timeout`           | 30s     | 1–300    | Return existing tags/desc   |
| Model test         | `model.timeout_secs`    | 30s     | -        | Return unhealthy            |

## Best Practices

1. **Always configure a Controller** for centralized model management and cross-encoder reranking.
2. **Set up at least one Ranker model** in `llm_configs` with `is_default=True` for better reranking.
3. **Monitor `degrade_info`** in resolve responses — it indicates which degradation paths are being triggered.
4. **Use `embedding_model_detect`** MCP tool to verify embedding dimensions before configuring.
5. **Set production-safe credentials** — the system will warn on startup if using default keys.