# Memory Tool Database Schema

The Memory Tool uses PostgreSQL with optional pgvector extension. Falls back to SQLite-compatible Text storage for embeddings when pgvector is unavailable.

---

## `memory_entries` - Memory Records

| Column | Type | Indexed | Description |
|--------|------|---------|-------------|
| `id` | UUID PK | - | Primary key |
| `project` | String(100) | Yes | Project identifier |
| `user_id` | String(100) | Yes | User identifier |
| `category` | String(50) | Yes | Category: architecture, decision, pattern, issue, bug, other |
| `title` | String(200) | - | Memory title |
| `content` | Text | - | Full memory content |
| `embedding` | Vector(384) or Text | - | Vector embedding for semantic search |
| `memory_tier` | String(20) | Yes | episodic, semantic (default), procedural |
| `parent_id` | UUID FK → memory_entries.id | Yes | Parent memory for hierarchy |
| `confidence_score` | Float | - | 0.0-1.0 confidence (default 1.0) |
| `ai_suggested` | Boolean | Yes | AI-generated flag (default false) |
| `ai_review_status` | String(20) | - | pending, approved (default), rejected |
| `ai_review_comment` | Text | - | Review comments |
| `merged_from` | Text | - | JSON array of merged memory IDs |
| `access_count` | Integer | - | Usage counter (default 0) |
| `last_accessed_at` | DateTime | - | Last access timestamp |
| `source_type` | String(50) | - | manual (default), auto, imported, ai |
| `source_uri` | String(500) | - | Source reference URI |
| `deleted_at` | DateTime | - | Soft delete timestamp |
| `created_at` | DateTime | Yes | Creation time |
| `updated_at` | DateTime | - | Last update (auto-updated) |

**Relationships**:
- `parent` (self-referencing to MemoryEntry) with `children` back-populates
- `outgoing_relations` (to MemoryRelation via `source_id`)
- `incoming_relations` (to MemoryRelation via `target_id`)

---

## `memory_relations` - Memory Graph Edges

| Column | Type | Indexed | Description |
|--------|------|---------|-------------|
| `id` | UUID PK | - | Primary key |
| `source_id` | UUID FK → memory_entries.id | Yes | Source memory (CASCADE delete) |
| `target_id` | UUID FK → memory_entries.id | Yes | Target memory (CASCADE delete) |
| `relation_type` | String(50) | Yes | similar (default), parent_child, reference, sequence, related |
| `strength` | Float | - | Relationship strength 0.0-1.0 (default 0.5) |
| `created_at` | DateTime | - | Creation time |

**Constraint**: `UNIQUE(source_id, target_id, relation_type)` - prevents duplicate relations.

**Relation Type Colors** (for graph visualization):
| Type | Color |
|------|-------|
| `similar` | `#94a3b8` (slate) |
| `parent_child` | `#3b82f6` (blue) |
| `reference` | `#10b981` (green) |
| `sequence` | `#f59e0b` (amber) |
| `related` | `#6b7280` (gray) |

---

## `context_packages` - User-Generated Context Bundles

| Column | Type | Indexed | Description |
|--------|------|---------|-------------|
| `id` | UUID PK | - | Primary key |
| `name` | String(200) | - | Package name |
| `description` | Text | - | Package description |
| `project` | String(100) | Yes | Associated project |
| `created_by` | String(100) | - | Creator |
| `memory_ids` | Text | - | JSON array of memory IDs |
| `generated_context` | Text | - | Pre-generated context string |
| `total_tokens` | Integer | - | Estimated token count (default 0) |
| `is_template` | Boolean | Yes | Reusable template flag (default false) |
| `usage_count` | Integer | - | Number of times used (default 0) |
| `created_at` | DateTime | - | Creation time |
| `updated_at` | DateTime | - | Last update (auto-updated) |

**Methods**:
- `to_dict(include_context=False)`: Serializes to dict, optionally including `generated_context`

---

## Legacy Models

### `mem_node` - Legacy Memory Nodes
| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `memory_id` | Integer | Memory reference |
| `label` | String(256) | Node label |
| `memory_type` | String(20) | Type string |
| `created_at` | DateTime | Creation time |

### `mem_edge` - Legacy Memory Edges
| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `source_id` | Integer | Source node |
| `target_id` | Integer | Target node |
| `relation` | String(64) | Relation type |
| `weight` | Float | Edge weight (default 1.0) |
| `created_at` | DateTime | Creation time |

---

## ER Diagram

```
memory_entries (self-referencing via parent_id)
    ├──< memory_relations (source_id + target_id)
    └── [ standalone ]

context_packages (independent, references memory_entries via JSON memory_ids)

mem_node ──< mem_edge
  (legacy, independent)
```

## Vector Support Detection

```python
try:
    from pgvector.sqlalchemy import Vector
    VECTOR_AVAILABLE = True
except ImportError:
    VECTOR_AVAILABLE = False  # Falls back to Text column
```

The `embedding` column is:
- `Vector(384)` when pgvector is available (PostgreSQL)
- `Text` when pgvector is unavailable (SQLite fallback)