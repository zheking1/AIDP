# git-tool 模块设计

| 模块 | 职责 |
|---|---|
| `GitInvokeController` | capability 路由 |
| `RepositoryRegistryService` | 仓库登记和 project 绑定 |
| `RepoPathGuard` | repo 和文件路径安全校验 |
| `GitCommandExecutor` | 白名单命令执行、timeout、输出截断 |
| `StatusService` | 解析 porcelain status |
| `DiffService` | diff 获取、解析、摘要 |
| `HistoryService` | log/show/file history |
| `CommitService` | 可选 create commit |

## Diff 摘要结构

每个文件返回：

- `path`
- `change_type`
- `additions`
- `deletions`
- `is_binary`
- `patch_excerpt`
- `truncated`

## 状态分类

- `staged`
- `unstaged`
- `untracked`
- `conflicted`

## 错误处理

| 场景 | 错误码 |
|---|---|
| repo 未登记 | `NOT_FOUND` |
| 路径越界 | `FORBIDDEN` |
| git 命令超时 | `TIMEOUT` |
| 写操作未启用 | `FORBIDDEN` |
| 工作区无变更提交 | `VALIDATION_ERROR` |
