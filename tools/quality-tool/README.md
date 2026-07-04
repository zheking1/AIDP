# quality-tool

Code quality checks for AIDP. Linting and security scanning.

## Features

- **Lint**: Line length, trailing whitespace, missing newline
- **Security**: Hardcoded secrets, SQL injection, dangerous functions
- Execution history tracking
- Tool protocol endpoints (`/tool/manifest`, `/tool/capabilities`, `/tool/invoke`)

## Environment

```bash
DATABASE_URL=postgresql+asyncpg://novel_os:jygame_postgres_01@host.docker.internal:5432/novel_os
LINT_MAX_LINE_LENGTH=120
```

## Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 18084
```
