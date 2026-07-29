# MCP Server — AIDP Controller Tools

## Overview

The MCP server (`apps/controller/app/mcp/server.py`) exposes 8 tools via `fastmcp.FastMCP`, allowing AI agents to interact with the AIDP platform through the Model Context Protocol (MCP). The server is named `"aidp-controller"` and enforces a strict tool-calling order: **`aidp_context` must be called first** before any other tool invocation.

### Architecture

```
app/mcp/server.py          -- FastMCP server + 8 @mcp.tool() endpoints
app/mcp/session_manager.py -- Session-level enforcement of aidp_context-first ordering
```

---

## Tool 1: `aidp_context` — 5-Stage Context Pipeline

**Code location:** `apps/controller/app/mcp/server.py:330-431`

This is the **mandatory first call** before any other tool. It triggers the full 5-stage Context Pipeline to assemble rich context for the current task.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ctx` | `Context` | (auto) | FastMCP session context (injected automatically) |
| `project_name` | `str` | required | Project name (e.g. `"aidp"`) |
| `task` | `str` | `""` | Natural language task description |
| `agent_type` | `str` | `"main"` | Agent type: `"main"` or `"subagent:sandbox-tool"` etc. |

### Flow

1. **Project lookup** — Queries `aidp_projects` table by `project_name` to get `project_id` (`server.py:370-374`)
2. **Pipeline init** — Creates `ContextPipeline(db)` instance (`server.py:376`)
3. **Execute 5 stages** — `pipeline.execute(task, project_id, session_id)` (`server.py:377-381`)
4. **Build response** — Extracts structured results from each stage:
   - `stage0_instructions`: role, rules_count, loaded_from_db (`server.py:385-389`)
   - `stage1_intent`: intent, domains, complexity, is_compound (`server.py:391-396`)
   - `stage2_retrieval`: memories count, knowledge count, assets count (`server.py:398-402`)
   - `stage3_skills`: matched skills count, rules count (`server.py:404-407`)
   - `stage4_assembly`: token_estimate, timing (`server.py:409-412`)
   - Full `context` (system_prompt truncated to 5000 chars), `user_message`, `estimated_tokens`, `metadata` (`server.py:415-419`)
5. **Session marking** — `session_manager.mark_context_loaded(session_id, result)` marks this session as context-loaded (`server.py:428`)

### Return Format

```json
{
  "project_name": "aidp",
  "task": "fix login bug",
  "agent_type": "main",
  "trace_id": "a1b2c3d4",
  "stages": {
    "stage0_instructions": {
      "role": "You are an AI programming assistant...",
      "rules_count": 2,
      "loaded_from_db": true
    },
    "stage1_intent": {
      "intent": "security",
      "domains": ["security", "backend"],
      "complexity": "simple",
      "is_compound": false
    },
    "stage2_retrieval": {
      "memories": 3,
      "knowledge": 2,
      "assets": 0
    },
    "stage3_skills": {
      "matched": 1,
      "rules": 1
    },
    "stage4_assembly": {
      "token_estimate": 1500,
      "timing_ms": 45
    }
  },
  "context": "... truncated system_prompt ...",
  "user_message": "fix login bug",
  "estimated_tokens": 1500,
  "stage_timings": { "stage_0": 5, "stage_1": 120, "stage_2": 350, "stage_3": 80, "stage_4": 45 },
  "metadata": { "trace_id": "a1b2c3d4", "project_id": "1", "intent": "security", ... }
}
```

---

## Tool 2: `aidp_init` — Project Initialization

**Code location:** `apps/controller/app/mcp/server.py:250-327`

Initializes a new project into AIDP. Creates/updates the project record in the unified `aidp_projects` table, then delegates to `init_project()` for full initialization including code indexing, doc import, memory creation, asset registration, and tool capability sync.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `project_name` | `str` | required | Unique project name |
| `description` | `str` | `""` | Project description |
| `tech_stack` | `str` | `""` | Tech stack description (e.g. `"Python 3.13 + FastAPI + PostgreSQL"`) |
| `nas_path` | `str` | `""` | NAS project path |
| `docs` | `str` | `"[]"` | JSON array of `[{"title":"...", "content":"..."}]` |
| `key_files` | `str` | `"[]"` | JSON array of `[{"path":"main.py", "content":"...", "type":"python"}]` |
| `architecture_summary` | `str` | `""` | Architecture overview |

### Flow

1. **Parse JSON params** — `docs`, `key_files` parsed from JSON strings with fallback to empty lists (`server.py:282-291`)
2. **Project upsert** — Queries `aidp_projects` by name; creates if not found, updates description if exists (`server.py:298-316`)
3. **Delegate init** — Calls `init_project()` from `app/services/project_init_service.py` (`server.py:317-325`)
4. **Inject project_id** — The newly created/updated project ID is added to the result (`server.py:326`)

### Return Format

```json
{
  "project_id": 42,
  "project_name": "my-web-app",
  "steps": [
    { "step": "create_project", "status": "ok", "result": { "project_id": 42 } },
    { "step": "code_index", "status": "ok", "result": { "project_id": "ci-99", "files_indexed": 120 } },
    { "step": "import_docs", "status": "ok", "result": { "docs_attempted": 5, "docs_imported": 5 } },
    ...
  ],
  "errors": [],
  "summary": {
    "docs_imported": 5,
    "memories_created": 2,
    "assets_registered": 3,
    "total_steps": 8,
    "total_errors": 0
  }
}
```

---

## Tool 3: `aidp_instructions` — Sub-Agent Instruction Generation

**Code location:** `apps/controller/app/mcp/server.py:434-523`

Generates specialized instructions for sub-agents when complex tasks need to be split into parallel subtasks.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `project_name` | `str` | required | Project name |
| `task` | `str` | required | Sub-agent task description |
| `agent_type` | `str` | `"subagent:sandbox-tool"` | Sub-agent type identifier |

### Flow

1. **Project lookup** — Queries `auth_models.Project` by name (`server.py:480-484`)
2. **Pipeline execute** — Runs full `ContextPipeline` for the sub-agent task (`server.py:486-490`)
3. **Build instructions** — Assembles `subagent_instructions` including:
   - `role`: Derived from pipeline instructions + domain specialization (`server.py:497`)
   - `context`: relevant_memories (titles, top 3), relevant_knowledge (titles, top 3), available_skills (names, top 3), constraints (`server.py:500-504`)
   - `allowed_tools`: `["memory-tool", "knowledge-tool", "asset-tool", "sandbox-tool", "quality-tool"]` (`server.py:506-512`)
   - `parent_trace_id`: Links back to pipeline trace (`server.py:513`)

### Return Format

```json
{
  "project_name": "aidp",
  "task": "run unit tests",
  "agent_type": "subagent:sandbox-tool",
  "trace_id": "e5f6g7h8",
  "subagent_instructions": {
    "agent_type": "subagent:sandbox-tool",
    "role": "You are a specialized subagent for security. You are an AI programming assistant...",
    "task": "run unit tests",
    "specialization": "security",
    "context": {
      "relevant_memories": ["Cookie修复", "登录问题分析"],
      "relevant_knowledge": ["API鉴权规范"],
      "available_skills": ["code-review-skill"],
      "constraints": { "max_tokens": 4000 }
    },
    "allowed_tools": ["memory-tool", "knowledge-tool", "asset-tool", "sandbox-tool", "quality-tool"],
    "parent_trace_id": "e5f6g7h8"
  }
}
```

---

## Tool 4: `invoke_tool_mcp` — Universal Tool Invocation

**Code location:** `apps/controller/app/mcp/server.py:30-94`

The universal tool invocation endpoint. Calls any registered AIDP tool's capability. **Enforces that `aidp_context` was called first** via session manager.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ctx` | `Context` | (auto) | FastMCP session context |
| `tool_name` | `str` | required | Tool name: `"sandbox-tool"`, `"quality-tool"`, `"memory-tool"`, `"knowledge-tool"`, `"skillrouter"`, `"asset-tool"` |
| `capability` | `str` | required | Capability: `"sandbox.execute"`, `"quality.check"`, `"memory.search"`, etc. |
| `arguments` | `str` | `"{}"` | JSON arguments string |
| `user_id` | `int` | `0` | User ID (0 = system) |
| `api_key` | `str` | `""` | API key from `.opencode/opencode.jsonc` |

### Flow

1. **API key extraction** — If `api_key` is empty, attempts to read `x-api-key` from request headers (`server.py:66-72`)
2. **Session enforcement** — `session_manager.can_call_tool(session_id, tool_name)` checks whether `aidp_context` was called in this session; returns `CONTEXT_REQUIRED` error if not (`server.py:75-85`)
3. **Argument parsing** — Parses `arguments` JSON string; falls back to `{}` on decode error (`server.py:88-90`)
4. **Record invocation** — `session_manager.record_tool_call(session_id, f"{tool_name}:{capability}")` (`server.py:92`)
5. **Invoke tool** — `invoke_tool(tool_name, capability, args, user_id)` via the ToolInvoker (`server.py:93`)

### Return Format

```json
{
  "success": true,
  "output": { ... tool-specific result ... }
}
```

On context-not-loaded error:
```json
{
  "success": false,
  "error": {
    "code": "CONTEXT_REQUIRED",
    "message": "AIDP context has not been loaded for this session",
    "hint": "请先调用 aidp_context(project_name='aidp', task='你的任务描述')"
  }
}
```

---

## Tool 5: `list_registered_tools` — Tool Registry Listing

**Code location:** `apps/controller/app/mcp/server.py:97-117`

Lists all registered AIDP tools with their capabilities and health status.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | `str` | `""` | Filter by status: `"healthy"`, `"unhealthy"`, `"unknown"`, or empty for all |

### Flow

1. Calls `list_tools(status=status or None)` from `app/services/tool_registry.py` (`server.py:116`)

### Return Format

```json
[
  {
    "name": "sandbox-tool",
    "display_name": "Code Sandbox",
    "capabilities": ["sandbox.execute", "sandbox.health"],
    "status": "healthy",
    "last_check": "2026-07-28T10:00:00"
  },
  ...
]
```

---

## Tool 6: `check_tool_health` — Health Checking

**Code location:** `apps/controller/app/mcp/server.py:120-142`

Checks the health status of one or all registered AIDP tools.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tool_name` | `str` | `""` | Specific tool name, or empty for all tools |

### Flow

1. If `tool_name` is provided: calls `health_check_tool(tool_name)` (`server.py:139`)
2. If empty: calls `health_check_all()` (`server.py:141`)
3. Both functions are from `app/services/tool_registry.py`

### Return Format

```json
{
  "sandbox-tool": { "status": "healthy", "response_time_ms": 45 },
  "quality-tool": { "status": "unhealthy", "response_time_ms": null, "error": "Connection refused" }
}
```

---

## Tool 7: `sync_tool_capabilities` — Capability Sync

**Code location:** `apps/controller/app/mcp/server.py:145-164`

Re-syncs a tool's capabilities from its manifest file. Typically only needed after a tool update.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tool_name` | `str` | required | Tool to sync (e.g. `"sandbox-tool"`) |

### Flow

1. Calls `sync_capabilities(tool_name)` from `app/services/tool_registry.py` (`server.py:163`)

### Return Format

```json
{
  "success": true,
  "tool_name": "sandbox-tool",
  "capabilities": [
    { "name": "sandbox.execute", "description": "Execute code in sandbox", "parameters": {...} }
  ]
}
```

---

## Tool 8: `manage_models` — LLM Model Management

**Code location:** `apps/controller/app/mcp/server.py:167-247`

Unified CRUD interface for managing LLM model configurations used across all AIDP tools.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `action` | `str` | `"list"` | Operation: `"list"`, `"get"`, `"get_best"`, `"create"`, `"update"`, `"delete"` |
| `task_type` | `str` | `""` | Filter/get-best by task type: `"chat"`, `"embedding"`, `"code"` |
| `model_id` | `int` | `0` | Model ID for `get`/`update`/`delete` |
| `name` | `str` | `""` | Display name (for create/update) |
| `provider` | `str` | `""` | Provider: `"OpenAI"`, `"DeepSeek"`, `"Local"` |
| `model_name` | `str` | `""` | Model identifier: `"deepseek-chat"`, `"text-embedding-3-small"` |
| `api_base` | `str` | `""` | API base URL |
| `task_types` | `str` | `"[]"` | JSON array of task types (for create/update) |
| `priority` | `int` | `0` | Priority (higher = preferred) |

### Flow

- **`list`**: Calls `ModelService.list_models()` or `ModelService.get_by_task(task_type)` (`server.py:204-208`)
- **`get_best`**: Calls `ModelService.get_best_for_task(task_type)` (`server.py:213-214`)
- **`get`**: Calls `ModelService.get_model(model_id)` (`server.py:217`)
- **`create`**: Parses `task_types` JSON, then `ModelService.create_model({...})` (`server.py:220-226`)
- **`update`**: Builds partial update dict from non-empty params, then `ModelService.update_model(model_id, updates)` (`server.py:228-238`)
- **`delete`**: `ModelService.delete_model(model_id)` (`server.py:240-242`)

### Return Format (list)

```json
{
  "items": [
    { "id": 1, "name": "DeepSeek", "provider": "DeepSeek", "model_name": "deepseek-chat", "task_types": ["chat","code"], "priority": 10 },
    ...
  ],
  "total": 5
}
```

### Return Format (create/update)

```json
{
  "success": true,
  "model": { "id": 2, "name": "GPT-4", "provider": "OpenAI", "model_name": "gpt-4", "task_types": ["chat"], "priority": 5 }
}
```

---

## Session Enforcement

The `session_manager` (`apps/controller/app/mcp/session_manager.py`) enforces that `aidp_context` is called before any other tool can be invoked:

- **`mark_context_loaded(session_id, result)`** — Marks a session as having loaded context (called at end of `aidp_context`, server.py:428)
- **`can_call_tool(session_id, tool_name)`** — Returns `(allowed: bool, reason: str)`; blocks `invoke_tool_mcp` if context not loaded
- **`record_tool_call(session_id, tool_name)`** — Logs each tool invocation in the session