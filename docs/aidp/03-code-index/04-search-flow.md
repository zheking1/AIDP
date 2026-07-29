# Code Index — Search Flow

This document covers the complete search system: exact symbol search, semantic fusion search, and fuzzy matching.

---

## 1. `search_symbols()` — Exact Search

**File:** `app/services/search_service.py:14`

```python
async def search_symbols(self, project_id: int, query: str,
                         node_type: str = None, limit: int = 50) -> List[Dict]:
    conditions = [Node.project_id == project_id]
    if node_type:
        conditions.append(Node.node_type == node_type)
    if query:
        conditions.append(
            or_(
                Node.name.ilike(f"%{query}%"),
                Node.signature.ilike(f"%{query}%"),
                Node.docstring.ilike(f"%{query}%"),
            )
        )
    result = await self.db.execute(
        select(Node).where(*conditions).limit(limit)
    )
    nodes = result.scalars().all()
    return [{
        "id": n.id,
        "node_type": n.node_type,
        "name": n.name,
        "qualified_name": n.qualified_name,
        "file_path": n.file_path,
        "line_start": n.line_start,
        "language": n.language,
    } for n in nodes]
```

**Behavior:**
- Uses SQL `ILIKE` (case-insensitive) with `%query%` wildcards
- Searches **three fields simultaneously** via `OR`:
  - `Node.name` — symbol name
  - `Node.signature` — function signature string
  - `Node.docstring` — documentation string
- Optional `node_type` filter (e.g., `"function"`, `"class"`)
- Returns basic node info: id, type, name, qualified_name, file_path, line_start, language

---

## 2. `semantic_search()` — Fusion Search

**File:** `app/services/search_service.py:60`

This is the core search algorithm — it fuses three scoring methods:

```python
async def semantic_search(self, project_id: int, query: str, top_k: int = 10,
                          node_type: str = None) -> List[Dict]:
    from app.services.node_embedding_store import NodeEmbeddingStore
    store = NodeEmbeddingStore(self.db)
```

### Step 1: Vector Search

```python
    vector_scores = {}
    try:
        vec_results = await store.vector_search(query, project_id, top_k=top_k * 2)
        for node_id, score in vec_results:
            vector_scores[node_id] = score
    except Exception as e:
        logger.warning(f"Vector search failed (falling back to exact): {e}")
```

- Calls `NodeEmbeddingStore.vector_search()` with `top_k * 2` (to get more candidates)
- Result is `Dict[int, float]` mapping node_id → cosine similarity score
- **Fallback:** If vector search fails (no embeddings, model unavailable, etc.), `vector_scores` stays empty and the system continues with exact+fuzzy only

### Step 2: Exact (ILIKE) Search

```python
    exact_conditions = [Node.project_id == project_id]
    if node_type:
        exact_conditions.append(Node.node_type == node_type)
    query_lower = query.lower()
    exact_conditions.append(
        (Node.name == query_lower) |
        (Node.name.ilike(f"%{query_lower}%")) |
        (Node.signature.ilike(f"%{query_lower}%")) |
        (Node.docstring.ilike(f"%{query_lower}%"))
    )
    exact_result = await self.db.execute(
        select(Node).where(*exact_conditions).limit(top_k * 2)
    )
    exact_nodes = exact_result.scalars().all()
```

- Broad ILIKE search (same as `search_symbols`)
- Also checks for exact name match (case-insensitive)

### Step 3: Union of Results

```python
    all_nodes_covered = list(exact_nodes)
    if vector_scores:
        vec_node_ids = list(vector_scores.keys())
        vec_result = await self.db.execute(
            select(Node).where(Node.id.in_(vec_node_ids))
        )
        for n in vec_result.scalars().all():
            if n.id not in {x.id for x in all_nodes_covered}:
                all_nodes_covered.append(n)
```

- Start with exact results
- Add vector results not already in the exact set
- This union ensures no duplicate nodes are scored

### Step 4: Score Fusion

```python
    scored = {}
    for node in all_nodes_covered:
        vec_score = vector_scores.get(node.id, 0.0)
        exact_score = 1.0 if node.name.lower() == query_lower else (
            0.4 if query_lower in (node.name or "").lower() else 0.0
        )
        fuzzy_score = self._fuzzy_match(query, node.name, node.signature, node.docstring)

        total = round(vec_score * 0.5 + exact_score * 0.3 + fuzzy_score * 0.2, 4)
        scored[node.id] = {
            "node": node,
            "score": total,
            "score_breakdown": {
                "vector": round(vec_score, 4),
                "exact": round(exact_score, 4),
                "fuzzy": round(fuzzy_score, 4),
            }
        }
```

**Fusion weights:**

| Component | Weight | Source                     | Range     |
|-----------|--------|----------------------------|-----------|
| Vector    | 0.5    | Cosine similarity (0..1)   | 0.0 – 1.0 |
| Exact     | 0.3    | Name match scoring         | 0.0, 0.4, or 1.0 |
| Fuzzy     | 0.2    | Word overlap in text fields| 0.0 – 1.0 |

**Exact scoring tiers:**
- `1.0` — name exactly matches query (case-insensitive)
- `0.4` — query is a substring of name
- `0.0` — no match

### Step 5: Rank and Return

```python
    ranked = sorted(scored.values(), key=lambda x: x["score"], reverse=True)[:top_k]
    return [{
        "id": r["node"].id,
        "node_type": r["node"].node_type,
        "name": r["node"].name,
        "qualified_name": r["node"].qualified_name,
        "file_path": r["node"].file_path,
        "line_start": r["node"].line_start,
        "language": r["node"].language,
        "signature": r["node"].signature,
        "return_type": r["node"].return_type,
        "docstring": r["node"].docstring,
        "score": r["score"],
        "score_breakdown": r["score_breakdown"],
    } for r in ranked]
```

Each result includes a **score breakdown** so callers can see which component contributed what.

---

## 3. `_fuzzy_match()` Algorithm

**File:** `app/services/search_service.py:133`

```python
def _fuzzy_match(self, query: str, name: str = None,
                 signature: str = None, docstring: str = None) -> float:
    q_words = set(query.lower().split())
    if not q_words:
        return 0.0
    texts = [t for t in [name, signature, docstring] if t]
    if not texts:
        return 0.0
    best = 0.0
    for text in texts:
        t_words = set(text.lower().split())
        overlap = q_words & t_words
        score = len(overlap) / len(q_words) if q_words else 0.0
        best = max(best, score)
    return best
```

**Algorithm:**
1. Split query into word set (lowercase, whitespace-delimited)
2. For each non-None text field (name, signature, docstring):
   - Split text into word set (lowercase)
   - Compute Jaccard-like overlap: `|q_words ∩ t_words| / |q_words|`
3. Return the best (max) score across all three text fields

**Properties:**
- Score is `1.0` if all query words appear in at least one text field
- Score is `0.0` if no query words match any text field
- Each text field is scored independently, best wins
- No edit-distance or substring matching — pure word token overlap

---

## 4. Fallback When Embeddings Are Unavailable

The semantic search gracefully degrades:

| Scenario                                | Behavior                                    |
|-----------------------------------------|---------------------------------------------|
| No `node_embeddings` records exist      | `vector_search()` returns empty → vec_score=0 |
| Model Controller unreachable            | `EmbeddingService` falls to local → mock    |
| Local sentence-transformers uninstalled | `EmbeddingService` falls to mock            |
| Mock active                             | Deterministic but meaningless vectors       |
| `vector_search()` throws exception      | Caught, `vector_scores` stays empty         |

When `vector_scores` is empty:
- `all_nodes_covered` = `exact_nodes` (only ILIKE results)
- `vec_score` = 0.0 for all nodes (no contribution from vector component)
- Scoring becomes: `0.3*exact + 0.2*fuzzy`

This means search still works — just without semantic relevance. Results are purely text-match based.

---

## 5. Other Search Methods

### `list_projects()`
```python
async def list_projects(self) -> List[Dict]:
    result = await self.db.execute(select(Project).order_by(Project.id.desc()))
    ...
```
Returns basic project info: id, name, path, language, framework, file_count, node_count, status.

### `get_project(project_id)`
```python
async def get_project(self, project_id: int) -> Optional[Project]:
    result = await self.db.execute(
        select(Project).where(Project.id == project_id)
    )
    return result.scalar_one_or_none()
```
Returns the full Project ORM object or None.

---

## 6. Typed Search (REST endpoint)

**File:** `app/api/code_index.py:62`

```python
@router.get("/api/search/typed")
async def search_typed(
    project_id: int,
    node_type: str = None,
    return_type: str = None,
    param_type: str = None,
    access_modifier: str = None,
    q: str = "",
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
```

Additional filter dimensions beyond basic search:
- `return_type` — ILIKE on `Node.return_type` (e.g., `"Optional[Dict]"`)
- `param_type` — ILIKE on `Node.params_json` (e.g., `"int"`)
- Filters are additive (AND), not exclusive

Returns richer output including `signature`, `return_type`, `params`, `docstring`, and a `filters_applied` section.