# Memory Search - BM25 + TFIDF + Vector Hybrid

## Overview

Memory search API (`search.py`) provides three search modes and a statistics endpoint. The embedding system integrates with the platform Controller to fetch the BGE-M3 model configuration.

## Embedding Generation

### Model Resolution

```python
async def _get_embedding_model() -> dict
```

1. Checks cached `_embedding_model_cache` (process-level cache)
2. Queries Controller: `GET {CONTROLLER_URL}/api/models/for-task/embedding`
3. Timeout: 5 seconds
4. Default fallback:
   ```json
   {
       "model_name": "BAAI/bge-m3",
       "api_base": "https://api.siliconflow.cn/v1",
       "api_key": ""
   }
   ```

### Vector Generation

```python
async def generate_embedding(query: str) -> List[float]
```

- Calls `POST {api_base}/embeddings` with model name and query (truncated to 3000 chars)
- BGE-M3 produces 1024-dimensional vectors, **truncated to 384d** to fit storage
- Timeout: 15 seconds
- On failure: returns `[0.0] * 384`

---

## Search Endpoints

### 1. Vector Search - `POST /api/memories/search/vector`

**Input** (`VectorSearchRequest`):

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search query |
| `project` | string | No | - | Project filter |
| `category` | string | No | - | Category filter |
| `memory_tier` | string | No | - | Tier filter |
| `top_k` | integer | No | - | Max results |
| `min_similarity` | float | No | - | Similarity threshold |

**Flow**:

1. If pgvector available and query present:
   - Generate query embedding via `generate_embedding()`
   - Execute raw SQL with `embedding <=> :embedding` (cosine distance)
   - Similarity = `1 - cosine_distance`
   - Returns `search_type: "vector"`
2. **Fallback** to text search if vector fails:
   - Uses `title ILIKE '%query%'` OR `content ILIKE '%query%'`
   - Returns `search_type: "text"` with default similarity `0.5`

**Response**:

```json
{
    "data": {
        "query": "search term",
        "results": [
            {
                "memory": { "id": "...", "title": "...", ... },
                "similarity": 0.85
            }
        ],
        "total": 5,
        "search_type": "vector"
    }
}
```

### 2. Hybrid Search - `POST /api/memories/search/hybrid`

**Input** (`HybridSearchRequest`):

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search query |
| `project` | string | No | - | Project filter |
| `category` | string | No | - | Category filter |
| `memory_tier` | string | No | - | Tier filter |
| `top_k` | integer | No | - | Max results |
| `vector_weight` | float | No | 0.7 | Vector weight |
| `text_weight` | float | No | 0.3 | Text match weight |

**Current Implementation**:

- Text search with `title ILIKE / content ILIKE`
- Results ordered by `access_count DESC`
- Pseudo-hybrid scoring:
  - `text_score = 0.5` (base)
  - `vector_score = 0.7` if embedding exists, else `0.3`
  - `hybrid_score = vector_weight * vector_score + text_weight * text_score`

The `search_type` is reported as `"hybrid"`.

### 3. Statistics - `GET /api/memories/stats/overview`

Returns comprehensive memory statistics:

```json
{
    "total_memories": 42,
    "by_tier": { "semantic": 25, "episodic": 12, "procedural": 5 },
    "by_category": { "architecture": 10, "pattern": 15, ... },
    "ai_suggested_count": 8,
    "pending_review_count": 3,
    "total_relations": 15
}
```

### 4. Category Stats - `GET /api/memories/stats/categories`

Returns per-category breakdown with percentages:

```json
{
    "categories": [
        { "name": "architecture", "count": 10, "percentage": 23.81 },
        ...
    ]
}
```

---

## Filtering

All search endpoints support the same filters:
- `project`: exact match on project field
- `category`: exact match on category field
- `memory_tier`: exact match on memory tier
- `deleted_at IS NULL`: soft delete exclusion (always applied)

---

## Response Helper

```python
def memory_to_response(entry: MemoryEntry) -> dict
```

Converts `MemoryEntry` to response dictionary with 200-char content preview, embedding presence flag, and all metadata fields.