# Tool Registry System

## Overview

The Tool Registry is the central mechanism by which AIDP discovers, manages, and invokes distributed tools. It consists of three components:

1. **Registry** (`services/tool_registry.py`) -- CRUD operations on the `tool_registry` database table
2. **Invoker** (`services/tool_invoker.py`) -- HTTP-based invocation of tool capabilities
3. **MCP Server** (`mcp/server.py`) -- Exposes tool operations via Model Context Protocol

## Data Model

Table: `tool_registry`

| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | Auto-increment |
| name | String(256) | Unique tool identifier (e.g. "sandbox-tool") |
| display_name | String(256) | Human-readable name |
| description | Text | Tool description |
| version | String(32) | Tool version |
| endpoint | String(512) | HTTP base URL of the tool |
| status | String(32) | registered/healthy/unhealthy/unreachable/disabled |
| last_health_check | DateTime | Last health check timestamp |
| capabilities | JSON | Array of capability objects synced from tool manifest |
| created_at | DateTime | |
| updated_at | DateTime | |

Table: `tool_invocation`
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | Auto-increment |
| tool_name | String(256) | Indexed |
| capability | String(256) | Capability name |
| arguments | JSON | Input arguments |
| result | JSON | Output result |
| status | String(32) | success/failure |
| duration_ms | Integer | |
| error | Text | |
| user_id | Integer | |
| created_at | DateTime | |

## Registration Flow

```
1. Tool starts up
      │
      ▼
2. Tool sends POST /api/tools with:
   {
     "name": "sandbox-tool",
     "endpoint": "http://localhost:18083",
     "displayName": "Code Sandbox",
     "description": "Execute code in sandboxed env",
     "version": "1.0.0"
   }
      │
      ▼
3. Controller calls register_tool():
   - Checks if tool with same name exists
   - If exists: updates endpoint/display_name/description/version
   - If new: inserts record with status="registered"
      │
      ▼
4. Returns tool record with id, name, status, capabilities
```

### Source: `services/tool_registry.py:15-49`

```python
async def register_tool(name, endpoint, display_name=None, description=None, version=None):
    # Upsert: updates existing or creates new
    # Sets status to "registered" for new tools
```

## Health Check Flow

```
1. Triggered via:
   - POST /api/tools/{name}/health (single)
   - GET /api/tools/health/all (all tools)
   - check_tool_health() MCP tool

2. For each tool:
   a. Look up endpoint from registry
   b. GET {endpoint}/health with 5s timeout
   c. If 200 -> status = "healthy"
      If non-200 -> status = "unhealthy"
      If exception -> status = "unreachable"
   d. Update last_health_check timestamp
   e. Persist to tool_registry table

3. Return status + response time
```

### Source: `services/tool_registry.py:69-106`

## Capability Sync Flow

```
1. Triggered via:
   - POST /api/tools/{name}/sync
   - sync_tool_capabilities() MCP tool

2. For the specified tool:
   a. GET {endpoint}/tool/capabilities (10s timeout)
   b. Parse response JSON, extract "capabilities" array
   c. Store in tool_registry.capabilities (JSON column)

3. Returns synced capabilities list
```

### Source: `services/tool_registry.py:118-141`

## Invocation Flow

```
1. Invocation via:
   - POST /api/tools/{tool_name}/invoke
   - invoke_tool_mcp() MCP tool
   
2. For MCP calls, session guard checks:
   - Is the tool exempt from context requirement?
     (aidp_context, aidp_init, list_registered_tools,
      check_tool_health, sync_tool_capabilities, aidp_instructions)
   - If not exempt: has aidp_context been called in this session?
   - If no: return CONTEXT_REQUIRED error

3. invoke_tool() in tool_invoker.py:
   a. Creates ToolInvoker (singleton pattern)
   b. Resolves tool endpoint:
      1. Check _endpoint_cache (in-memory dict)
      2. Query tool_registry table for status="healthy"
      3. Fallback to hardcoded env var endpoints
   c. POST {endpoint}/tool/invoke with payload:
      {
        "capability": "sandbox.execute",
        "input": {"code": "...", "language": "python"},
        "trace_id": "a1b2c3d4"
      }
   d. 30s timeout (httpx.AsyncClient default)
   e. On success: returns response JSON
   f. On timeout: returns error dict
   
4. Records invocation in tool_invocation table:
   - tool_name, capability, arguments, result, status
   - user_id, created_at

5. Broadcasts via WebSocket to /ws/logs clients
```

### Source: `services/tool_invoker.py:15-175`

## Tool Status Lifecycle

```
                    register_tool()
      NEW --------> registered -----------------------.
                        |                             |
                   health_check_tool()                |
                        |                             |
           .------ healthy ------ unhealthy           |
           |            |            |                |
      health_check  tool error   tool error           |
           |            |            |                |
           '-----> healthy <--- unreachable           |
                        |                             |
                   disable_tool()                enable_tool()
                        |                             |
                        v                             |
                     disabled ----------------------->renabled
                        |
                   delete_tool()
                        |
                        v
                     (removed)
```

## MCP Session Enforcement

Before `invoke_tool_mcp` runs any tool, the `MCPSessionManager` checks:

```python
# Exempt tools (can run without aidp_context first):
ALLOWED_WITHOUT_CONTEXT = {
    "aidp_context",
    "aidp_init",
    "list_registered_tools",
    "check_tool_health",
    "sync_tool_capabilities",
    "aidp_instructions",
}
```

When a session calls `aidp_context`, it gets marked as `context_loaded=True`. Subsequent `invoke_tool_mcp` calls check this flag. Sessions expire after 30 minutes of inactivity.

### Source: `mcp/session_manager.py:68-91`

## Invocation History

```python
async def get_invocation_history(tool_name=None, limit=20):
    # Queries tool_invocation table
    # Orders by created_at DESC
    # Filters by tool_name if provided
```

Available via:
- `GET /api/tools/invocations/history?tool_name=X&limit=20`
- Dashboard stats aggregates: total_tools, healthy_tools, today_calls, recent_invocations

## Tool Endpoint Fallback Map

When the tool_registry DB has no record, the invoker uses these env-based defaults (`tool_invoker.py:90-97`):

| Tool | Env Var | Default URL |
|------|---------|-------------|
| skill-router | SKILLROUTER_URL | http://localhost:8788 |
| knowledge-tool | KNOWLEDGE_URL | http://localhost:18081 |
| memory-tool | MEMORY_URL | http://localhost:18085 |
| asset-tool | ASSET_URL | http://localhost:18082 |
| sandbox-tool | SANDBOX_URL | http://localhost:18083 |
| quality-tool | QUALITY_URL | http://localhost:18084 |

## API Reference (Tool Registry)

| Endpoint | Method | Function |
|----------|--------|----------|
| /api/tools | POST | Register/update tool |
| /api/tools | GET | List tools (filter by ?status=) |
| /api/tools/{name} | GET | Get single tool |
| /api/tools/{name}/health | POST | Health check one tool |
| /api/tools/{name}/sync | POST | Sync capabilities |
| /api/tools/{name}/disable | POST | Disable tool |
| /api/tools/{name}/enable | POST | Enable tool |
| /api/tools/{name} | DELETE | Delete tool |
| /api/tools/{name}/invoke | POST | Invoke capability |
| /api/tools/health/all | GET | Health check all |
| /api/tools/invocations/history | GET | Invocation history |
| /api/tools/dashboard/stats | GET | Dashboard stats |