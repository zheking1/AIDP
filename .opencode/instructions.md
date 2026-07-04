# AIDP Project Instructions

## Project Context
You are working on the AIDP (AI DevOps Platform) project.
AIDP is a private AI programming infrastructure platform with Controller + N optional tools.

## Key Architecture
- Controller (port 8883): central orchestrator, exposes MCP endpoint at /mcp/
- SkillRouter (8788): intent analysis + skill matching
- knowledge-tool (18081): document indexing and search
- asset-tool (18082): code asset management
- sandbox-tool (18083): code execution sandbox
- quality-tool (18084): code quality checks  
- memory-tool (18085): project memory storage
- code-index (18086): code structure indexing
- context-optimizer (18088): staged retrieval + context assembly
- All deployed on NAS (192.168.0.100) as Docker containers with network_mode=host

## Mandatory Workflow
1. BEFORE coding: call `aidp_context(project_name="aidp", task="<task>")`
2. DURING coding: use sandbox-tool and quality-tool to verify
3. AFTER coding: store learnings in memory-tool via `memory.create`

## Tool Protocol
Every tool implements: GET /health, GET /tool/manifest, GET /tool/capabilities, POST /tool/invoke
Standard invoke format: {trace_id, capability, context, input} → {trace_id, tool, capability, success, output, error, elapsed_ms}

## Deployment
All services on NAS (192.168.0.100). Deploy via: package source → SCP to NAS → docker build --no-cache → docker restart
Use deploy-nas.ps1 or manual: ssh root@192.168.0.100 (key: ~/.ssh/nas_temp)

## Security
All passwords/keys in environment variables. Never hardcode credentials.
Use .env file for local development (copy from .env.example).