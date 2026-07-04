# git-tool AI 实施包

## 1. 目标交付

实现 Git 工具，支持登记仓库、同步提交、分析 diff、检索历史提交并导出历史方案。

## 2. 推荐模块结构

```text
git-tool/
  src/
    server.ts
    api/
      tool-protocol.routes.ts
      health.routes.ts
      git-repo.routes.ts
      git-commit.routes.ts
    services/
      git-repository.service.ts
      git-sync.service.ts
      commit-index.service.ts
      diff-summary.service.ts
      git-search.service.ts
      asset-tool.client.ts
    repository/
      git-repository.repository.ts
      git-commit-record.repository.ts
```

## 3. 数据库迁移

必须创建：

- `git_repository`
- `git_commit_record`
- `git_changed_file`

## 4. API

- `POST /api/git/repos`
- `POST /api/git/repos/{id}/sync`
- `POST /api/git/commits/search`
- `GET /api/git/commits/{hash}`
- `POST /api/git/commits/{hash}/export-pattern`

## 5. 核心实现

### GitSyncService

必须支持：

- 本地仓库扫描。
- 远程仓库 shallow clone。
- 只读同步。
- last_sync_at。

### DiffSummaryService

必须输出：

- changed_files。
- added_lines。
- deleted_lines。
- commit_message。
- summary。

## 6. 安全要求

- token 使用 secret reference。
- 不明文保存 token。
- 不执行仓库脚本。
- 不自动 push。
- 限制 clone 深度和仓库大小。

## 7. 测试

- 本地仓库登记测试。
- commit 解析测试。
- diff summary 测试。
- commit search 测试。

## 8. Definition of Done

- 可独立启动。
- 可被 controller 安装。
- 可登记本地仓库。
- 可同步提交。
- 可检索提交。
- 可导出 pattern。
