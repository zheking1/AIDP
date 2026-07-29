# Skill Router — REST API + Tool API

## Endpoint Summary

| Method | Path                           | Auth    | Description                              |
|--------|--------------------------------|---------|------------------------------------------|
| GET    | `/health`                      | None    | Health check                             |
| GET    | `/`                            | None    | Redirect to `/login`                     |
| GET    | `/tool/manifest`               | None    | Tool manifest (metadata + capabilities)  |
| GET    | `/tool/capabilities`           | None    | All 14 capabilities with input schemas   |
| POST   | `/tool/invoke`                 | API key | Unified capability invocation            |
| GET    | `/api/skills`                  | Session | List all active skills                   |
| GET    | `/api/skills/search`           | None    | Search skills (name ILIKE + tag filter)  |
| POST   | `/api/skills/create`           | Session | Create skill with files                  |
| GET    | `/api/skills/{id}`             | None    | Get skill detail with files              |
| GET    | `/api/skills/{id}/files`       | None    | List skill files                         |
| POST   | `/api/skills/{id}/files`       | Session | Replace all files for a skill            |
| POST   | `/api/skills/{id}/exec-config` | Session | Save execution config                    |
| GET    | `/api/skills/{id}/package`     | None    | Download skill as tar.gz                 |
| POST   | `/api/skills/upload`           | Session | Upload skill package (tar.gz)            |
| POST   | `/api/skills/import/preview`   | Session | Preview skill from GitHub/ClawHub URL    |
| POST   | `/api/skills/import/search`    | Session | Search GitHub for skills                 |
| POST   | `/api/skills/import`           | Session | Import skill from GitHub URL             |
| POST   | `/api/skills/{id}/move`        | Session | Move skill to a group                    |
| GET    | `/api/skill-groups`            | Session | List skill groups with count             |
| POST   | `/api/skill-groups`            | Session | Create skill group                       |
| PATCH  | `/api/skill-groups/{id}`       | Session | Update skill group                       |
| DELETE | `/api/skill-groups/{id}`       | Session | Delete skill group                       |
| GET    | `/api/rule-groups`             | Session | List rule groups with count              |
| POST   | `/api/rule-groups`             | Session | Create rule group                        |
| PATCH  | `/api/rule-groups/{id}`        | Session | Update rule group                        |
| DELETE | `/api/rule-groups/{id}`        | Session | Delete rule group                        |
| POST   | `/api/rules/{id}/move`         | Session | Move rule to a group                     |
| GET    | `/api/cli/install.sh`          | None    | CLI installer script (bash)              |
| GET    | `/api/cli/srcli.py`            | None    | CLI client script (python)               |

## `/tool/manifest` Response

```json
{
  "apiVersion": "aidp.dev/v1",
  "kind": "Tool",
  "metadata": {
    "name": "skillrouter",
    "displayName": "Skill Router",
    "version": "0.1.0",
    "description": "Core routing engine for AI agent task resolution."
  },
  "runtime": {
    "modes": ["standalone", "managed"],
    "docker": {
      "image": "aidp/skillrouter:0.1.0",
      "port": 8788
    }
  },
  "capabilities": [
    {
      "name": "resolve_task",
      "description": "Resolve a task to matching skills.",
      "endpoint": "MCP resolve_task",
      "timeoutMs": 10000,
      "permission": "skill:resolve"
    }
    // ... 14 capabilities
  ]
}
```

## `/tool/invoke` — Unified Capability Invocation

### Request Schema

```python
class ToolInvokeRequest(BaseModel):
    trace_id: Optional[str] = None
    capability: str               # Required: one of 14 capability names
    context: dict = {}            # Optional: extra context (e.g., api_key, instructions)
    input: dict = {}              # Required: capability-specific parameters
```

### Response Schema

```python
class ToolInvokeResponse(BaseModel):
    trace_id: str
    tool: str                     # Always "skillrouter"
    capability: str               # Echo of requested capability
    success: bool
    output: Any = None            # Capability-specific output on success
    error: Optional[dict] = None  # {"code": "...", "message": "..."} on failure
    elapsed_ms: int = 0
```

### All 14 Capabilities with Input Schemas

#### 1. `resolve_task`

```json
// Input
{
  "task": "string (required)",
  "mode": "string (optional, default: auto, values: auto|llm_only|embedding_only|tag_only)",
  "hint_tags": ["string"] (optional),
  "top_k": "integer (optional, default: 5, range: 2-6)",
  "role": "string (optional, for permission filtering)",
  "session_id": "string (optional)",
  "api_key": "string (optional)"
}
// Output: see resolve_skills response (intent_analysis + skills + rules + meta)
```

#### 2. `skill_register`

```json
// Input
{
  "name": "string (required)",
  "content": "string (required)",
  "tags": ["string"] (optional, auto-generated if auto_classify=true),
  "description": "string (optional)",
  "group_name": "string (optional, auto-created if not exists)",
  "auto_classify": "boolean (optional, default: true)",
  "api_key": "string (optional)"
}
// Output: {"id": "uuid", "name": "skill name", "tags": [...]}
```

Also triggers embedding generation on registration (name + description + content[:500]).

#### 3. `skill_update`

```json
// Input
{
  "id": "string (required)",
  "name": "string (optional)",
  "description": "string (optional)",
  "content": "string (optional)",
  "tags": "string (optional, NOT array — comma-separated)",
  "api_key": "string (optional)"
}
// Output: result from skill_service.update_skill()
```

Note: In the REST API (`/tool/invoke`), `tags` is passed as a string string (original schema) and stored as-is. In MCP tool `skill_update`, tags is comma-separated → split to list.

#### 4. `skill_delete`

```json
// Input
{
  "id": "string (required)",
  "api_key": "string (optional)"
}
// Output: result from skill_service.delete_skill() — true/false
```

#### 5. `skill_get`

```json
// Input
{
  "id": "string (required)",
  "api_key": "string (optional)"
}
// Output: {id, name, description, content, tags, scope, is_active, review_status, has_embedding}
```

#### 6. `skill_run`

```json
// Input
{
  "task": "string (required)",
  "mode": "string (optional, default: auto)",
  "top_k": "integer (optional, default: 5)",
  "api_key": "string (optional)"
}
// Output: resolve_task() result with instructions
```

#### 7. `skill_list`

```json
// Input
{
  "q": "string (optional, ILIKE search on name)",
  "tag": "string (optional, single tag filter)",
  "limit": "integer (optional, default: 50)",
  "offset": "integer (optional, default: 0)",
  "api_key": "string (optional)"
}
// Output: [{id, name, tags, ...}] for user's active skills
```

#### 8. `rule_create`

```json
// Input
{
  "name": "string (required)",
  "content": "string (required)",
  "tags": ["string"] (optional, auto-generated if auto_classify=true),
  "priority": "integer (optional, default: 0)",
  "api_key": "string (optional)"
}
// Output: {id, name, tags, priority}
```

#### 9. `rule_list`

```json
// Input
{
  "limit": "integer (optional, default: 50)",
  "offset": "integer (optional, default: 0)",
  "api_key": "string (optional)"
}
// Output: [{id, name}] for user's rules
```

#### 10. `model_add`

```json
// Input
{
  "name": "string (required)",
  "endpoint": "string (required)",
  "api_key": "string (required, the LLM provider's API key)",
  "model_name": "string (required)",
  "mcp_api_key": "string (optional, SkillRouter API key)"
}
// Output: result from model_service.add_model()
```

#### 11. `model_list`

```json
// Input
{
  "role": "string (optional, filter by LLM role)",
  "mcp_api_key": "string (optional)"
}
// Output: [{id, name, model_name, role, is_healthy, is_default}]
```

#### 12. `cache_flush`

```json
// Input
{
  "key_hash": "string (optional, specific cache key to delete)",
  "api_key": "string (optional)"
}
// Output: calls delete_cache(key_hash) — flushes by key or clears all
```

#### 13. `evolution_submit`

```json
// Input
{
  "resource_type": "string (required, 'skill' or 'rule')",
  "resource_id": "string (required, UUID)",
  "change_type": "string (required)",
  "diff_summary": "string (required)",
  "api_key": "string (optional)"
}
// Output: {evolution_id, old_version, new_version, diff_summary, status}
```

#### 14. `evolution_rollback`

```json
// Input
{
  "evolution_id": "string (required, UUID of the evolution to rollback)",
  "trigger_reason": "string (required)",
  "api_key": "string (optional)"
}
// Output: {evolution_id, status: "rolled_back"}
```

### Bonus: `analyze_intent`

```json
// Input
{
  "task": "string (required)",
  "instructions": "object (optional, {role, constraints, rules})"
}
// Output: {intent, entities, required_tools, search_queries, relevant_rules, budget_hints}
```

This is Stage 1 of the AIDP context pipeline — generates a retrieval plan before actual tool invocation. Uses LLM enhancement when available, falls back to rule-based detection.

## Auth

- **Web endpoints** (`/login`, `/api/skills/create`, etc.): Session-based via `SessionMiddleware`. Session user stored in `request.session["user"]`.
- **Tool endpoints** (`/tool/invoke`): API key via `req.input["api_key"]` or `req.context["api_key"]`. Key is SHA-256 hashed and matched against `api_keys` table.
- **Public fallback**: `resolve_task` and `analyze_intent` capabilities fall back to admin user if no API key is provided.