# git-tool API 与 Capability

## 1. Capability

| capability | REST |
|---|---|
| `git.repo_status` | `GET /api/repos/{repo_id}/status` |
| `git.diff_summary` | `POST /api/repos/{repo_id}/diff-summary` |
| `git.commit_history` | `GET /api/repos/{repo_id}/commits` |
| `git.show_commit` | `GET /api/repos/{repo_id}/commits/{sha}` |
| `git.file_history` | `GET /api/repos/{repo_id}/files/history` |
| `git.create_commit` | `POST /api/repos/{repo_id}/commits` |

## 2. diff_summary 请求

```json
{
  "base": "HEAD",
  "target": "working_tree",
  "paths": ["src/services"],
  "max_patch_bytes": 20000
}
```

## 3. diff_summary 响应

```json
{
  "repo_id": "repo_01",
  "base": "HEAD",
  "files": [
    {
      "path": "src/services/order-service.ts",
      "change_type": "modified",
      "additions": 12,
      "deletions": 3,
      "patch_excerpt": "@@ ...",
      "truncated": false
    }
  ],
  "totals": {
    "files": 1,
    "additions": 12,
    "deletions": 3
  }
}
```

## 4. create_commit 请求

```json
{
  "message": "feat: add order approval API",
  "paths": ["src/routes/order"]
  "allow_empty": false
}
```

写操作关闭时返回 `FORBIDDEN`。

## 5. 错误码

`VALIDATION_ERROR`、`FORBIDDEN`、`NOT_FOUND`、`TIMEOUT`、`EXECUTION_FAILED`、`INTERNAL_ERROR`。
