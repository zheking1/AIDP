# project-analyzer-tool 数据模型

## 1. project_snapshot

字段：

- `id`
- `workspace_id`
- `project_id`
- `project_path`
- `scan_mode`
- `status`
- `git_commit`
- `summary_markdown`
- `stats`
- `created_by`
- `created_at`
- `finished_at`

## 2. project_file_index

字段：

- `id`
- `snapshot_id`
- `file_path`
- `language`
- `module_name`
- `size_bytes`
- `mtime`
- `content_hash`
- `status`
- `skip_reason`

索引：`snapshot_id + file_path`、`snapshot_id + language`。

## 3. project_symbol

字段：

- `id`
- `snapshot_id`
- `symbol_type`
- `name`
- `qualified_name`
- `file_path`
- `line_start`
- `line_end`
- `language`
- `module_name`
- `metadata`

索引：`snapshot_id + symbol_type + name`。

## 4. project_dependency

字段：

- `id`
- `snapshot_id`
- `source_module`
- `target`
- `dependency_type`
- `version`
- `scope`
- `metadata`

## 5. project_scan_event

记录扫描开始、跳过、解析错误、完成等事件。

## 6. 配置

```yaml
server:
  port: 18088

scan:
  maxFileBytes: 1048576
  maxFiles: 200000
  defaultExcludes:
    - "**/.git/**"
    - "**/build/**"
    - "**/node_modules/**"
    - "**/dist/**"
    - "**/coverage/**"
    - "**/.venv/**"
    - "**/__pycache__/**"
  enableTreeSitter: false
```

## 7. 迁移

`V1__project_snapshot.sql`、`V2__project_file_index.sql`、`V3__project_symbol.sql`、`V4__project_dependency.sql`、`V5__project_scan_event.sql`。
