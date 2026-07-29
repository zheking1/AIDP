# Memory Tool API Reference

## Tool Protocol (`tool.py`)

### `GET /tool/manifest`

Returns tool registration manifest:

```json
{
    "apiVersion": "aidp.dev/v1",
    "kind": "Tool",
    "metadata": { "name": "memory-tool", "version": "0.1.0" },
    "runtime": { "modes": ["standalone", "managed"], "docker": { ... } },
    "capabilities": [
        "memory.create", "memory.search", "memory.search.hybrid",
        "memory.contradiction.check", "memory.consolidate",
        "memory.context", "memory.update", "memory.delete"
    ]
}
```

### `GET /tool/capabilities`

Returns all 8 capabilities with complete input/output schemas.

### `POST /tool/invoke`

Unified invocation endpoint. Request format:

```json
{
    "trace_id": "tr_abc123",
    "capability": "memory.create",
    "context": { "user_id": "user1" },
    "input": { "project": "myapp", "category": "architecture", "title": "...", "content": "..." }
}
```

---

## Capability Reference

### 1. `memory.create`

- **Endpoint**: `POST /api/memory`
- **Timeout**: 3000ms
- **Permission**: `memory:write`

**Required inputs**: `project`, `category`, `title`, `content`

**Optional inputs**: `tags`, `pinned` (boolean), `user_id` (from context)

Calls `create_memory()` service function.

### 2. `memory.search`

- **Endpoint**: `GET /api/memory/search`
- **Timeout**: 3000ms
- **Permission**: `memory:read`

**Required inputs**: `project`

**Optional inputs**: `query`, `category`, `limit` (default 50)

Calls `search_memory()` with user_id from context.

### 3. `memory.search.hybrid`

- **Endpoint**: `POST /api/memory/search/hybrid`
- **Timeout**: 5000ms
- **Permission**: `memory:read`

**Required inputs**: `project`, `query`

**Optional inputs**:
- `top_k` (default 10)
- `weights`: `{ "vector" (default 0.5), "tfidf" (default 0.3), "bm25" (default 0.2) }`

Calls `hybrid_search()` service function with weighted scores.

### 4. `memory.contradiction.check`

- **Endpoint**: `POST /api/memory/check-contradictions`
- **Timeout**: 5000ms
- **Permission**: `memory:write`

**Required inputs**: `project`, `title`, `content`

**Process**:
1. Loads up to 100 existing memories for the project
2. Runs `SemanticContradictionDetector.detect()`
3. Applies `ContradictionHandler.handle()` to each result

**Response**:
```json
{
    "has_contradictions": true,
    "contradictions": [
        {
            "contradiction": {
                "existing_memory": { ... },
                "contradiction_type": "negation",
                "confidence": 0.8,
                "evidence": "..."
            },
            "action": {
                "action": "flag_for_review",
                "reason": "High confidence conflict, requires manual review"
            }
        }
    ]
}
```

### 5. `memory.consolidate`

- **Endpoint**: `POST /api/memory/consolidate`
- **Timeout**: 10000ms
- **Permission**: `memory:write`

**Required inputs**: `project`

**Optional inputs**: `similarity_threshold` (default 0.85)

Calls `MemoryConsolidator.consolidate()`.

### 6. `memory.context`

- **Endpoint**: `GET /api/memory/context`
- **Timeout**: 3000ms
- **Permission**: `memory:read`

**Required inputs**: `project`, `query`

**Optional inputs**: `limit` (default 10)

Calls `get_context_package()` to retrieve a context package of relevant memories.

### 7. `memory.update`

- **Endpoint**: `PUT /api/memory/{id}`
- **Timeout**: 3000ms
- **Permission**: `memory:write`

**Required inputs**: `memoryId`

**Optional inputs**: `category`, `title`, `content`, `tags`, `pinned`

Partial update - only provided fields are modified. Returns `null` if memory not found (error response with `NOT_FOUND`).

### 8. `memory.delete`

- **Endpoint**: `DELETE /api/memory/{id}`
- **Timeout**: 3000ms
- **Permission**: `memory:delete`

**Required inputs**: `memoryId`

**Response**: `{ "deleted": true }` or validation error if `memoryId` missing.

---

## Error Handling

All invoke errors return:

```json
{
    "trace_id": "tr_xxx",
    "tool": "memory-tool",
    "capability": "...",
    "success": false,
    "error": {
        "code": "NOT_FOUND" | "VALIDATION_ERROR" | "INTERNAL_ERROR",
        "message": "..."
    },
    "elapsed_ms": 42
}
```

Error codes:
- `NOT_FOUND`: Capability not recognized or memory not found
- `VALIDATION_ERROR`: Required input missing (e.g., `memoryId` for update/delete)
- `INTERNAL_ERROR`: Exception during execution