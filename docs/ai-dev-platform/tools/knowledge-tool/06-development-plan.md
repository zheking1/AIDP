# knowledge-tool 开发计划

## 1. 总体策略

`knowledge-tool` 是第一批 P0 工具，开发时要同时满足两个目标：

- 做出可运行的知识库 MVP。
- 形成后续工具可复用的工具协议实现样板。

因此开发顺序必须先打通工具协议和基础骨架，再实现文档业务。

## 2. 里程碑

| 里程碑 | 目标 | 交付物 |
|---|---|---|
| M0 | 工程骨架 | Python + FastAPI 项目、配置、健康检查、统一响应 |
| M1 | 工具协议 | `tool.yaml`、`/tool/manifest`、`/tool/capabilities`、`/tool/invoke` |
| M2 | 文档元数据 | 文档表、创建、查询、删除、上传 |
| M3 | 解析切片 | Markdown/TXT/source parser、chunking service |
| M4 | 索引任务 | index job、状态机、批量写 chunk |
| M5 | 检索能力 | keyword/vector/hybrid search、citation |
| M6 | controller 联调 | managed 安装、capability 映射、trace 和权限 |
| M7 | 测试验收 | 单元、集成、端到端、性能基线 |

## 3. M0 工程骨架

### 3.1 开发任务

- 创建工具项目目录。
- 配置 Python 3.11+、FastAPI、uvicorn。
- 配置 SQL migration 工具，优先 Alembic 或 SQL 脚本。
- 配置 OpenAPI。
- 增加统一异常处理。
- 增加统一响应 DTO。
- 增加 `TraceContext` filter。
- 增加配置类。

### 3.2 验收

- `GET /health` 返回 UP。
- 应用无数据库时能给出清晰依赖错误。
- 单元测试可运行。
- 日志包含 `trace_id`。

## 4. M1 工具协议

### 4.1 开发任务

- 编写 `tool.yaml`。
- 编写 `config.example.yaml`。
- 实现 manifest loader。
- 实现 capability registry。
- 实现 `/tool/manifest`。
- 实现 `/tool/capabilities`。
- 实现 `/tool/invoke` 路由。
- 定义 capability input/output DTO。

### 4.2 `/tool/invoke` 要求

必须能分发：

- `document.create`
- `document.index`
- `document.delete`
- `document.get`
- `knowledge.search`
- `knowledge.get_chunk`

未实现 capability 返回：

```json
{
  "success": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "capability not found"
  }
}
```

### 4.3 验收

- controller 可读取 manifest。
- capability schema 可被解析。
- unknown capability 返回结构化错误。

## 5. M2 文档元数据与文件接入

### 5.1 开发任务

- 创建 `kt_document` 表。
- 实现 `DocumentRepository`。
- 实现 `DocumentService.createDocument`。
- 实现 `DocumentService.getDocument`。
- 实现 `DocumentService.listDocuments`。
- 实现 `DocumentService.deleteDocument`。
- 实现本地文件存储。
- 实现 multipart 上传。
- 实现 checksum。

### 5.2 边界处理

- 文件过大返回 `VALIDATION_ERROR`。
- 不支持扩展名返回 `UNSUPPORTED_DOCUMENT_TYPE`。
- 文件路径越权返回 `FORBIDDEN`。
- 重复 checksum 不阻止创建，但可提示 duplicate。

### 5.3 验收

- 可创建 Markdown 文档。
- 可上传 TXT 文件。
- 可列表查询。
- 删除后列表不可见。

## 6. M3 解析与切片

### 6.1 开发任务

- 实现 `DocumentParser` 接口。
- 实现 `MarkdownParser`。
- 实现 `PlainTextParser`。
- 实现 `SourceTextParser`。
- 实现 `ParserRegistry`。
- 实现 `ChunkingService`。
- 实现 token 估算器。
- 实现 content hash。

### 6.2 Markdown 切片要求

- 按标题层级保留 `heading_path`。
- 小节过长时继续拆分。
- 代码块不要被随意截断，无法保证时至少保留完整行。

### 6.3 TXT 切片要求

- 空行分段。
- 段落过长时按句子或行拆分。
- 保留段落序号。

### 6.4 Source 切片要求

MVP 可先使用行级策略：

- 优先按空行和函数声明附近切片。
- 保留 `source_start_line` 和 `source_end_line`。
- 后续由 tree-sitter 增强。

### 6.5 验收

- Markdown 标题路径正确。
- overlap 生效。
- chunk hash 稳定。
- 空文档不生成 chunk，并返回解析错误。

## 7. M4 索引任务

### 7.1 开发任务

- 创建 `kt_document_index_job` 表。
- 创建 `kt_document_chunk` 表。
- 实现 `IndexingService.createIndexJob`。
- 实现 `IndexingService.runIndexJob`。
- 实现任务状态机。
- 实现同文档并发锁。
- 实现 mock embedding。
- 实现批量写入 chunk。

### 7.2 同步与异步

MVP 可先同步执行，但 API 返回仍使用 job 模型。推荐：

- `sync=true` 开发调试使用。
- 默认创建 job 后后台执行。

### 7.3 验收

- 文档索引成功后 `index_status=indexed`。
- 失败后记录 `error_code` 和 `error_message`。
- 重复索引不会产生重复 chunk。

## 8. M5 检索能力

### 8.1 开发任务

- 实现 keyword search。
- 实现 mock vector search 或 PGVector search。
- 实现 hybrid score merge。
- 实现权限过滤 SQL。
- 实现 `CitationService`。
- 实现 `knowledge.search`。
- 实现 `knowledge.get_chunk`。

### 8.2 MVP 检索优先级

如果 PGVector 可用：

```text
metadata filter -> keyword search -> vector search -> merge
```

如果 PGVector 不可用：

```text
metadata filter -> keyword search -> degraded response
```

### 8.3 验收

- 查询能命中已索引文档。
- 返回 citation。
- 项目隔离生效。
- top_k 上限生效。

## 9. M6 controller 联调

### 9.1 开发任务

- 使用 controller 安装本工具。
- controller 读取 `/tool/manifest`。
- controller 注册 `knowledge.search`。
- controller 调用 `/tool/invoke`。
- 验证 trace_id 贯穿。
- 验证权限失败路径。

### 9.2 验收

- controller 管理后台能看到工具 UP。
- MCP Skill 能调用 `knowledge.search`。
- 调用审计中有 trace、tool、capability、elapsed_ms。

## 10. M7 测试与发布

### 10.1 开发任务

- 补齐单元测试。
- 补齐 repository 集成测试。
- 补齐 API 测试。
- 编写 examples。
- 编写 Dockerfile。
- 生成 OpenAPI。
- 编写 README 快速启动。

### 10.2 发布物

```text
tool.yaml
openapi.yaml
config.example.yaml
Dockerfile
migrations/
src/
tests/
examples/
```

## 11. AI 编码任务拆分

建议给 AI 开发工具按以下任务执行：

1. 创建项目骨架和通用响应错误模型。
2. 实现工具协议接口。
3. 创建 Alembic/SQL 迁移和 repository。
4. 实现文档创建、查询、删除、上传。
5. 实现 parser registry 和 Markdown/TXT parser。
6. 实现 chunking service 和测试。
7. 实现 index job 和 mock embedding。
8. 实现 keyword search。
9. 实现 vector store 抽象和 PGVector/mock 实现。
10. 实现 hybrid search 和 citation。
11. 实现 `/tool/invoke` capability 映射。
12. 补齐 OpenAPI、examples、Dockerfile。
13. 进行 controller 联调。

## 12. 风险与控制

| 风险 | 影响 | 控制方式 |
|---|---|---|
| PDF/Word 解析复杂 | 拖慢 MVP | 放到增强阶段 |
| embedding provider 不稳定 | 索引失败 | mock provider 和重试机制 |
| PGVector 环境不统一 | 部署失败 | keyword 降级和 optional migration |
| chunk 质量差 | 检索效果差 | Markdown 标题优先，保留 heading_path |
| 权限漏查 | 数据泄露 | repository 查询必须带 scope |
| 大文件导致内存压力 | 服务不稳定 | 文件大小限制和流式读取 |

## 13. 开发完成定义

- 所有 P0 capability 可用。
- 所有 API 有 OpenAPI 描述。
- 所有表由 migration 创建。
- 单元测试、集成测试、端到端测试通过。
- standalone 和 managed 模式均可运行。
- 文档和示例足够新用户 10 分钟启动。
