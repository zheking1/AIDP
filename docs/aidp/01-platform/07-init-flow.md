# AIDP Init Flow

## Overview

The `aidp_init` flow is the process of onboarding a new project into the AIDP platform. It has two main code paths:

1. **MCP `aidp_init()` tool** — Full-service init via MCP, runs on the server side (`apps/controller/app/mcp/server.py:250-327` → `apps/controller/app/services/project_init_service.py:60-283`)
2. **REST `POST /api/projects/{id}/init`** — Task-based init, some tasks run locally (`apps/controller/app/routers/projects_new.py:303-393`)

Both flows converge on a unified data model and project structure.

---

## Architecture: What Runs Where

```
                    ┌──────────────────────────────┐
                    │     AIDP Controller (NAS)     │
                    │                               │
  User/Agent        │   aidp_init() MCP Tool         │
  ─────────►       │   ├─ Create project record     │
                    │   ├─ Code-index (server)       │
                    │   ├─ Knowledge-tool docs        │
                    │   ├─ Memory-tool entries        │
                    │   ├─ Asset-tool registration   │
                    │   └─ Sync all tool capabilities │
                    │                               │
                    │   projects_new.py /init        │
                    │   ├─ code_index       (NAS)    │
                    │   ├─ doc_import       (NAS)    │
                    │   ├─ mcp_register     (NAS)    │
                    │   ├─ official_docs    (NAS)    │
                    │   ├─ rules_extract    (NAS)    │
                    │   ├─ agent_setup      (NAS)    │
                    │   └─ file_watcher ─────────►  ↓
                    │       git_hook    ─────────►  ↓
                    │       tech_analysis ────────►  ↓
                    └──────────────────────────────┘
                                                    │
                    ┌──────────────────────────────┐
                    │     User's Local Machine     │
                    │                               │
                    │   python scripts/aidp_init.py │
                    │   --project-id {id}           │
                    │   --controller-url {url}      │
                    │   --task file_watcher          │
                    │                               │
                    │   Installs:                   │
                    │   - File watcher              │
                    │   - Git hooks                 │
                    │   - Runs tech_scan.py         │
                    └──────────────────────────────┘
```

---

## Flow 1: MCP `aidp_init()` Tool (Server-Side)

**Entry point:** `apps/controller/app/mcp/server.py:250-327`, function `aidp_init()`
**Core logic:** `apps/controller/app/services/project_init_service.py:60-283`, function `init_project()`

### Parameters (MCP)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `project_name` | str | required | Unique project name |
| `description` | str | `""` | Project description |
| `tech_stack` | str | `""` | e.g. `"Python 3.13 + FastAPI + PostgreSQL"` |
| `nas_path` | str | `""` | Project path on NAS (e.g. `"/home/docker/projects/myapp"`) |
| `docs` | str | `"[]"` | JSON array of `[{"title":"...", "content":"..."}]` |
| `key_files` | str | `"[]"` | JSON array of `[{"path":"...", "content":"...", "type":"..."}]` |
| `architecture_summary` | str | `""` | Architecture overview text |

### 9 Initialization Steps

All steps run sequentially inside `init_project()`. Each step records a `{"step": name, "status": "ok"|"error", "result": {...}}` entry.

#### Step 1: Create Project Record (`project_init_service.py:84-100`)

Creates a row in `aidp_projects` table with:
- `name` = project_name
- `description` = provided description or `"{name} - initialized via aidp init"`
- `status` = `"active"`

Returns `project_id` (integer).

#### Step 2: Import via Project Importer (`project_init_service.py:103-113`)

**Only runs if `nas_path` is provided.**

Invokes `project-importer` tool with capability `project.import`:
```python
invoke_tool("project-importer", "project.import", {
    "path": nas_path,
    "name": project_name,
    "type": tech_stack or "python"
})
```

#### Step 3: Code Indexing (`project_init_service.py:116-145`)

Creates a code-index project and scans files:

1. Determine effective path: `nas_path` or `settings.NAS_PATH`
2. Invoke `code-index` → `code.create_project` with `name` and `path`
3. If project_id received, invoke `code-index` → `code.scan_project` with `project_id`
4. Returns `files_indexed` count

#### Step 4: Upload Key Files to Code-Index (`project_init_service.py:148-168`)

**Only if `key_files` provided and code-index project exists.**

For each file (up to 50), invokes `code-index` → `code.index_file`:
```python
{
    "project_id": ci_pid,
    "file_path": file["path"],
    "content": file["content"],
    "language": file["type"]  # e.g. "python"
}
```

#### Step 5: Store Docs in Knowledge-Tool (`project_init_service.py:171-192`)

**Only if `docs` provided.**

For each document (up to 50), invokes `knowledge-tool` → `knowledge.create_document`:
```python
{
    "workspace_id": "default",
    "title": doc["title"],
    "doc_type": "markdown",
    "content": doc["content"],
    "project_id": str(project_id),
    "source_uri": doc["title"]
}
```

#### Step 6: Create Memories in Memory-Tool (`project_init_service.py:194-234`)

Creates up to 3 memory entries:

| Trigger | Category | Title | Content |
|---------|----------|-------|---------|
| `architecture_summary` provided | `"architecture"` | `"架构概述"` | architecture_summary text |
| `tech_stack` provided | `"architecture"` | `"技术栈"` | `"{name} 技术栈: {tech_stack}"` |
| `description` provided | `"architecture"` | `"项目描述"` | description text |

Each invokes `memory-tool` → `memory.create` with `project`, `category`, `title`, `content`, `tags`.

#### Step 7: Register Assets (`project_init_service.py:236-257`)

**Only if `key_files` provided.**

For each file (up to 30), invokes `asset-tool` → `asset.create`:
```python
{
    "name": file["path"],
    "content": file["content"],
    "asset_type": file["type"],
    "tags": [file["type"]],
    "project_id": str(project_id)
}
```

#### Step 8: Sync Tool Capabilities (`project_init_service.py:259-269`)

Syncs capabilities for all 7 tools:
```python
for tool in ["knowledge-tool", "memory-tool", "asset-tool", "sandbox-tool", "quality-tool", "skillrouter", "code-index"]:
    sync_capabilities(tool_name)
```

#### Step 9: Return Summary (`project_init_service.py:271-283`)

Returns structured result with `project_id`, `project_name`, `steps` list, `errors` list, and summary counts.

---

## Flow 2: REST Init (Mixed Server/Local)

**Entry point:** `apps/controller/app/routers/projects_new.py:303-393`, `run_init()`

The REST init endpoint uses a task-based model with 9 defined tasks (`INIT_TASKS` at `models/project_new.py:159-169`). Each task is tracked in `aidp_project_init_tasks`.

### Task Execution Flow

```
1. POST /api/projects/{id}/init → run_init()
2. Seed any missing task records as "pending"
3. For each task:
   a. Set status → "running", record started_at
   b. Execute task function
   c. On error with skip → "skipped"
   d. On error → "failed", store error_msg
   e. On success → "completed", store metadata_json
   f. Record completed_at
4. Return all task results + overall init-status
```

### Server-Side Tasks (Run on NAS)

| task_id | Function | What Happens |
|---------|----------|-------------|
| `code_index` | `_run_code_index()` | POSTs to code-index API to create project, registers `ProjectMapping` |
| `doc_import` | `_run_doc_import()` | Creates project-level `KnowledgeBase` in DB |
| `mcp_register` | `_run_mcp_register()` | Health-checks required tools (code-index, doc-index, skillrouter) |
| `official_docs` | `_run_official_docs()` | Reads tech_stack from project, maps to known official doc URLs |
| `rules_extract` | `_run_rules_extract()` | Queries knowledge documents with category `"code_style"` |
| `agent_setup` | `_run_agent_setup()` | Creates default project agent record |

### Local Tasks (Run on User's Machine)

These tasks return a shell command; execution happens on the user's local machine:

| task_id | Command |
|---------|---------|
| `file_watcher` | `python scripts/aidp_init.py --project-id {id} --controller-url {url} --task file_watcher` |
| `git_hook` | `python scripts/aidp_init.py --project-id {id} --controller-url {url} --task git_hook` |
| `tech_analysis` | `python scripts/tech_scan.py --project-id {id} --controller-url {url}` |

The `_run_local_setup()` function (line 488-496) generates these commands. The user must execute them on their local machine where the project source code resides.

### Why Some Tasks Run Locally

- **file_watcher**: Needs filesystem access to watch for file changes
- **git_hook**: Needs to install hooks in the local `.git/hooks/` directory
- **tech_analysis**: Needs local file scanning to detect tech stack from project files

The `CONTROLLER_URL` environment variable (default: `http://localhost:8883`) tells local scripts where to send results back to.

---

## Project Mappings

**Model:** `ProjectMapping` at `apps/controller/app/models/project_new.py:137-156`
**Table:** `aidp_project_mappings`

### Purpose

Since each AIDP tool has its own internal project ID, the mapping table links the controller's project ID to each tool's equivalent:

```
controller_project_id (42)
    ├─ tool_name: "code-index"    → tool_project_id: "ci-abc123"
    ├─ tool_name: "skillrouter"   → tool_project_id: "sr-xyz789"
    └─ tool_name: "knowledge-tool"→ tool_project_id: "kb-default-42"
```

### When Mappings Are Created

| Flow | When | By Which Function |
|------|------|------------------|
| REST `code_index` task | `_run_code_index()` creates code-index project | `projects_new.py:432-445` |
| MCP `aidp_init` Step 3 | Code index project creation | (handled implicitly by code-index tool) |

Mappings are returned in the `GET /api/projects/{id}/verify` response.

---

## Verify Flow

**Endpoint:** `GET /api/projects/{project_id}/verify`
**Code location:** `projects_new.py:628-772`

After init, the verify endpoint checks the health of the project across all integrated tools. Defines 7 checks at `VERIFY_CHECKS` (line 617-625):

| # | Check | Source | Validation | Severity |
|---|-------|--------|------------|----------|
| 1 | 代码索引 | sqlite3 `/app/data/code_index.db` | `COUNT(*) FROM nodes WHERE project_id=?` > 0 | error if 0 |
| 2 | 文档导入 | `aidp_knowledge_documents` | Count > 0 | error if 0 |
| 3 | 技术栈分析 | `aidp_projects.tech_stack` | Non-empty JSON array | warn if empty |
| 4 | 官方文档 | `aidp_knowledge_bases` with `kb_level="framework"` | Count > 0 | warn if 0 |
| 5 | 规则提取 | `rules` table | Count > 0 | warn if 0 |
| 6 | Agent 创建 | `agents` table (active) | Count > 0 | warn if 0 |
| 7 | MCP 注册 | `list_tools()` from registry | All `{code-index, doc-index, skillrouter, memory-tool, knowledge-tool}` healthy | error if missing |

### Verify Response

```json
{
  "project_id": 42,
  "project_name": "my-app",
  "owner_id": "user-1",
  "checks": [
    { "task_id": "code_index", "name": "代码索引", "passed": true, "detail": "code-index 中 152 个节点", "severity": "ok" },
    { "task_id": "doc_import", "name": "文档导入", "passed": true, "detail": "knowledge 库中 8 篇文档", "severity": "ok" },
    ...
  ],
  "mappings": [
    { "controller_project_id": 42, "tool_name": "code-index", "tool_project_id": "ci-abc" }
  ],
  "summary": "7/7 检查通过",
  "all_passed": true
}
```

---

## Common Issues

### 1. "Project not found" on init-status/verify
**Cause:** Project record not created or soft-deleted (`deleted_at` IS NOT NULL).
**Check:** Query `aidp_projects WHERE id = ? AND deleted_at IS NULL`.

### 2. code-index has 0 nodes
**Cause:** Local file scanning never ran. The REST init only creates the project in code-index; actual scanning requires running the local script.
**Fix:** Run `python scripts/aidp_init.py --project-id {id} --controller-url {url} --task tech_scan` on the local machine.

### 3. MCP tools unhealthy (verify check 7)
**Cause:** Required tools (`code-index`, `doc-index`, `skillrouter`, `memory-tool`, `knowledge-tool`) not registered or not healthy.
**Check:** `GET /api/tools` to see registered tools and their health status. Tools must self-register by calling `POST /api/tools` on startup.

### 4. tech_stack is empty after tech_analysis
**Cause:** `python scripts/tech_scan.py` may have failed or not been run.
**Fix:** Run tech_scan locally; it analyzes project files and updates `aidp_projects.tech_stack`.

### 5. "Tools not healthy" in MCP register
**Cause:** Required tools not yet registered with the controller.
**Check:** Ensure all tool services are running and have registered. Each tool should POST to `{controller}/api/tools` on startup.

### 6. Duplicate project init
**Cause:** Calling `aidp_init` or `POST /init` on an already-initialized project.
**Behavior:** Both flows handle deduplication:
- MCP init: `aidp_init()` in server.py checks if project exists in `aidp_projects` before creating (line 299-304)
- REST init: Each task's implementation checks for existing records before creating (e.g., `_run_agent_setup()` checks for active agents at line 580-587)

### 7. nas_path vs local_path confusion
- `nas_path`: The project path on the NAS server (used by MCP init for server-side operations)
- `local_path`: Stored in `ProjectMapping.local_path` — the user's local filesystem path
- Code-index creates the project structure on NAS; file scanning runs from the local machine