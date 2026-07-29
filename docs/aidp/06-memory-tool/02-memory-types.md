# Memory Types & Tiers

Memory Tool supports three memory tiers via the `memory_tier` field.

## Memory Tiers

### 1. Episodic Memory

Event memory - records interactions and decisions at specific points in time.

- Time-associated, records "what happened"
- Use cases: debugging sessions, meeting notes, troubleshooting history
- Short lifespan, can be consolidated into semantic memory

### 2. Semantic Memory

Structured factual knowledge - the system's core knowledge base.

- Time-independent persistent knowledge
- Use cases: architecture docs, technical decision rationale, design patterns, API guides
- Default tier for most memories

### 3. Procedural Memory

Operational knowledge - procedures, workflows, best practices.

- Operation-oriented, describes "how to do"
- Use cases: deployment procedures, bug fix steps, code review checklists

---

## MemoryEntry Model

### Core Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `project` | String(100) | Project identifier |
| `user_id` | String(100) | User identifier |
| `category` | String(50) | Category (see below) |
| `title` | String(200) | Memory title |
| `content` | Text | Full memory content |
| `memory_tier` | String(20) | Tier, default `semantic` |

### Categories

| Value | Meaning | Graph Color |
|-------|---------|-------------|
| `architecture` | Architecture design records | Blue `#3b82f6` |
| `decision` | Technical decisions | Green `#10b981` |
| `pattern` | Design patterns | Amber `#f59e0b` |
| `issue` | Issue tracking | Red `#ef4444` |
| `bug` | Bug records | Dark red `#dc2626` |
| `other` | Miscellaneous | Gray `#6b7280` |

### Hierarchy & Relations

- **parent_id**: Self-referencing FK, builds tree-structured memory hierarchy
- **outgoing_relations / incoming_relations**: Graph edges via `MemoryRelation` model

### AI Fields

| Field | Type | Description |
|-------|------|-------------|
| `ai_suggested` | Boolean | Whether AI suggested this memory |
| `ai_review_status` | String(20) | Review status: `pending`/`approved`/`rejected` |
| `ai_review_comment` | Text | Review comments |
| `merged_from` | Text | JSON array of merged memory IDs |

### Usage Tracking

| Field | Type | Description |
|-------|------|-------------|
| `access_count` | Integer | Number of accesses (affects graph node radius) |
| `last_accessed_at` | DateTime | Last access timestamp |
| `confidence_score` | Float | 0.0-1.0 confidence level |

### Source Tracking

| Field | Type | Description |
|-------|------|-------------|
| `source_type` | String(50) | `manual`/`auto`/`imported`/`ai` |
| `source_uri` | String(500) | Source URI |

### Soft Delete & Timestamps

| Field | Type | Description |
|-------|------|-------------|
| `deleted_at` | DateTime | Soft delete timestamp |
| `created_at` | DateTime | Creation time (indexed) |
| `updated_at` | DateTime | Last update time |

### Embedding

| Field | Type | Description |
|-------|------|-------------|
| `embedding` | Vector(384) or Text | pgvector vector or JSON string fallback |

The embedding field uses **384 dimensions**. When pgvector is available, it uses `Vector(384)` type; otherwise falls back to `Text` (JSON string) for SQLite compatibility.

---

## Memory Entry Methods

### `to_dict(include_content=True)`
Converts memory to dictionary. When `include_content=False`, provides `content_preview` (first 200 chars) instead.

### `to_graph_node()`
Returns D3.js graph visualization format with:
- Color by category
- Radius based on access_count: `min(20, 5 + access_count * 0.5)`
- All core metadata fields

---

## Memory Tiers by Access Pattern

| Tier | Access Frequency | Retention | Consolidation |
|------|-----------------|-----------|---------------|
| episodic | High, short-term | Days to weeks | Merge into semantic |
| semantic | Moderate, persistent | Indefinite | Archive rarely |
| procedural | Low, on-demand | Indefinite | Update on change |