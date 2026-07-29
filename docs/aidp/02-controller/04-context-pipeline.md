# 5-Stage Context Pipeline

## Overview

The Context Pipeline (`apps/controller/app/services/context_pipeline.py`) is the core intelligence engine of AIDP. It assembles rich, task-aware context for every LLM call by executing 5 sequential stages. The pipeline is triggered by the `aidp_context` MCP tool and used internally by `aidp_instructions`.

### Architecture

```
apps/controller/app/services/context_pipeline.py   -- Pipeline implementation (395 lines)
apps/controller/app/services/context_cache.py       -- In-memory cache for Stage 2 results (TTL: 300s)
apps/controller/app/services/context_assembly.py    -- ContextAssembler with priority/dedup/compression
apps/controller/app/services/tool_retry.py          -- Retry mechanism (exp. backoff, max 3 retries)
```

### Key Data Class

**`PipelineContext`** (line 29-59) — Accumulator object passed through all stages:

```python
trace_id: str          # 8-char UUID
project_id: str        # From DB lookup
task: str              # User task description
instructions: dict     # Stage 0 output
intent: dict           # Stage 1 output
memories: list         # Stage 2 output
knowledge: list        # Stage 2 output
assets: list           # Stage 2 output
code_context: list     # Reserved, not yet populated
skills: list           # Stage 3 output
rules: list            # Stage 3 output
assembled_context: dict # Stage 4 output
stage_timings: dict    # Per-stage timing in ms
token_estimate: int    # Final token count
```

### Execution Entry Point

**`ContextPipeline.execute()`** (line 76-114) — Runs all 5 stages sequentially, printing a trace per stage:

```
[trace_id] Starting 5-Stage Pipeline for task: <task[:50]>...
[trace_id] Stage 0: Loaded instructions (Xms)
[trace_id] Stage 1: Intent analyzed - <intent> (Xms)
[trace_id] Stage 2: Retrieved X items (M:X K:X A:X) (Xms)
[trace_id] Stage 3: Matched X skills, X rules (Xms)
[trace_id] Stage 4: Context assembled (Xt, ratio:X) (Xms)
[trace_id] Pipeline completed in Xms
```

---

## Stage 0: Load Agent Instructions

**Code location:** `context_pipeline.py:116-151`, method `_stage_0_load_instructions()`

### Purpose

Loads the project's agent instructions from the database — role definition, constraints, and behavioral rules that shape how the LLM responds.

### Flow

1. Query `agent_instructions` table by `project_id` and `agent_type == "main"` (`line 120-126`)
2. If found: populate `ctx.instructions` with `role`, `constraints`, `rules`, `loaded_from_db: True` (`line 129-134`)
3. If not found: use default instructions:
   - Role: `"You are an AI programming assistant. Help users with code-related tasks."`
   - Constraints: `max_tokens: 4000`, `response_format: "markdown"`
   - Rules: `"Always provide code examples when relevant"`, `"Explain your reasoning step by step"`
   - `loaded_from_db: False` (`line 137-148`)

### Output Format

```python
ctx.instructions = {
    "role": str,           # Role/persona definition
    "constraints": dict,   # { "max_tokens": 4000, "response_format": "markdown" }
    "rules": list[str],    # Behavioral rules
    "loaded_from_db": bool # Whether instructions came from DB vs defaults
}
```

---

## Stage 1: Intent Analysis

**Code location:** `context_pipeline.py:153-214`, method `_stage_1_intent_analysis()` + `_fallback_intent_analysis()`

### Purpose

Analyzes the user's task description to determine intent, relevant domains, complexity, and whether the task is compound (needs splitting).

### Primary Path — SkillRouter

Invokes the `skill-router` tool with capability `"analyze_intent"` (`line 159-166`):

```python
tool_invoker.invoke("skill-router", "analyze_intent", {
    "task": ctx.task,
    "session_id": ctx.session_id
})
```

### Fallback Path — Rule-Based

`_fallback_intent_analysis()` (line 181-214) activated when SkillRouter is unavailable or fails:

**Domain detection** (keyword matching):

| Domain | Keywords |
|--------|----------|
| `api` | api, endpoint, route, request, response |
| `database` | database, sql, query, table, schema |
| `frontend` | ui, component, react, vue, html, css |
| `backend` | server, service, controller, middleware |
| `devops` | docker, deploy, ci/cd, kubernetes |
| `security` | auth, login, permission, encrypt |
| `testing` | test, unittest, e2e, mock |

**Complexity detection:**

| Complexity | Condition |
|------------|-----------|
| `"compound"` | task length > 200 chars, or contains "and"/"then" |
| `"complex"` | contains "implement", "create", "build", "design" |
| `"simple"` | default |

### Output Format

```python
ctx.intent = {
    "intent": str,        # Primary domain (e.g. "security") or "general"
    "domains": list[str], # All matched domains
    "complexity": str,    # "simple" | "complex" | "compound"
    "tags_needed": list,  # Same as domains (used as retrieval tags)
    "is_compound": bool,  # True if complexity == "compound"
}
```

---

## Stage 2: Staged Retrieval

**Code location:** `context_pipeline.py:216-283`, method `_stage_2_staged_retrieval()` + `_safe_retrieve()`

### Purpose

Retrieves relevant context from three knowledge sources **in parallel** using `asyncio.gather()`. Each source has independent error handling, retry, and fallback.

### Cache Layer

Before retrieval, checks `ContextCache` (TTL: 300 seconds) with key `(intent, tags, project_id)` (`line 223-236`). Cache hit returns immediately, skipping all tool calls.

### Retrieval Functions

| Source | Tool | Capability | Key Args | Code Location |
|--------|------|------------|----------|---------------|
| **Memory** | `memory-tool` | `memory.search` | `project`, `query`, `category` (1st domain), `limit=5` | `line 238-245` |
| **Knowledge** | `knowledge-tool` | `knowledge.search` | `query`, `top_k=5`, `task_domains` | `line 247-251` |
| **Asset** | `asset-tool` | `search` | `query`, `tags`, `top_k=3` | `line 253-257` |

### Error Handling

`_safe_retrieve()` (line 277-283) wraps each retrieval with:

- **Retry** — `RetryManager.execute_with_retry(func)` — max 3 retries, exponential backoff
- **Fallback** — If all retries fail, `FallbackManager.handle_tool_failure(tool_name, error)` returns a degradation entry:
  ```python
  {"title": f"{tool_name} degraded", "content": fallback_msg, "source": f"{tool_name}_fallback"}
  ```

### Parallel Execution

All three retrievals run concurrently via `asyncio.gather(..., return_exceptions=True)` (`line 259-264`), then results are assigned with exception guarding:

```python
ctx.memories = results[0] if not isinstance(results[0], Exception) else []
ctx.knowledge = results[1] if not isinstance(results[1], Exception) else []
ctx.assets = results[2] if not isinstance(results[2], Exception) else []
```

Cache is populated after retrieval (`line 270-271`).

### Output Format

```python
ctx.memories:  list[dict]  # Each: {"title": str, "content": str, ...}
ctx.knowledge: list[dict]  # Each: {"title": str, "content": str, ...}
ctx.assets:    list[dict]  # Each: {"name": str, "description": str, ...}
```

---

## Stage 3: Skill Matching

**Code location:** `context_pipeline.py:285-319`, method `_stage_3_skill_matching()`

### Purpose

Matches the user's task to available AI skills and project rules via the SkillRouter.

### Invocation

Calls `skill-router` with capability `"skill_run"` (`line 290-300`):

```python
tool_invoker.invoke("skill-router", "skill_run", {
    "task": ctx.task,
    "mode": "auto",
    "hint_tags": ctx.intent.get("tags_needed", []),
    "top_k": 6,
    "session_id": ctx.session_id
})
```

### Output Handling

If SkillRouter succeeds (`line 302-311`):

- `ctx.skills` — List of matched skill definitions with `name` and `content`
- `ctx.rules` — List of applicable rules
- `ctx.instructions["skill_instructions"]` — Skill-generated instructions
- `ctx.instructions["project_instructions"]` — Project-level instructions from router

If SkillRouter fails (`line 313-316`): both `skills` and `rules` default to empty lists.

### Output Format

```python
ctx.skills: list[dict]  # Each: {"name": str, "content": str, ...}
ctx.rules:  list[dict]  # Each: {"name": str, "content": str, ...}
ctx.instructions["skill_instructions"]: str    # (optional)
ctx.instructions["project_instructions"]: str  # (optional)
```

---

## Stage 4: Context Assembly

**Code location:** `context_pipeline.py:321-383`, method `_stage_4_assembly()`

### Purpose

Assembles all data from previous stages into a compact, ranked context package suitable for LLM consumption. Uses `ContextAssembler` with `max_tokens=8000` for priority-based truncation, deduplication, and compression.

### Assembly Order

Items are collected with `source`, `content`, `relevance_score`, and `metadata` fields, then passed to `self.assembler.assemble(items)` (`line 357`).

| Priority (Score) | Source | Content | Line |
|------------------|--------|---------|------|
| **1.0** | `instructions` | `role` string | `line 326-327` |
| **0.9** | `instructions` | `constraints` as `"key: value"` lines | `line 330-333` |
| **0.8** | `instructions` | `rules` as `"- rule"` lines | `line 335-338` |
| **0.7** | `instructions` | `project_instructions` (if present from Stage 3) | `line 340-342` |
| **0.6** | `memory` | Title + content[:500] — top 3 items only | `line 344-346` |
| **0.6** | `knowledge` | Title + content[:500] — top 3 items only | `line 347-349` |
| **0.4** | `asset` | `"name: description"` — all items | `line 350-352` |
| **0.5** | `skill` | `name` + content[:800] — top 4 items | `line 353-355` |

### Output

```python
ctx.assembled_context = {
    "system_prompt": str,        # Assembled context text (truncated via priority)
    "user_message": str,         # Original task
    "compression_ratio": float,  # Compression applied by assembler
    "metadata": {
        "trace_id": str,
        "project_id": str,
        "intent": str,
        "complexity": str,
        "sources": {
            "memories": int,
            "knowledge": int,
            "assets": int,
            "skills": int,
            "rules": int
        },
        "cache_stats": dict,
        "fallback_status": dict
    }
}
ctx.token_estimate: int  # Total estimated tokens
```

---

## Error Handling Summary

| Stage | Error Behavior |
|-------|---------------|
| **0** | If DB row missing → use hardcoded defaults (never fails) |
| **1** | If SkillRouter fails → rule-based fallback with keyword matching |
| **2** | Each source independent: retry 3x with exp. backoff, then fallback degradation entry |
| **3** | If SkillRouter fails → empty `skills` and `rules` lists |
| **4** | Assembler handles empty input gracefully |

---

## Dependency Graph

```
Stage 0 (instructions)
    ↓
Stage 1 (intent: uses skill-router, "analyze_intent")
    ↓ tags_needed, domains
Stage 2 (retrieval: memory-tool, knowledge-tool, asset-tool — in parallel)
    ↓ memories, knowledge, assets
Stage 3 (skills: uses skill-router, "skill_run")
    ↓ skills, rules, additional instructions
Stage 4 (assembly: priority ranking + token compression)
    → assembled_context, token_estimate
```

### Exact Capability Names Used

| Stage | Tool | Capability |
|-------|------|------------|
| Stage 1 | `skill-router` | `analyze_intent` |
| Stage 2 | `memory-tool` | `memory.search` |
| Stage 2 | `knowledge-tool` | `knowledge.search` |
| Stage 2 | `asset-tool` | `search` |
| Stage 3 | `skill-router` | `skill_run` |