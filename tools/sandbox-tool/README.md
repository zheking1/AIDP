# sandbox-tool

Code execution sandbox for AIDP. Supports Python and Bash execution with timeout and output capture.

## Features

- Execute Python and Bash code
- Timeout protection (30s default)
- Output capture (stdout/stderr)
- Execution history tracking
- Tool protocol endpoints (`/tool/manifest`, `/tool/capabilities`, `/tool/invoke`)

## Environment

```bash
DATABASE_URL=postgresql+asyncpg://novel_os:CHANGE_ME@host.docker.internal:5432/novel_os
EXECUTION_TIMEOUT=30
EXECUTION_MAX_OUTPUT=10240
```

## Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 18083
```
