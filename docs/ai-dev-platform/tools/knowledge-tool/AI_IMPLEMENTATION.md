# knowledge-tool AI 实施包

## 1. 开发输入

开发前必须阅读：

- `docs/ai-dev-platform/common/tool-contract.md`
- `docs/ai-dev-platform/common/engineering-standards.md`
- `docs/ai-dev-platform/tools/knowledge-tool/README.md`
- `docs/ai-dev-platform/tools/knowledge-tool/01-requirements.md`
- `docs/ai-dev-platform/tools/knowledge-tool/02-architecture.md`
- `docs/ai-dev-platform/tools/knowledge-tool/03-module-design.md`
- `docs/ai-dev-platform/tools/knowledge-tool/04-api-capabilities.md`
- `docs/ai-dev-platform/tools/knowledge-tool/05-data-model.md`
- `docs/ai-dev-platform/tools/knowledge-tool/06-development-plan.md`
- `docs/ai-dev-platform/tools/knowledge-tool/07-testing-acceptance.md`

## 2. 目标交付

实现一个可独立运行、可被 controller 安装的知识库工具。

必须交付：

```text
tool.yaml
openapi.yaml
config.example.yaml
src/
tests/
examples/
```

## 3. 推荐模块结构

```text
knowledge-tool/
  src/aidp_knowledge/
    main.py
    api/
      tool_protocol.py
      health.py
      documents.py
      search.py
    services/
      document_service.py
      indexing_service.py
      chunking_service.py
      embedding_service.py
      search_service.py
      citation_service.py
    storage/
      base.py
      local_storage.py
    repository/
      documents.py
      chunks.py
```

## 4. 数据库迁移

必须创建：

- `document`
- `document_chunk`
- `document_index_job`

`document_index_job` 字段：

- id
- document_id
- status
- error_message
- created_at
- started_at
- finished_at

## 5. API 开发任务

### 5.1 工具协议接口

- `GET /health`
- `GET /tool/manifest`
- `GET /tool/capabilities`
- `POST /tool/invoke`

### 5.2 业务接口

- `POST /api/documents`
- `GET /api/documents/{id}`
- `POST /api/documents/{id}/index`
- `POST /api/knowledge/search`
- `GET /api/knowledge/chunks/{id}`

## 6. 核心实现要求

### ChunkingService

必须支持：

- Markdown 标题切片。
- TXT 段落切片。
- chunk size 配置。
- overlap 配置。
- heading_path。
- content_hash。

### EmbeddingService

必须提供接口：

```text
embed(text): vector
embedBatch(texts): vectors
```

MVP 可实现：

- MockEmbeddingService。
- 后续替换真实 embedding provider。

### SearchService

必须实现：

- metadata filter。
- keyword search。
- vector search。
- score merge。
- top_k。

## 7. 测试清单

单元测试：

- Markdown 切片。
- overlap 逻辑。
- citation_id 生成。
- metadata filter。

集成测试：

- 创建文档。
- 索引文档。
- 搜索文档。
- 跨 project_id 隔离。

端到端测试：

```text
启动 knowledge-tool
  -> 上传 examples/order.md
  -> index
  -> search "审批接口"
  -> 返回 citation_id
```

## 8. Definition of Done

- 工具可独立启动。
- controller 可安装。
- `/tool/capabilities` 返回 `knowledge.search`。
- 文档搜索 P95 小于 1500ms。
- 检索结果有来源。
- 所有错误结构化。
