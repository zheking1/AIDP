# knowledge-tool 测试与验收

## 1. 测试目标

测试必须证明 `knowledge-tool` 在以下方面可用：

- 工具协议兼容 controller。
- 文档可以创建、上传、索引、删除。
- Markdown/TXT/source 文档可以被正确解析和切片。
- 检索结果准确、可追溯、带权限隔离。
- 错误返回结构化。
- standalone 和 managed 两种模式都能工作。

## 2. 测试分层

| 测试类型 | 覆盖范围 | 是否必须 |
|---|---|---|
| 单元测试 | parser、chunker、citation、score merge | 是 |
| Repository 测试 | PostgreSQL 表、索引、scope 查询 | 是 |
| API 测试 | controller、DTO、错误响应 | 是 |
| 工具协议测试 | manifest、capabilities、invoke | 是 |
| 集成测试 | 文档创建到检索完整流程 | 是 |
| 端到端测试 | standalone 和 controller managed | 是 |
| 性能测试 | 检索延迟、索引耗时 | MVP 基线 |
| 安全测试 | 跨项目访问、路径越权、文件限制 | 是 |

## 3. 单元测试清单

### 3.1 MarkdownParser

用例：

- 一级标题、二级标题生成正确 heading path。
- 代码块不破坏解析。
- front matter 进入 metadata。
- 空文件返回解析失败。
- 非 UTF-8 文件返回明确错误。

验收：

- section 数量稳定。
- `startLine`、`endLine` 正确。
- 标题路径不丢失。

### 3.2 PlainTextParser

用例：

- 空行分段。
- 连续空行合并。
- 超长段落可继续切分。
- 保留段落顺序。

### 3.3 SourceTextParser

用例：

- TypeScript/Python 文件按行生成 chunk candidate。
- SQL 文件保留语句边界。
- 大文件不一次性生成超大 chunk。

### 3.4 ChunkingService

用例：

- chunk size 限制生效。
- overlap 生效。
- content hash 稳定。
- heading_path 传递到 chunk。
- 空 section 不生成 chunk。

### 3.5 MockEmbeddingProvider

用例：

- 相同文本生成相同向量。
- 不同文本生成不同向量。
- dimension 等于配置。
- batch 和单条结果一致。

### 3.6 HybridScoreMerger

用例：

- keyword 和 vector 同时命中时分数更高。
- project scope boost 生效。
- min_score 过滤生效。
- 去重按 chunk_id 合并。

### 3.7 CitationService

用例：

- citation_id 格式正确。
- source refs 包含 document 和 chunk。
- version 缺失时使用默认版本。

## 4. Repository 测试

建议使用 Testcontainers PostgreSQL。

### 4.1 文档表

用例：

- 插入 project 文档成功。
- `visibility=project` 但 `project_id=null` 失败。
- soft delete 后默认查询不可见。
- tags GIN 查询可用。

### 4.2 Chunk 表

用例：

- 同一文档 chunk_index 唯一。
- 按 workspace/project 查询。
- deleted chunk 不参与检索。
- keyword_tsv 查询可返回结果。

### 4.3 Index Job 表

用例：

- job 状态写入。
- trace_id 可查询。
- 任务失败记录 error_code。

## 5. API 测试

### 5.1 创建文档

请求缺少 `workspace_id`：

期望：

- HTTP 400。
- code=`VALIDATION_ERROR`。
- 不写入数据库。

创建 project 文档：

期望：

- HTTP 200。
- 返回 `document_id`。
- `index_status=created`。

### 5.2 上传文件

用例：

- 上传 Markdown 成功。
- 上传超大文件失败。
- 上传不支持扩展名失败。
- 上传文件名包含特殊字符时 object key 安全。

### 5.3 索引文档

用例：

- 已创建文档可以索引。
- 不存在文档返回 404。
- 无权限文档返回 403。
- 重复索引返回已有 running job 或新建 force job。

### 5.4 检索

用例：

- 空 query 返回 400。
- top_k 超过上限返回 400 或自动截断，必须文档明确。
- hybrid 检索返回 items。
- `include_content=false` 不返回 content。
- 返回 citation_id。

### 5.5 删除

用例：

- 删除后无法检索。
- 删除后 get 返回 deleted 或 404，必须实现保持一致。
- purge 需要管理员权限。

## 6. 工具协议测试

### 6.1 `/health`

期望：

- tool name 正确。
- version 正确。
- dependencies 存在。

### 6.2 `/tool/manifest`

期望：

- 与 `tool.yaml` 一致。
- metadata.name=`knowledge-tool`。
- capabilities 包含 `knowledge.search`。

### 6.3 `/tool/capabilities`

期望：

- 每个 capability 有 name、permission、input_schema、output_schema。
- schema 可被 JSON Schema validator 校验。

### 6.4 `/tool/invoke`

用例：

- 调用 `knowledge.search` 成功。
- 调用不存在 capability 返回 `NOT_FOUND`。
- 缺少 context 返回 `VALIDATION_ERROR`。
- trace_id 原样返回。

## 7. 集成测试场景

### 7.1 Markdown 入库检索

步骤：

1. 启动 PostgreSQL。
2. 启动 `knowledge-tool`。
3. 创建文档，内容包含“订单状态为 SUBMITTED 时可以发起审批”。
4. 调用索引。
5. 等待 job succeeded。
6. 搜索“什么时候可以发起订单审批”。

期望：

- 返回至少 1 个结果。
- 第一条结果来自该文档。
- `citation_id` 非空。
- `heading_path` 非空。

### 7.2 跨项目隔离

步骤：

1. 在 `project_a` 创建文档，内容包含唯一词 `A_ONLY_SECRET_RULE`。
2. 在 `project_b` 搜索该唯一词。

期望：

- 不返回 `project_a` 文档。
- 如果直接 get chunk，返回 403 或 404。

### 7.3 workspace 文档共享

步骤：

1. 创建 `visibility=workspace` 文档。
2. 在同一 workspace 下不同 project 搜索。

期望：

- 可以返回。
- source ref 中 visibility 为 workspace。

### 7.4 降级检索

步骤：

1. 配置 vector store 不可用。
2. 启动 keyword search。
3. 搜索关键词。

期望：

- 请求成功。
- `degraded=true`。
- `degrade_reason=VECTOR_STORE_UNAVAILABLE`。

## 8. 端到端验收

### 8.1 standalone 验收

命令：

```bash
docker compose -f examples/standalone-compose.yml up -d
```

步骤：

```text
GET /health
POST /api/documents
POST /api/documents/{id}/index
GET /api/index-jobs/{job_id}
POST /api/knowledge/search
```

验收：

- 全流程成功。
- 日志中能看到同一个 trace_id。
- 检索结果包含来源。

### 8.2 managed 验收

步骤：

1. 启动 `aidp-controller`。
2. 安装 `knowledge-tool`。
3. controller 健康检查通过。
4. controller 注册 capability。
5. 通过 MCP Skill 调用 `knowledge.search`。

验收：

- controller 工具列表显示 UP。
- 调用审计记录成功。
- tool invocation 有 `elapsed_ms`。

## 9. 性能验收

MVP 基线：

| 指标 | 目标 |
|---|---:|
| 1000 篇 Markdown，top_k=8，P95 检索 | < 1500ms |
| 单篇 1MB Markdown mock embedding 索引 | < 15s |
| 10MB TXT 拒绝或流式处理 | 不 OOM |
| 并发 10 个检索请求 | 无错误 |

性能测试数据必须写入测试报告。

## 10. 安全验收

必须覆盖：

- 路径穿越：`../../secret` 不能读取。
- 跨 project 搜索不能泄露。
- 直接 chunk_id 访问不能绕过权限。
- 文件大小限制生效。
- 错误日志不打印全文。
- `top_k` 上限生效。

## 11. 最终验收清单

发布前必须全部通过：

- [ ] `tool.yaml` 存在且 schema 合法。
- [ ] `openapi.yaml` 存在且覆盖所有 API。
- [ ] `config.example.yaml` 可启动。
- [ ] `/health` 可用。
- [ ] `/tool/manifest` 可用。
- [ ] `/tool/capabilities` 可用。
- [ ] `/tool/invoke` 可调用 `knowledge.search`。
- [ ] Markdown 文档可创建、索引、检索。
- [ ] TXT 文档可创建、索引、检索。
- [ ] 检索结果有 citation。
- [ ] 跨项目隔离测试通过。
- [ ] 降级检索测试通过。
- [ ] 所有错误结构化。
- [ ] standalone 示例可运行。
- [ ] controller managed 联调通过。
