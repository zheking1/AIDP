# Code Index — Embedding System

Code Index uses a 3-tier embedding strategy for semantic code search. Embeddings are generated during indexing and consumed during search.

---

## Architecture Overview

```
                    ┌─────────────────────────┐
                    │  Tier 1: Controller API  │
                    │  (BGE-M3, 1024-dim)      │
                    │  http://localhost:8883   │
                    │  /api/models/for-task/   │
                    │  embedding                │
                    └──────────┬──────────────┘
                               │ unreachable / no model
                               ▼
                    ┌─────────────────────────┐
                    │  Tier 2: Local ST        │
                    │  (all-MiniLM-L6-v2,      │
                    │   384-dim)               │
                    │  sentence-transformers   │
                    └──────────┬──────────────┘
                               │ import error / fail
                               ▼
                    ┌─────────────────────────┐
                    │  Tier 3: Mock            │
                    │  Deterministic SHA256+sin│
                    │  dimension: 1024         │
                    └─────────────────────────┘
```

---

## EmbeddingService

**File:** `app/services/embedding_service.py:14`

```python
class EmbeddingService:
    _model = None                  # Local SentenceTransformer instance
    _controller_model = None       # Remote model config dict

    def __init__(self, model_name: str = None):
        self.model_name = model_name or "BAAI/bge-m3"
        self._dimension = 1024                     # BGE-M3 default
```

Singleton via module-level:
```python
_embedding_service: Optional[EmbeddingService] = None

def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
```

---

## Tier 1: Controller API (BGE-M3)

**Priority:** Highest  
**Dimension:** 1024  
**Model:** Configurable via controller, defaults to `BAAI/bge-m3`

### Model Fetch (`_load_controller`)

```python
CONTROLLER_URL = os.getenv("CONTROLLER_URL", "http://localhost:8883")

def _load_controller(self):
    resp = httpx.get(
        f"{CONTROLLER_URL}/api/models/for-task/embedding",
        timeout=5.0
    )
    if resp.status_code == 200:
        model = resp.json().get("model")
        if model and model.get("api_base") and model["api_base"] != "none":
            self._controller_model = model
            self.model_name = model.get("model_name", self.model_name)
        else:
            self._controller_model = "unavailable"
    else:
        self._controller_model = "unavailable"
```

The model config dict from the controller:
```json
{
  "model_name": "BAAI/bge-m3",
  "api_base": "https://api.openai.com/v1",
  "api_key": "sk-..."
}
```

### Embedding Request (`embed` — Tier 1 path)

```python
def embed(self, text: str) -> List[float]:
    self._load_controller()
    ctrl = self._controller_model
    if ctrl and ctrl != "unavailable":
        ep = ctrl.get("api_base")
        api_key = ctrl.get("api_key", "")
        resp = httpx.post(
            f"{ep}/embeddings",
            json={"model": ctrl.get("model_name", ""), "input": text},
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15.0,
        )
        if resp.status_code == 200:
            return resp.json()["data"][0]["embedding"]
```

Uses OpenAI-compatible `/v1/embeddings` endpoint. Returns a 1024-dimensional float list.

---

## Tier 2: Local sentence-transformers

**Priority:** Medium (fallback when controller unavailable)  
**Dimension:** 384 (`all-MiniLM-L6-v2` output)  
**Model:** `all-MiniLM-L6-v2` (hardcoded)

### Model Loading (`_load_local_model`)

```python
def _load_local_model(self):
    if EmbeddingService._model is None:
        try:
            from sentence_transformers import SentenceTransformer
            model_name = "all-MiniLM-L6-v2"
            EmbeddingService._model = SentenceTransformer(model_name)
            self._dimension = EmbeddingService._model.get_sentence_embedding_dimension()
            self.model_name = model_name
        except (ImportError, Exception) as e:
            EmbeddingService._model = "unavailable"
```

Note: When local model activates, `_dimension` changes from 1024 to 384. This affects the mock tier as well (through `self._dimension`).

### Embedding Request (Tier 2 path)

```python
self._load_local_model()
if self._model and self._model != "unavailable":
    return self._model.encode(text, show_progress_bar=False).tolist()
```

---

## Tier 3: Mock (Deterministic Hash)

**Priority:** Lowest (always available as last resort)  
**Dimension:** Follows whatever `self._dimension` was last set to

```python
def _mock_embed(self, text: str) -> List[float]:
    import hashlib, math
    b = hashlib.sha256(text.encode()).digest()
    return [math.sin(i * 7 + x) * 0.5 for i, x in enumerate(b[:self._dimension])]
```

**Properties:**
- **Deterministic:** Same text always produces the same vector
- **Dimension:** Uses `self._dimension` — 1024 for BGE-M3 path, 384 if local model was tried
- **Range:** [-0.5, 0.5] (sin-based, centered near 0)
- **Not semantically meaningful** — purely a placeholder that maintains API compatibility

---

## Dimension Handling

| Path         | Dimension | Model                  |
|--------------|-----------|------------------------|
| Controller   | 1024      | BAAI/bge-m3 (or configured) |
| Local ST     | 384       | all-MiniLM-L6-v2      |
| Mock         | 1024      | — (same as last active)|

The dimension can change at runtime depending on which tier activates. This is a known limitation — search quality may degrade if embeddings from different dimensions are mixed in the database.

---

## Batch Embedding

```python
def embed_batch(self, texts: List[str]) -> List[List[float]]:
    return [self.embed(t) for t in texts]
```

Simple sequential loop — no parallelization. For local model, the SentenceTransformer.encode() supports batch but is not used here.

---

## NodeEmbeddingStore

**File:** `app/services/node_embedding_store.py:14`

```python
class NodeEmbeddingStore:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = get_embedding_service()
```

### Building Embedding Input

```python
def _build_embedding_input(self, node: Node) -> str:
    parts = [f"name: {node.name}", f"type: {node.node_type}"]
    if node.signature:
        parts.append(f"signature: {node.signature}")
    if node.docstring:
        parts.append(f"docstring: {node.docstring}")
    if node.return_type:
        parts.append(f"return_type: {node.return_type}")
    if node.file_path:
        parts.append(f"file: {node.file_path}")
    return "\n".join(parts)
```

The embedding text is a structured key-value string:
```
name: authenticate_user
type: function
signature: def authenticate_user(token: str) -> User
docstring: Authenticate a user from a JWT token.
return_type: User
file: src/auth.py
```

Field inclusion is conditional — only non-None fields are added. This means two nodes with different metadata produce different embedding texts and therefore different vectors.

### Single Node Embedding

```python
async def compute_embedding(self, node: Node) -> None:
    text = self._build_embedding_input(node)
    content_hash = str(hash(text))
    embedding = self.embedding_service.embed(text)
    store = NodeEmbedding(
        node_id=node.id,
        project_id=node.project_id,
        embedding=json.dumps(embedding),       # JSON serialized
        embedding_model=self.embedding_service.model_name,
        content_hash=content_hash,
    )
    self.db.add(store)
```

### Batch Embedding

```python
async def compute_batch(self, nodes: List[Node]) -> None:
    texts = [self._build_embedding_input(n) for n in nodes]
    embeddings = self.embedding_service.embed_batch(texts)
    for node, emb in zip(nodes, embeddings):
        content_hash = str(hash(self._build_embedding_input(node)))
        store = NodeEmbedding(
            node_id=node.id,
            project_id=node.project_id,
            embedding=json.dumps(emb),
            embedding_model=self.embedding_service.model_name,
            content_hash=content_hash,
        )
        self.db.add(store)
```

NOTE: Does NOT call `await self.db.commit()` — relies on the caller to commit. In `_index_file_content()`, the caller calls `await self.db.flush()` after creating all nodes and before creating embeddings, so node IDs are available.

---

## Cosine Similarity

```python
def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    return dot / (na * nb + 1e-10)
```

Pure Python implementation — no NumPy dependency. The `+ 1e-10` prevents division by zero.

---

## Vector Search Algorithm

```python
async def vector_search(self, query: str, project_id: int,
                        top_k: int = 20) -> List[Tuple[int, float]]:
    # 1. Embed the query
    query_embedding = self.embedding_service.embed(query)

    # 2. Load ALL embeddings for the project
    result = await self.db.execute(
        select(NodeEmbedding).where(NodeEmbedding.project_id == project_id)
    )
    embeddings = result.scalars().all()

    # 3. Linear scan: compute cosine similarity for every embedding
    scored = []
    for emb in embeddings:
        try:
            stored = json.loads(emb.embedding) if isinstance(emb.embedding, str) else emb.embedding
            similarity = self._cosine_similarity(query_embedding, stored)
            scored.append((emb.node_id, similarity))
        except Exception:
            pass

    # 4. Sort descending and return top-k
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]
```

**Characteristics:**
- **Full table scan** — loads every `NodeEmbedding` for the project into Python
- **Linear `O(n)` scan** — no index, no approximation
- **JSON deserialization per row** — parsing the embedding from text
- **Scalability limit:** Works for moderate-sized projects (thousands of nodes). For very large codebases, consider adding a vector database or ANN index
- **Returns:** `List[Tuple[int, float]]` — (node_id, cosine_similarity) pairs

---

## Dedup via `content_hash`

The `NodeEmbedding.content_hash` column stores `str(hash(text))` — a Python hash of the embedding input text. This is NOT crypto-grade and can have collisions, but it's only used for reference, not for dedup logic. The unique constraint `(node_id, embedding_model)` is the actual dedup mechanism.

---

## Deletion

```python
async def delete_by_node(self, node_id: int) -> None:
    await self.db.execute(
        delete(NodeEmbedding).where(NodeEmbedding.node_id == node_id)
    )
```

Called during re-indexing when old nodes are deleted before new ones are created.

---

## Integration Points

### During Indexing (`_index_file_content`)
```python
if nodes_to_embed:
    try:
        store = NodeEmbeddingStore(self.db)
        await store.compute_batch(nodes_to_embed)
    except Exception as e:
        logger.warning(f"Failed to generate embeddings for {file_path}: {e}")
```
Embedding failure is non-fatal — indexing continues without embeddings. Search will fall back to exact+fuzzy scoring.

### During Search (`semantic_search`)
```python
store = NodeEmbeddingStore(self.db)
try:
    vec_results = await store.vector_search(query, project_id, top_k=top_k * 2)
    for node_id, score in vec_results:
        vector_scores[node_id] = score
except Exception as e:
    logger.warning(f"Vector search failed (falling back to exact): {e}")
```
Search failure is also non-fatal — vector score becomes 0 for all results.

---

## Future Improvements

Potential enhancements to the embedding system:
1. **Batch embedding with local ST** — Use `SentenceTransformer.encode(texts)` for tensor-level batching instead of sequential single-text calls
2. **ANN index** — Replace linear scan with FAISS/Qdrant for large projects
3. **Dimension normalization** — Ensure consistent dimensions regardless of active tier
4. **Crypto-grade content hash** — Use SHA256 instead of Python's `hash()` for content_hash
5. **Embedding caching** — Cache query embeddings during a session to avoid re-computing identical queries