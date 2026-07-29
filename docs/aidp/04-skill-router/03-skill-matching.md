# Skill Router — Skill Matching (Resolve Pipeline)

The core function is `resolve_skills()` in `app/services/resolve_service.py:73`. It implements a 6-stage hybrid matching pipeline.

## Pipeline Overview

```
User task (string)
    │
    ▼
[Stage 1] Cache Check ──────────────────────► hit? → return cached result
    │
    ▼
[Stage 2] Intent Analysis (LLM) ────────────► primary/secondary intents, tags_needed, is_compound
    │  mode=auto: timeout → degrade to embedding_only
    │  mode=llm_only: timeout → degrade to tag_only
    ▼
[Stage 3] Embedding Generation ─────────────► 1024-dim vector via OpenAI-compatible API
    │  fail → degrade to tag_only
    │  success → check session cache (cosine ≥ 0.7)
    ▼
[Stage 4] Vector Search (pgvector HNSW) ────► top_k*2 skills + top_k*2 rules
    │  |  1 - cosine_distance | → vec_score
    │  Concurrent: skills & rules fetched in parallel (asyncio.create_task)
    ▼
[Stage 5] Scoring ──────────────────────────►
    │  Skill: final_score = vec_score*0.6 + tag_score*0.3 + keyword_boost + dep_boost
    │  Rule:  final_score = vec_score*0.6 + tag_score*0.3
    │
    ▼
[Stage 6] Reranking (RankerService) ────────► LLM rerank → adjust scores, mark primary/secondary
    │  |  compound intent? → primary_skills get 70% weight budget, secondary get 30%
    │  |  normal intent?   → final_score = vec*0.4 + tag*0.2 + kw*0.1 + rerank*0.3
    ▼
[Stage 7] Validation + Cache ───────────────► validate output, log operation, cache results
```

## Stage 1: Cache Check

```python
cache_key = make_cache_key(task, user_id, mode)  # SHA-256(task:user_id:mode)
cached = await get_cached(cache_key)
if cached:
    return {**cached, "cache_hit": True, "cache_source": "request"}

# Session cache: shortcut by comparing query embedding to recent embeddings
sc = await get_session_cache(str(user_id), query_embedding)  # cosine ≥ 0.7 threshold
if sc:
    return {**sc, "cache_hit": True, "cache_source": "session"}
```

Two-level cache:
- **Request cache:** Exact match via hashed key, TTL = `cache_ttl_seconds` (default 3600s).
- **Session cache:** Approximate match via cosine similarity on query embeddings, last 20 entries per user, TTL = 1800s.

## Stage 2: Intent Analysis (LLM)

```python
intent = await analyze_intent(task)  # returns dict or None

# Response format:
{
    "primary_intent": "code_generation",
    "secondary_intent": "testing",  # or null
    "domain": "backend",
    "tags_needed": ["python", "fastapi"],
    "secondary_tags": ["pytest", "testing"],
    "complexity": "low/medium/high",
    "is_compound": true/false
}
```

LLM prompt:
```
"Analyze the following task. Output JSON with keys:
 primary_intent, secondary_intent, domain, tags_needed, secondary_tags,
 complexity, is_compound.
 If the task has multiple distinct goals, set is_compound=true..."
```

**Degradation path:**
- `mode=auto` + `intent is None` → `mode = "embedding_only"` (degrade_info: `llm_timeout → embedding_only`)
- `mode=llm_only` + `intent is None` → `mode = "tag_only"` (degrade_info: `llm_timeout → tag_only`)
- `query_embedding is None` → `mode = "tag_only"` (degrade_info: `embedding_fail → tag_only`)

## Stage 3: Embedding Generation

```python
query_embedding = await generate_embedding(task)
# Calls: POST {cfg['endpoint']}/embeddings
# Body: {"model": cfg["model"], "input": task}
# Returns: list[float] of length 1024, or None on failure
```

Config is fetched from Controller (`get_embedding_model()`) with fallback to `config.py` defaults.

## Stage 4: Vector Search

For `mode=embedding_only` or `mode=auto` with successful embedding:

```python
# Skills query (pgvector cosine_distance on HNSW index)
skill_sql = base_skill.add_columns(
    (1 - Skill.embedding.cosine_distance(text(f"'{emb_str}'::vector"))).label("vec_score")
).where(Skill.embedding.isnot(None)).order_by(text("vec_score DESC")).limit(top_k * 2)

# Rules query — same approach, separate table
# Both run concurrently via asyncio.create_task
skills_future = asyncio.create_task(fetch_skills())
rules_future = asyncio.create_task(fetch_rules())
skills = await skills_future
rules = await rules_future
```

For `mode=tag_only` (degraded):
```python
# Filter by tags_needed, order by updated_at DESC
base_skill = base_skill.where(or_(*[Skill.tags.any(t) for t in tag_filter]))
```

**Permission filtering (`role` parameter):**
```python
if role:
    base_skill = base_skill.where(
        (Skill.allowed_roles.is_(None)) | (Skill.allowed_roles.any(role))
    )
```

## Stage 5: Scoring

### Skill Scoring

```python
final_score = (vec_score * 0.6) + (tag_score * 0.3) + keyword_boost + dep_boost
```

- **vec_score** (weight 0.6): Cosine similarity from pgvector (normalized to 0–1).
- **tag_score** (weight 0.3): Overlap between `tags_needed` (from intent) and skill tags: `|intersection| / |tags_needed|`.
- **keyword_boost** (0.0–0.15): Domain-specific keyword patterns (`compute_keyword_boost()`):

  | Pattern                              | Weight |
  |--------------------------------------|--------|
  | `programming\|code\|script\|debug...` | 0.15   |
  | `security\|auth\|login...`           | 0.15   |
  | `api\|rest\|endpoint...`             | 0.12   |
  | `database\|sql\|query...`            | 0.12   |
  | `deploy\|docker\|kubernetes...`      | 0.12   |
  | `data\|analytics\|ml...`             | 0.12   |
  | `frontend\|ui\|react...`             | 0.10   |
  | `backend\|server\|service...`        | 0.10   |
  | `test\|testing\|unit...`             | 0.10   |
  | `financial\|payment\|accounting...`  | 0.08   |

- **dep_boost**: +0.05 if skill has dependencies (promotes composite skills).

### Rule Scoring

```python
final_score = (vec_score * 0.6) + (tag_score * 0.3)
```

Also sorted by `priority` descending.

### Deduplication

Skills with identical first 100 chars of `content` are deduplicated:
```python
content_key = s.content[:100]
if content_key in seen_content:
    continue
seen_content.add(content_key)
```

## Stage 6: Reranking (RankerService)

```python
rerank_result = await ranker_service.rerank(session, task, skill_list)
```

Reranker (dedicated LLM role "Ranker"):
1. **Attempts Controller cross-encoder API** (`_rerank_with_api`) — returns relevance scores per skill.
2. **Falls back to LLM prompt** (`_rerank_with_llm`) — JSON response with `{relevance, reason, is_primary}`.

### Compound Intent Weight Allocation

When `intent.is_compound = true`:

| Skill Type  | Weight Budget | Formula                                                     |
|-------------|---------------|-------------------------------------------------------------|
| Primary     | 70%           | `vec*0.35 + tag*0.15 + kw*0.05 + rerank*0.45`              |
| Secondary   | 30%           | `vec*0.20 + tag*0.10 + kw*0.05 + rerank*0.15`              |

For **normal intent**:
```python
s["score"] = (vec * 0.4) + (tag * 0.2) + (kw * 0.1) + (rr_score * 0.3)
```

## Stage 7: Validation + Cache

```python
# 1. Write operation log
log = OperationLog(user_id=..., resource_type="resolve", action="resolve", detail={...})
session.add(log); await session.commit()

# 2. Validate output
result = validate_resolve_result(output)  # Checks: sensitive data, dangerous ops, placeholders, permissions

# 3. Cache results
if query_embedding:
    await set_session_cache(str(user_id), query_embedding, output)
await set_cache(cache_key, output)
```

## Dependency Cycle Detection

```python
async def detect_cycle(skill_id, deps, visited=None, path=None) -> (bool, list):
    # DFS-based cycle detection in skill dependency graph
    # Returns (has_cycle, cycle_path)
```

Each skill result includes `has_cycle_dep: true/false`.

## Output Structure

```json
{
  "intent_analysis": {
    "primary_intent": "code_generation",
    "secondary_intent": null,
    "domain": "backend",
    "tags_needed": ["python"],
    "complexity": "medium",
    "is_compound": false
  },
  "skills": [
    {
      "id": "uuid",
      "name": "skill name",
      "content": "full skill content",
      "score": 0.852,
      "score_detail": {
        "vector_score": 0.82,
        "tag_score": 0.5,
        "keyword_boost": 0.12,
        "dep_boost": 0.05,
        "rerank_score": 0.91,
        "is_primary": true,
        "final_score": 0.852
      },
      "match_score": 0.852,
      "require_approval": false,
      "version": 1,
      "tags": ["python"],
      "review_status": "approved",
      "dependencies": [],
      "has_cycle_dep": false
    }
  ],
  "rules": [
    {
      "id": "uuid",
      "name": "rule name",
      "content": "rule content",
      "score": 0.65,
      "priority": 10
    }
  ],
  "meta": {
    "latency_ms": 423,
    "degrade_info": {"degraded": false, "reason": ""},
    "ranker_used": true,
    "rule_boosts_applied": [...],
    "permission_filtered": 0,
    "mode": "auto",
    "top_k": 5
  }
}
```