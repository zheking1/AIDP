# project-analyzer-tool API 与 Capability

## 1. Capability

| capability | 权限 | REST |
|---|---|---|
| `project.scan` | `project:read` | `POST /api/projects/scan` |
| `project.summary` | `project:read` | `GET /api/projects/{project_id}/summary` |
| `project.find_symbol` | `project:read` | `POST /api/projects/{project_id}/symbols/search` |
| `project.find_files` | `project:read` | `POST /api/projects/{project_id}/files/search` |
| `project.dependency_graph` | `project:read` | `GET /api/projects/{project_id}/dependency-graph` |
| `project.export_memory` | `memory:write` | `POST /api/projects/{project_id}/export-memory` |

## 2. project.scan

```json
{
  "project_path": "/workspace/erp",
  "mode": "incremental",
  "include": ["**/*"],
  "exclude": ["**/dist/**", "**/build/**", "**/coverage/**", "**/node_modules/**", "**/.venv/**"],
  "max_file_bytes": 1048576,
  "generate_summary": true
}
```

响应：

```json
{
  "scan_id": "scan_01",
  "snapshot_id": "snap_01",
  "status": "succeeded",
  "stats": {
    "files_total": 1200,
    "files_parsed": 830,
    "files_skipped": 370
  }
}
```

## 3. project.summary

返回：

```json
{
  "snapshot_id": "snap_01",
  "markdown": "## 技术栈\n- TypeScript\n- Fastify\n...",
  "summary": {
    "tech_stack": ["TypeScript", "Fastify", "PostgreSQL"],
    "build_commands": ["pnpm test"],
    "modules": []
  }
}
```

## 4. project.find_symbol

```json
{
  "query": "OrderController",
  "symbol_types": ["class", "route"],
  "top_k": 20
}
```

## 5. project.find_files

```json
{
  "query": "order approval",
  "languages": ["typescript", "sql"],
  "path_glob": "**/order/**",
  "top_k": 20
}
```

## 6. project.dependency_graph

返回模块节点、依赖边、外部依赖和冲突提示。

## 7. project.export_memory

将项目技术栈、构建命令、核心目录、关键约束写入 memory-tool，默认 `status=pending_review`。

## 8. 错误码

`VALIDATION_ERROR`、`FORBIDDEN`、`NOT_FOUND`、`DEPENDENCY_UNAVAILABLE`、`EXECUTION_FAILED`、`TIMEOUT`。
