# aidp-controller

AIDP tool controller. Manages tool registration, health checks, capability sync, and invocation.

## Features

- Tool registration and discovery
- Health monitoring (per-tool and bulk)
- Capability sync from tool manifests
- Tool invocation with audit trail
- MCP Streamable-HTTP endpoint
- Tool protocol endpoints (`/tool/manifest`, `/tool/capabilities`, `/tool/invoke`)

## Environment

```bash
DATABASE_URL=postgresql+asyncpg://novel_os:CHANGE_ME@host.docker.internal:5432/novel_os
```

## Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8883
```

## API

- `POST /api/tools` - Register tool
- `GET /api/tools` - List tools
- `GET /api/tools/{name}` - Get tool
- `POST /api/tools/{name}/health` - Health check
- `POST /api/tools/{name}/sync` - Sync capabilities
- `POST /api/tools/{name}/invoke` - Invoke tool
- `GET /api/tools/invocations/history` - Invocation history

## MCP

Endpoint: `http://host:8883/mcp/`

Tools:
- `invoke_tool_mcp` - Invoke a tool
- `list_registered_tools` - List tools
- `check_tool_health` - Check health
- `sync_tool_capabilities` - Sync capabilities
