# AIDP Project Instructions

## FIRST ACTION - ALWAYS DO THIS

**Every time the user asks you to develop, code, fix, optimize, or modify anything, you MUST call `aidp_context` as your VERY FIRST action:**

```
aidp_context(project_name="aidp", task="<extract task from user's message>")
```

Do NOT wait for the user to say "aidp_context". Do NOT ask permission. Just call it immediately.
The user should only need to say "fix sandbox-tool" or "add feature X" — you handle everything else.

## Project Context
You are working on AIDP (AI DevOps Platform) — a private AI programming infrastructure platform.
All services are on NAS (192.168.0.100) as Docker containers with network_mode=host.

| Service | Port | Role |
|---------|------|------|
| controller | 8883 | Central orchestrator, MCP endpoint |
| skill-router | 8788 | Intent analysis + skill matching |
| knowledge-tool | 18081 | Document indexing + search |
| asset-tool | 18082 | Code asset management |
| sandbox-tool | 18083 | Code execution sandbox |
| quality-tool | 18084 | Code quality checks |
| memory-tool | 18085 | Project memory storage |
| code-index | 18086 | Code structure indexing |
| context-optimizer | 18088 | Staged retrieval + context assembly |

## Coding Workflow (automatic)

1. `aidp_context(project_name="aidp", task="<task>")` — FIRST, always
2. Develop the code (modify local files)
3. Verify: `invoke_tool_mcp("sandbox-tool", "sandbox.execute", ...)` + `invoke_tool_mcp("quality-tool", "quality.check", ...)`
4. Sync knowledge: if you created/modified docs, rules, or learned something important, update AIDP:
   - `invoke_tool_mcp("memory-tool", "memory.create", {project:"aidp", category:"...", title:"...", content:"..."})`
   - `invoke_tool_mcp("knowledge-tool", ...)` - re-index updated documents

## Important: Local files vs AIDP knowledge

Local files and AIDP knowledge are TWO SEPARATE layers:
- Modifying local files (code, docs, configs) does NOT automatically update AIDP tools
- You MUST explicitly call AIDP tools to sync knowledge after changes
- Treat AIDP as the "project brain" that augments development with context, not a replica of the filesystem

## Deployment
All changes must be deployed to NAS after coding:
1. `tar czf` source → `scp` to NAS → `docker build --no-cache` → `docker restart`
2. SSH: `ssh -i ~/.ssh/nas_temp root@192.168.0.100`

## Security
All passwords/keys in environment variables. Never hardcode. Use .env.example as reference.