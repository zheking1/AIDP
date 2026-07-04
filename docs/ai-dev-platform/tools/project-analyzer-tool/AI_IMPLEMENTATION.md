# project-analyzer-tool AI 实施包

## 1. 目标交付

实现项目结构分析工具，支持扫描源码、识别技术栈、提取依赖、接口和数据库脚本。

## 2. 推荐模块结构

```text
project-analyzer-tool/
  src/
    server.ts
    api/
      tool-protocol.routes.ts
      health.routes.ts
      project-scan.routes.ts
    services/
      project-scan.service.ts
      stack-detect.service.ts
      dependency-extract.service.ts
      api-extract.service.ts
      database-extract.service.ts
      project-summary.service.ts
    repository/
      project-scan.repository.ts
      project-symbol.repository.ts
```

## 3. 数据库迁移

必须创建：

- `project_scan`
- `project_symbol`
- `project_dependency`
- `project_api_endpoint`

## 4. API

- `POST /api/project-analyzer/scan`
- `GET /api/project-analyzer/scans/{id}`
- `GET /api/project-analyzer/scans/{id}/summary`
- `GET /api/project-analyzer/scans/{id}/apis`
- `GET /api/project-analyzer/scans/{id}/dependencies`

## 5. 核心实现

### StackDetectService

识别：

- TypeScript/Fastify。
- Node/TypeScript。
- Python。
- Node。
- Flutter。

### ApiExtractService

MVP 提取：

- `fastify.get`
- `fastify.post`
- `fastify.put`
- `fastify.delete`
- Fastify plugin route registration

### DependencyExtractService

MVP 解析：

- `package.json`
- `pnpm-lock.yaml`
- `pyproject.toml`

## 6. 测试

- TypeScript/Fastify 项目识别测试。
- Node/Python 依赖提取测试。
- Fastify 路由提取测试。
- SQL migration 扫描测试。

## 7. Definition of Done

- 可独立启动。
- 可被 controller 安装。
- 可扫描示例 TypeScript/Fastify 项目。
- 可输出接口列表。
- 可输出依赖列表。
- 可生成项目摘要。
