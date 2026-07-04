# git-tool 数据模型

## 1. git_repository

字段：

- `id`
- `workspace_id`
- `project_id`
- `name`
- `repo_path`
- `remote_url`
- `default_branch`
- `write_enabled`
- `created_at`
- `updated_at`

## 2. git_sync_snapshot

保存 status/diff 查询快照：

- `id`
- `repo_id`
- `head_sha`
- `branch`
- `dirty`
- `status_json`
- `created_at`

## 3. git_commit_cache

可选缓存 commit 元数据：

- `repo_id`
- `sha`
- `author`
- `message`
- `committed_at`
- `files_changed`
- `stats`

## 4. 配置

```yaml
server:
  port: 18089

git:
  allowWrite: false
  commandTimeoutMs: 30000
  maxDiffBytes: 200000
  maxPatchBytesPerFile: 20000
  allowedRepoRoots:
    - /workspace
```

## 5. 迁移

`V1__git_repository.sql`、`V2__git_sync_snapshot.sql`、`V3__git_commit_cache.sql`。
