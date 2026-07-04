# memory-tool

Project memory management for AIDP. Store, search, and retrieve project context.

## Features

- Create/search/update/delete memory entries
- Categories (decision, pattern, bug, note, etc.)
- Pinned entries
- Context packages for queries
- Tool protocol endpoints (`/tool/manifest`, `/tool/capabilities`, `/tool/invoke`)

## Environment

```bash
DATABASE_URL=postgresql+asyncpg://novel_os:CHANGE_ME@host.docker.internal:5432/novel_os
```

## Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 18085
```
