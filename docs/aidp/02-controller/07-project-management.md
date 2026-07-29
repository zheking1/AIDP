# Project Management

## Overview

The project management system (`apps/controller/app/routers/projects_new.py`, 772 lines) provides the unified project API for AIDP: CRUD, members, initialization tasks, verification, and cross-tool ID mappings.

## Data Model

All models in `apps/controller/app/models/project_new.py`:

| Table | Model | Line | Purpose |
|-------|-------|------|---------|
| `aidp_projects` | `Project` | 32-65 | Core project record (id, name, description, visibility, owner_id, status, tech_stack) |
| `aidp_project_members` | `ProjectMember` | 68-88 | Membership (project_id, user_id, role: admin/editor/viewer) |
| `aidp_project_settings` | `ProjectSettings` | 91-109 | Per-project config (instructions, config, integrations as JSON text) |
| `aidp_project_access_logs` | `ProjectAccessLog` | 112-134 | Audit log of project access |
| `aidp_project_mappings` | `ProjectMapping` | 137-156 | Cross-tool ID mapping (controller_project_id, tool_name, tool_project_id, local_path) |
| `aidp_project_init_tasks` | `ProjectInitTask` | 174-202 | Init task tracking (project_id, task_id, status, timestamps, error_msg, metadata_json) |

### `ProjectMapping` (line 137-156)

Links controller project IDs to IDs in external tools:

| Column | Type | Example |
|--------|------|---------|
| `controller_project_id` | Integer FK | 42 |
| `tool_name` | String(64) | `code-index`, `skillrouter`, `knowledge-tool` |
| `tool_project_id` | String(128) | `ci-abc123` |
| `local_path` | String(1024) | `/home/user/projects/myapp` |

---

## Project CRUD

### `GET /api/projects` — List Projects

**Code location:** `projects_new.py:77-111`, `list_projects()`

Access filter via `_project_filter()` (line 64-74): `owner_id == user_id` OR member-of OR `visibility == "public"`. Supports `search` (name LIKE), `skip`, `limit` (1-100, default 20). Returns `my_role` and `member_count` per project.

### `POST /api/projects` — Create Project

**Code location:** `projects_new.py:114-136`, `create_project()`

Requires `project:create` permission. Auto-creates `admin` member record for creator. Parameters: `name` (required), `description`, `visibility` (`private`/`internal`/`public`), `tech_stack` (JSON array string).

### `GET /api/projects/{project_id}` — Get Project

**Code location:** `projects_new.py:139-160`, `get_project()`

Access check via `_check_project_access()` (line 32-61):
- Owner → always has access
- Member → needs membership record
- Others → readable if `visibility == "public"` (read-only)
- Write access → requires `admin` or `editor` role

### `PUT /api/projects/{project_id}` — Update Project

**Code location:** `projects_new.py:163-176`, `update_project()`

Requires write access. Uses `ProjectUpdate` model: optional `name`, `description`, `visibility`, `tech_stack`, `status`.

### `DELETE /api/projects/{project_id}` — Delete Project

**Code location:** `projects_new.py:179-191`, `delete_project()`

Soft delete: sets `deleted_at = datetime.now()`. Requires admin role or project owner.

---

## Member Management

| Endpoint | Method | Line | Auth | Description |
|----------|--------|------|------|-------------|
| `/{project_id}/members` | POST | 194-214 | `project:create` + write access | Add member (user_id, role) |
| `/{project_id}/members` | GET | 217-228 | Project access | List all members |
| `/{project_id}/members/{member_user_id}` | DELETE | 231-250 | `project:create` + write access | Remove member |

---

## Init Status

### `GET /api/projects/{project_id}/init-status`

**Code location:** `projects_new.py:255-294`, `get_init_status()`

Auto-seeds missing task records as `"pending"`. Returns all 9 tasks + overall status.

**Overall status logic** (line 286-293):

| Overall | Condition |
|---------|-----------|
| `"completed"` | All tasks done (excluding `file_watcher`) |
| `"running"` | Any task has `running` status |
| `"failed"` | Any task has `failed` status |
| `"pending"` | Otherwise |

---

## Init Execute (9 Tasks)

### `POST /api/projects/{project_id}/init`

**Code location:** `projects_new.py:303-393`, `run_init()`

Request body `InitRequest` (line 299): `tasks: List[str]` — empty = run all pending. Each task: set to `"running"` → execute → mark `"completed"`/`"skipped"`/`"failed"`.

### The 9 Tasks

Defined at `apps/controller/app/models/project_new.py:159-169` (`INIT_TASKS`):

| # | task_id | Name | Phase | Depends On | Implementation |
|---|---------|------|-------|------------|----------------|
| 1 | `code_index` | 代码索引 | 1 | — | `_run_code_index()` (line 396) |
| 2 | `doc_import` | 文档导入 | 2 | code_index | `_run_doc_import()` (line 450) |
| 3 | `tech_analysis` | 技术栈分析 | 1 | — | `_run_local_setup("tech_scan")` (line 488) |
| 4 | `official_docs` | 官方文档导入 | 2 | tech_analysis | `_run_official_docs()` (line 499) |
| 5 | `file_watcher` | 文件监听安装 | 3 | — | `_run_local_setup("file_watcher")` (line 488) |
| 6 | `git_hook` | Git 钩子安装 | 3 | — | `_run_local_setup("git_hook")` (line 488) |
| 7 | `rules_extract` | 规则提取 | 2 | doc_import | `_run_rules_extract()` (line 542) |
| 8 | `agent_setup` | Agent 创建 | 2 | — | `_run_agent_setup()` (line 573) |
| 9 | `mcp_register` | MCP 注册检查 | 1 | — | `_run_mcp_register()` (line 477) |

### Task Detail

#### `_run_code_index()` (lines 396-447)
1. Looks up project in `aidp_projects`
2. `POST {controller}/api/tools/code-index/invoke` with capability `code.create_project`
3. Extracts returned `project_id` from code-index
4. Creates `ProjectMapping(tool_name="code-index", tool_project_id=<ci_project_id>)`
5. Returns code-index project ID; actual file scanning runs locally

#### `_run_doc_import()` (lines 450-474)
Creates project-level `KnowledgeBase` (name: `project-{id}-docs`) if none exists. Deduplication: checks `kb_level == "project"` before creating.

#### `_run_mcp_register()` (lines 477-485)
Health-checks required tools: `code-index`, `doc-index`, `skillrouter`. Returns warning if any are unhealthy.

#### `_run_local_setup()` (lines 488-496)
Returns shell command for user to run locally:
```
python scripts/aidp_init.py --project-id {id} --controller-url {url} --task {task}
```
Used by: `file_watcher`, `git_hook`, `tech_scan`.

#### `_run_official_docs()` (lines 499-539)
Reads project `tech_stack`, maps to known official doc URLs:

| Technology | Doc URL |
|------------|---------|
| Spring Boot | `https://docs.spring.io/spring-boot/docs/current/reference/htmlsingle/` |
| Vue.js | `https://vuejs.org/guide/introduction.html` |
| React | `https://react.dev/learn` |
| FastAPI | `https://fastapi.tiangolo.com/` |

#### `_run_rules_extract()` (lines 542-570)
Checks for existing rules; if none, queries `aidp_knowledge_documents` for `category == "code_style"` docs. Returns count for on-demand extraction.

#### `_run_agent_setup()` (lines 573-612)
Creates default project agent:
- Name: `"{project_name} Assistant"`
- Role: `"developer"`
- Instructions: `"You are an AI assistant for {project_name}. Help with code, docs, and architecture."`
- Scope: `"project"`

---

## Verify Flow

### `GET /api/projects/{project_id}/verify`

**Code location:** `projects_new.py:628-772`, `verify_init()`

Runs 7 verification checks defined in `VERIFY_CHECKS` (line 617-625):

| # | Check | Line | What It Checks | Fail Severity |
|---|-------|------|----------------|---------------|
| 1 | 代码索引 | 644-660 | `SELECT COUNT(*) FROM nodes WHERE project_id=?` in sqlite3 at `/app/data/code_index.db` | `error` if 0, `warn` if < 50 |
| 2 | 文档导入 | 662-677 | `COUNT(aidp_knowledge_documents)` for this project | `error` if 0 |
| 3 | 技术栈分析 | 679-687 | `project.tech_stack` is non-empty | `warn` if empty |
| 4 | 官方文档 | 689-705 | Framework-level `KnowledgeBase` count for project | `warn` if 0 |
| 5 | 规则提取 | 707-719 | `COUNT(Rule)` for project | `warn` if 0 |
| 6 | Agent 创建 | 721-736 | `COUNT(Agent)` for project (active) | `warn` if 0 |
| 7 | MCP 注册 | 738-752 | Health-check `code-index`, `doc-index`, `skillrouter`, `memory-tool`, `knowledge-tool` | `error` if any missing |

**Response includes** `mappings` (all `ProjectMapping` records for the project) and summary:
```json
{
  "project_id": 42,
  "project_name": "my-app",
  "owner_id": "user-1",
  "checks": [
    { "task_id": "code_index", "name": "代码索引", "passed": true, "detail": "code-index 中 152 个节点", "severity": "ok" },
    ...
  ],
  "mappings": [
    { "id": 1, "controller_project_id": 42, "tool_name": "code-index", "tool_project_id": "ci-99" }
  ],
  "summary": "7/7 检查通过",
  "all_passed": true
}
```

---

## MCP Init: `aidp_init()` Tool

**Code location:** `apps/controller/app/mcp/server.py:250-327`

The `aidp_init` MCP tool performs a full project init through a different path — delegating to `init_project()` in `app/services/project_init_service.py` (356 lines, 9 steps):

| Step | What Happens | Code Location |
|------|-------------|---------------|
| 1 | Create `aidp_projects` record | `project_init_service.py:84-100` |
| 2 | Import via `project-importer` (if nas_path) | `project_init_service.py:103-113` |
| 3 | Code index via `code-index` tool | `project_init_service.py:116-145` |
| 4 | Upload key files to code-index | `project_init_service.py:148-168` |
| 5 | Store docs in `knowledge-tool` | `project_init_service.py:171-192` |
| 6 | Create architecture memories in `memory-tool` | `project_init_service.py:194-234` |
| 7 | Register key files in `asset-tool` | `project_init_service.py:236-257` |
| 8 | Sync tool capabilities | `project_init_service.py:259-269` |
| 9 | Return summary | `project_init_service.py:271-283` |