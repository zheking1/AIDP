# API Endpoint Index

Complete listing of every endpoint exposed by the AIDP Controller.

## Health

| Method | Path | Purpose | Auth | Input | Output |
|--------|------|---------|------|-------|--------|
| GET | `/health` | Service health check | None | -- | `{"status":"UP","service":"AIDP Controller","version":"0.1.0"}` |

## Metrics

| Method | Path | Purpose | Auth | Input | Output |
|--------|------|---------|------|-------|--------|
| GET | `/metrics` | Prometheus metrics | None | -- | Prometheus text format |

## WebSocket

| Path | Purpose | Auth |
|------|---------|------|
| `/ws/logs` | Real-time tool invocation broadcast | None (WebSocket accept) |

---

## Tool Registry (`/api/tools`)

| Method | Path | Purpose | Auth | Input | Output |
|--------|------|---------|------|-------|--------|
| POST | `/api/tools` | Register or update a tool | None | `{"name":"str","endpoint":"str","displayName?":"str","description?":"str","version?":"str"}` | Tool record with id, name, endpoint, status, capabilities |
| GET | `/api/tools` | List all tools (optional `?status=` filter) | None | Query: `status?` (str) | Array of tool records |
| GET | `/api/tools/health/all` | Health-check all registered tools | None | -- | Array of `{"tool":"name","status":"healthy\|unhealthy\|unreachable","durationMs":int}` |
| GET | `/api/tools/{tool_name}` | Get a single tool by name | None | Path: `tool_name` | Tool record |
| POST | `/api/tools/{tool_name}/health` | Health-check a single tool | None | Path: `tool_name` | `{"tool":"name","status":"...","durationMs":int}` |
| POST | `/api/tools/{tool_name}/sync` | Sync capabilities from tool's manifest | None | Path: `tool_name` | `{"tool":"name","capabilities":[...]}` |
| POST | `/api/tools/{tool_name}/disable` | Disable a tool | None | Path: `tool_name` | Tool record (status="disabled") |
| POST | `/api/tools/{tool_name}/enable` | Enable a tool | None | Path: `tool_name` | Tool record (status="registered") |
| DELETE | `/api/tools/{tool_name}` | Delete a tool from registry | None | Path: `tool_name` | `{"deleted":"name"}` |
| POST | `/api/tools/{tool_name}/invoke` | Invoke a tool capability | None | `{"capability":"str","arguments":{},"userId?":int}` | Tool invocation result JSON |
| GET | `/api/tools/invocations/history` | Get invocation history | None | Query: `tool_name?` (str), `limit?` (int, default 20) | Array of invocation records |
| GET | `/api/tools/dashboard/stats` | Dashboard statistics | None | -- | `{"total_tools":int,"healthy_tools":int,"today_calls":int,"recent_invocations":[...]}` |

---

## Authentication (`/api/auth`)

| Method | Path | Purpose | Auth | Input | Output |
|--------|------|---------|------|-------|--------|
| POST | `/api/auth/login` | API-based user login | None | `{"username":"str","password":"str","remember_me?":bool}` | `{"success":bool,"message":"str","user":{...}}` + sets `aidp_session` cookie |
| POST | `/api/auth/login/form` | Form-based login (web UI) | None | Form: `username`, `password`, `remember_me` | Redirect to `/` or `/login?error=...` |
| POST | `/api/auth/logout` | API-based logout | Session cookie | -- (reads `aidp_session` cookie) | `{"success":true,"message":"..."}` |
| POST | `/api/auth/logout/form` | Form-based logout (web UI) | Session cookie | -- | Redirect to `/login` |
| GET | `/api/auth/me` | Get current logged-in user | Session cookie | -- | `{"id":"str","username":"str","nickname":"str","email":"str","role":"str","avatar_url":"str","status":"str"}` |
| POST | `/api/auth/change-password` | Change password | Session cookie | `{"old_password":"str","new_password":"str"}` | `{"success":true,"message":"..."}` |
| PUT | `/api/auth/profile` | Update own profile | Session cookie | `{"email?":"str","nickname?":"str","role?":"str","status?":"str"}` | `{"success":true,"user":{...}}` |
| GET | `/api/auth/users` | List all users (admin) | Session cookie + admin | Query: `page?`(int,1), `size?`(int,20), `search?`(str) | `{"items":[...],"total":int,"page":int,"size":int,"pages":int}` |
| POST | `/api/auth/users` | Create user (admin) | Session cookie + admin | `{"username":"str","password":"str","email?":"str","nickname?":"str","role?":"str"}` | `{"success":true,"user":{...}}` |
| POST | `/api/auth/users/{user_id}/toggle` | Enable/disable user (admin) | Session cookie + admin | Path: `user_id` | `{"success":true,"message":"..."}` |
| DELETE | `/api/auth/users/{user_id}` | Delete user (super_admin) | Session cookie + super_admin | Path: `user_id` | `{"success":true,"message":"..."}` |
| PUT | `/api/auth/users/{user_id}` | Update a user (admin) | Session cookie + admin | `{"email?":"str","nickname?":"str","role?":"str","status?":"str"}` | `{"success":true,"user":{...}}` |
| GET | `/api/auth/api-keys` | List own API keys | Session cookie | -- | `{"items":[...]}` |
| POST | `/api/auth/api-keys` | Create API key | Session cookie | Query/Form: `label?`(str), `expires_days?`(int) | `{"success":true,"key":"str","key_id":"str","message":"..."}` |
| DELETE | `/api/auth/api-keys/{key_id}` | Revoke API key | Session cookie | Path: `key_id` | `{"success":true,"message":"..."}` |
| GET | `/api/auth/api-keys/{key_id}/reveal` | Reveal API key plaintext | Session cookie | Path: `key_id` | `{"success":true,"key":"str"}` |

---

## Projects (`/api/projects`) -- `routers/projects_new.py`

| Method | Path | Purpose | Auth | Input | Output |
|--------|------|---------|------|-------|--------|
| GET | `/api/projects` | List projects for current user | Session cookie | Query: `search?`(str), `skip?`(int,0), `limit?`(int,20) | `{"items":[...]}` (each with my_role, member_count) |
| POST | `/api/projects` | Create a new project | `project:create` | Query: `name`(str), `description?`(str), `visibility?`(str, "private"), `tech_stack?`(str, JSON array) | Project dict |
| GET | `/api/projects/{project_id}` | Get single project | Session cookie | Path: `project_id` | Project dict (with my_role, member_count) |
| PUT | `/api/projects/{project_id}` | Update project | `project:create` + write access | `{"name?":"str","description?":"str","visibility?":"str","tech_stack?":"str","status?":"str"}` | Project dict |
| DELETE | `/api/projects/{project_id}` | Soft-delete project (admin/owner) | `project:create` + admin | Path: `project_id` | `{"success":true}` |
| POST | `/api/projects/{project_id}/members` | Add member to project | `project:create` + write access | Query: `user_id`(str), `role?`(str, "viewer") | `{"success":true}` |
| GET | `/api/projects/{project_id}/members` | List project members | Session cookie + access | Path: `project_id` | `{"items":[...]}` |
| DELETE | `/api/projects/{project_id}/members/{member_user_id}` | Remove member | `project:create` + write access | Path: `project_id`, `member_user_id` | `{"success":true}` |
| GET | `/api/projects/{project_id}/init-status` | Get init tasks status | None | Path: `project_id` | `{"project_id":int,"tasks":[...],"overall":"str"}` |
| POST | `/api/projects/{project_id}/init` | Run init tasks | None | `{"tasks?":["str"]}` (empty=run all) | `{"project_id":int,"results":[...],"status":{...}}` |
| GET | `/api/projects/{project_id}/verify` | Verify init completion | None | Path: `project_id` | `{"project_id":int,"checks":[...],"mappings":[...],"summary":"str","all_passed":bool}` |

---

## Configs (`/api/projects/{project_id}/configs`) -- `api/configs.py`

| Method | Path | Purpose | Auth | Input | Output |
|--------|------|---------|------|-------|--------|
| GET | `/api/projects/{project_id}/configs/` | Get all configs for project | Session + view access | Path: `project_id` | `{"configs":[{id,env_type,config_key,config_value}]}` |
| POST | `/api/projects/{project_id}/configs/` | Set a config for project | Session + manage access | `{"env_type":"str","config_key":"str","config_value":"str"}` | `{id,project_id,env_type,config_key,config_value}` |
| GET | `/api/projects/{project_id}/configs/{env_type}` | Get config for specific env | Session + view access | Path: `project_id`, `env_type` | Config key-value dict |
| POST | `/api/projects/{project_id}/configs/{env_type}/resolve` | Agent auto-resolve configs | None | `{"keys":["str"]}` | Resolved config dict |

---

## NAS Storage (`/api/projects`) -- `api/nas_storage.py`

| Method | Path | Purpose | Auth | Input | Output |
|--------|------|---------|------|-------|--------|
| GET | `/api/projects/{project_id}/code-path` | Get project code path on NAS | Session + view access | Path: `project_id` | `{"path":"str","exists":bool}` |
| POST | `/api/projects/{project_id}/sync-code` | Sync code from Git to NAS | Session + manage access | `{"source":"str","branch?":"str"}` | `{"success":true,"path":"str"}` |
| GET | `/api/projects/{project_id}/files` | List project files | Session + view access | Query: `path?`(str) | `{"files":[...]}` |
| GET | `/api/projects/{project_id}/files/{file_path}` | Read file content | Session + view access | Path: `project_id`, `file_path` | `{"file_path":"str","content":"str"}` |
| POST | `/api/projects/{project_id}/files/{file_path}` | Write file content | Session + manage access | `{"content":"str"}` | `{"success":true,"file_path":"str"}` |

---

## Instructions (`/api/instructions`) -- 5-Stage Pipeline

| Method | Path | Purpose | Auth | Input | Output |
|--------|------|---------|------|-------|--------|
| POST | `/api/instructions` | Create/update agent instructions | None | `{"project_id?":int,"agent_type?":"str","role?":"str","constraints?":{},"rules?":[]}` | `{"success":true,"agent_type":"str"}` |
| GET | `/api/instructions` | Get instructions by project & agent type | None | Query: `project_id?`(int,0), `agent_type?`(str,"main") | Instruction record (id, role, constraints, rules) |
| GET | `/api/instructions/list` | List all instructions for a project | None | Query: `project_id?`(int,0) | Array of `{id, agent_type, role_preview, rules_count}` |
| PUT | `/api/instructions/{instruction_id}` | Update instruction | None | `{"role?":"str","constraints?":{},"rules?":[]}` | `{"success":true,"id":int}` |
| DELETE | `/api/instructions/{instruction_id}` | Delete instruction | None | Path: `instruction_id` | `{"success":true,"deleted":true,"id":int}` |
| POST | `/api/instructions/context` | Execute full 5-stage pipeline | None | `{"task":"str","project_id?":"str","user_id?":"str","session_id?":"str","hint_tags?":["str"]}` | `{"success":true,"trace_id":"str","data":{system_prompt,user_message,metadata,token_estimate,stage_timings,sources}}` |
| POST | `/api/instructions/subagent` | Generate subagent instructions | None | `{"task":"str","parent_trace_id":"str","project_id?":"str","specialization?":"str"}` | `{"success":true,"data":{role,constraints,task,specialization}}` |
| GET | `/api/instructions/stages/info` | Get pipeline stage info | None | -- | `{"success":true,"data":{stages:[...],version:"str"}}` |

---

## Models (`/api/models`)

| Method | Path | Purpose | Auth | Input | Output |
|--------|------|---------|------|-------|--------|
| GET | `/api/models` | List all models (optional `?task_type=` filter) | Session cookie | Query: `task_type?`(str) | `{"items":[...]}` |
| POST | `/api/models` | Create a model config | Session cookie + admin | `{"name":"str","provider":"str","model_name":"str","api_base?":"str","api_key?":"str","task_types?":["str"],"max_tokens?":int,"temperature?":float,"status?":"str","priority?":int}` | `{"success":true,"model":{...}}` |
| PUT | `/api/models/{model_id}` | Update a model config | Session cookie + admin | Partial model fields | `{"success":true,"model":{...}}` |
| DELETE | `/api/models/{model_id}` | Delete a model config | Session cookie + admin | Path: `model_id` | `{"success":true,"message":"..."}` |
| GET | `/api/models/for-task/{task_type}` | Get best model for task (public) | None | Path: `task_type` | `{"model":{...}}` |

---

## Settings (`/api/settings`)

| Method | Path | Purpose | Auth | Input | Output |
|--------|------|---------|------|-------|--------|
| GET | `/api/settings` | Get system settings | Session cookie | -- | `{"siteName":"str","siteDescription":"str","allowRegistration":bool,"requireApproval":bool}` |
| PUT | `/api/settings` | Update system settings | Session cookie + admin | `{"siteName?":"str","siteDescription?":"str","allowRegistration?":bool,"requireApproval?":bool}` | `{"success":true,"settings":{...}}` |

---

## Reviews (`/api/reviews`)

| Method | Path | Purpose | Auth | Input | Output |
|--------|------|---------|------|-------|--------|
| POST | `/api/reviews/` | Submit a review | Session cookie | `{"document_id":"str","action":"str","content?":"str"}` | `{id,document_id,user_id,action,content,status}` |
| GET | `/api/reviews/` | List reviews (admin) | Session cookie + admin | Query: `status?`(str) | `{"reviews":[{id,document_id,user_id,action,content,status,review_comment,reviewed_by,reviewed_at,created_at}]}` |
| POST | `/api/reviews/{review_id}/approve` | Approve a review (admin) | Session cookie + admin | `{"comment?":"str"}` | `{id,status,review_comment}` |
| POST | `/api/reviews/{review_id}/reject` | Reject a review (admin) | Session cookie + admin | `{"reason":"str"}` (required) | `{id,status,review_comment}` |

---

## Audit (`/api/audit`)

| Method | Path | Purpose | Auth | Input | Output |
|--------|------|---------|------|-------|--------|
| GET | `/api/audit/` | List recent 100 audit entries | Session cookie | -- | `{"audits":[{id,user_id,action,resource,details,created_at}]}` |
| GET | `/api/audit/logs` | List audit logs with filter | Session cookie | Query: `limit?`(int,50), `action?`(str) | `{"items":[{id,user_id,action,resource_type,resource_id,detail,created_at}]}` |
| POST | `/api/audit/` | Create an audit entry | Session cookie | `{"user_id?":"str","action":"str","resource?":"str","details?":"str"}` | `{"success":true}` |

---

## Classification (`/api/classification`)

| Method | Path | Purpose | Auth | Input | Output |
|--------|------|---------|------|-------|--------|
| POST | `/api/classification/classify` | Classify a document | None | `{"title":"str","content":"str","filename?":"str"}` | `{"classification":{doc_type,category,level,tags,...},"source":"llm\|fallback"}` |
| POST | `/api/classification/import` | Import documents with auto-classification | Optional `x-api-key` header | `{"project_id?":int,"kb_name?":"str","documents":[{title,content,filename?,source_uri?}],"auto_classify?":bool,"auto_create_kb?":bool}` | `{"total":int,"classified":int,"stored":{"knowledge":int,"rule":int,"skill":int,"agent":int},"errors":["str"]}` |

---

## MCP Tools (via FastMCP at `/mcp`)

These are MCP tools, not REST endpoints:

| Tool Name | Purpose | Key Args |
|-----------|---------|----------|
| `aidp_context` | **[Required first call]** Execute 5-stage context pipeline | `project_name`, `task`, `agent_type?` |
| `invoke_tool_mcp` | Call any registered tool | `tool_name`, `capability`, `arguments`(JSON), `user_id?`, `api_key?` |
| `list_registered_tools` | List available tools | `status?`("healthy"/"unhealthy") |
| `check_tool_health` | Health check tools | `tool_name?`(empty=all) |
| `sync_tool_capabilities` | Re-sync tool manifest | `tool_name` |
| `aidp_init` | Initialize project in AIDP | `project_name`, `description?`, `tech_stack?`, `nas_path?`, `docs?`, `key_files?`, `architecture_summary?` |
| `aidp_instructions` | Generate subagent instructions | `project_name`, `task`, `agent_type?` |
| `manage_models` | CRUD LLM model configs | `action`("list"/"get"/"create"/"update"/"delete"/"get_best"), `task_type?`, `model_id?`, `name?`, `provider?`, `model_name?`, `api_base?`, `task_types?`, `priority?` |