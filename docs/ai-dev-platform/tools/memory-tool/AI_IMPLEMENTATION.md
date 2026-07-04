# memory-tool AI 实施包

## 1. 开发输入

必须阅读：

- `common/tool-contract.md`
- `common/engineering-standards.md`
- `tools/memory-tool/README.md`

## 2. 目标交付

实现项目记忆、会话摘要和上下文包工具。

## 3. 推荐模块结构

```text
memory-tool/
  src/
    server.ts
    api/
      tool-protocol.routes.ts
      health.routes.ts
      memory.routes.ts
      context-package.routes.ts
    services/
      memory.service.ts
      context-package.service.ts
      summary.service.ts
      token-estimate.service.ts
    repository/
      memory-item.repository.ts
```

## 4. 数据库迁移

必须创建：

- `memory_item`
- `session_summary`

## 5. API 开发任务

- `GET /health`
- `GET /tool/manifest`
- `GET /tool/capabilities`
- `POST /tool/invoke`
- `POST /api/memory/items`
- `POST /api/memory/search`
- `POST /api/memory/context-package`
- `POST /api/memory/session-summary`

## 6. 核心实现要求

### MemoryService

必须支持：

- global memory。
- workspace memory。
- project memory。
- session memory。
- importance。
- expires_at。
- status。

### ContextPackageService

必须按以下顺序组装：

1. 当前会话摘要。
2. 高重要度项目规范。
3. 最近业务决策。
4. 与 task 匹配的记忆。

必须支持 max_tokens。

## 7. 测试清单

单元测试：

- 重要度排序。
- 过期过滤。
- project_id 隔离。
- token 估算。

集成测试：

- 保存项目记忆。
- 保存会话摘要。
- 生成 context package。

## 8. Definition of Done

- 可独立启动。
- controller 可安装。
- context package 不跨项目。
- max_tokens 生效。
- 过期记忆不返回。
