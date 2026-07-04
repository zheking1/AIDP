# error-tool AI 实施包

## 1. 目标交付

实现报错知识库工具，支持记录错误、归一化错误、检索相似错误、绑定解决方案。

## 2. 推荐模块结构

```text
error-tool/
  src/
    server.ts
    api/
      tool-protocol.routes.ts
      health.routes.ts
      error-case.routes.ts
      error-search.routes.ts
    services/
      error-case.service.ts
      error-normalize.service.ts
      error-search.service.ts
      solution.service.ts
      asset-tool.client.ts
    repository/
      error-case.repository.ts
      error-embedding.repository.ts
```

## 3. 数据库迁移

必须创建：

- `error_case`
- `error_embedding`
- `error_solution_link`

## 4. API

- `POST /api/errors`
- `POST /api/errors/search`
- `POST /api/errors/{id}/solution`
- `POST /api/errors/{id}/resolve`
- `POST /api/errors/{id}/export-pattern`

## 5. 核心实现

### ErrorNormalizeService

必须识别：

- TypeScript compilation failure。
- Python exception。
- Node.js runtime stacktrace。
- test failure。

归一化输出：

```json
{
  "error_type": "typescript_compile",
  "main_message": "TS2339 Property does not exist",
  "file": "src/services/order-service.ts",
  "line": 42,
  "root_cause": "field renamed but caller not updated"
}
```

### ErrorSearchService

必须支持：

- 关键词检索。
- 向量检索。
- error_type 过滤。
- project_id 隔离。

## 6. 测试

- TypeScript 错误归一化测试。
- stacktrace root cause 提取测试。
- 相似错误检索测试。
- export_pattern 调用 asset-tool mock 测试。

## 7. Definition of Done

- 可独立启动。
- 可被 controller 安装。
- 可记录错误。
- 可检索相似错误。
- 可绑定解决方案。
- 可导出 pattern 到 asset-tool。
