# knowledge-tool 模块设计

## 1. 推荐代码结构

以 Python 3.11+ + FastAPI 为默认实现：

```text
knowledge-tool/
  tool.yaml
  openapi.yaml
  config.example.yaml
  migrations/
  src/aidp_knowledge/
    main.py
    api/
      health.py
      tool_protocol.py
      documents.py
      search.py
      index_jobs.py
    services/
      document_service.py
      indexing_service.py
      search_service.py
      permission_scope_service.py
      citation_service.py
    parser/
      base.py
      markdown_parser.py
      plain_text_parser.py
      source_text_parser.py
    chunk/
      service.py
      markdown_heading_chunker.py
      paragraph_chunker.py
      source_line_chunker.py
    embedding/
      base.py
      mock_provider.py
      pgvector_store.py
    search/
      keyword_engine.py
      vector_engine.py
      hybrid_score_merger.py
    storage/
      base.py
      local_storage.py
    repository/
      documents.py
      chunks.py
      index_jobs.py
    domain/
      models.py
      enums.py
    common/
      trace.py
      response.py
      errors.py
```

## 2. 模块职责

### 2.1 `api`

负责 HTTP 层：

- 接收请求。
- 参数校验。
- 转换 DTO。
- 统一返回结构。
- 捕获异常并转换为结构化错误。

禁止在 controller 中写业务逻辑。controller 只调用 application service。

### 2.2 `application`

负责业务编排：

- `DocumentService`：文档登记、更新、删除、查询。
- `IndexingService`：创建索引任务、执行索引、重建索引。
- `SearchService`：检索流程编排。
- `PermissionScopeService`：工作区、项目、可见性过滤。
- `CitationService`：生成 citation 和 source refs。

### 2.3 `parser`

负责从原始文件得到结构化文本：

```python
class DocumentParser(Protocol):
    def supports(self, input: ParseInput) -> bool: ...
    def parse(self, input: ParseInput) -> ParsedDocument: ...
```

`ParsedDocument` 至少包含：

- title
- sections
- metadata
- checksum

`ParsedSection` 至少包含：

- headingPath
- text
- startLine
- endLine
- pageNumber
- metadata

### 2.4 `chunk`

负责切片：

```python
class ChunkingService(Protocol):
    def split(self, document: ParsedDocument, options: ChunkingOptions) -> list[ChunkCandidate]: ...
```

切片必须保证：

- chunk 顺序稳定。
- 同一内容生成相同 `content_hash`。
- chunk 不为空。
- chunk token 数不超过配置硬上限。

### 2.5 `embedding`

负责向量生成：

```python
class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> EmbeddingVector: ...
    def embed_batch(self, texts: list[str]) -> list[EmbeddingVector]: ...
    def provider(self) -> str: ...
    def model(self) -> str: ...
    def dimension(self) -> int: ...
```

MVP 的 `MockEmbeddingProvider` 必须是确定性的。相同文本生成相同向量，便于测试。

### 2.6 `search`

负责检索实现：

- `KeywordSearchEngine` 使用 PostgreSQL full text search 或 `ILIKE` MVP 降级。
- `VectorSearchEngine` 使用 `VectorStore`。
- `HybridScoreMerger` 合并关键词分数和向量分数。

混合分数默认公式：

```text
final_score = vector_score * 0.60
            + keyword_score * 0.25
            + scope_boost * 0.10
            + freshness_boost * 0.05
```

### 2.7 `storage`

负责原始文件存取：

```python
class ObjectStorage(Protocol):
    def put(self, input: BinaryIO, request: StoragePutRequest) -> StoredObject: ...
    def get(self, object_key: str) -> BinaryIO: ...
    def delete(self, object_key: str) -> None: ...
    def exists(self, object_key: str) -> bool: ...
```

MVP 默认 `LocalObjectStorage`。

## 3. 领域对象

### 3.1 Document

字段职责：

- `id`：文档 ID。
- `workspaceId`：工作区 ID。
- `projectId`：项目 ID，可为空。
- `title`：展示标题。
- `docType`：文档类型。
- `visibility`：可见性。
- `sourceUri`：来源。
- `objectKey`：存储对象 key。
- `checksum`：文件 hash。
- `version`：业务版本。
- `indexStatus`：索引状态。
- `tags`：标签。
- `metadata`：扩展元数据。

### 3.2 DocumentChunk

字段职责：

- `id`：chunk ID。
- `documentId`：所属文档。
- `chunkIndex`：文档内序号。
- `content`：片段文本。
- `contentHash`：内容 hash。
- `headingPath`：标题路径。
- `sourceStartLine`：来源起始行。
- `sourceEndLine`：来源结束行。
- `embedding`：向量。
- `embeddingModel`：向量模型。
- `metadata`：扩展元数据。

### 3.3 DocumentIndexJob

字段职责：

- `id`：任务 ID。
- `documentId`：文档 ID。
- `status`：任务状态。
- `triggerType`：触发方式。
- `errorCode`：失败错误码。
- `errorMessage`：失败摘要。
- `startedAt`：开始时间。
- `finishedAt`：结束时间。

## 4. 状态机

### 4.1 文档索引状态

```text
created
  -> indexing
  -> indexed
  -> index_failed
  -> deleted
```

规则：

- 文档创建后为 `created`。
- 开始索引时变为 `indexing`。
- 成功后变为 `indexed`。
- 失败后变为 `index_failed`。
- 删除后变为 `deleted`。

### 4.2 索引任务状态

```text
pending
  -> running
  -> succeeded
  -> failed
  -> canceled
```

规则：

- `pending` 只能进入 `running` 或 `canceled`。
- `running` 只能进入 `succeeded`、`failed` 或 `canceled`。
- 终态不可再修改。

## 5. 关键服务详细设计

### 5.1 DocumentService

主要方法：

```text
createDocument(command)
getDocument(id, scope)
updateDocument(id, command)
deleteDocument(id, scope)
listDocuments(query, scope)
```

必须做：

- 校验 `workspace_id`。
- 根据 visibility 校验 `project_id`。
- 计算 checksum。
- 写入文档元数据。
- 删除时软删除。

### 5.2 IndexingService

主要方法：

```text
createIndexJob(documentId, options)
runIndexJob(jobId)
reindexDocument(documentId, options)
cancelJob(jobId)
```

索引步骤：

1. 加载文档。
2. 校验权限和状态。
3. 加锁，防止同一文档并发索引。
4. 读取原始文件。
5. 解析。
6. 切片。
7. 批量 embedding。
8. 批量写入 chunk。
9. 更新文档状态。
10. 更新任务状态。

错误处理：

- parser 失败：`PARSE_FAILED`。
- embedding 失败：`EMBEDDING_FAILED`。
- vector store 失败：`VECTOR_STORE_FAILED`。
- 文件不存在：`SOURCE_NOT_FOUND`。

### 5.3 SearchService

主要方法：

```text
search(SearchCommand command, PermissionScope scope)
getChunk(chunkId, scope)
```

检索步骤：

1. 校验 query 和 top_k。
2. 构造权限过滤条件。
3. 执行 keyword search。
4. 执行 vector search。
5. 合并和去重 chunk。
6. 生成 citation。
7. 返回结果。

降级策略：

- vector store 不可用时可降级 keyword search。
- 降级响应必须包含 `degraded=true` 和 `degrade_reason`。

## 6. 异常处理

所有业务异常必须转换为统一错误码：

| 错误码 | HTTP 状态 | 场景 |
|---|---:|---|
| `VALIDATION_ERROR` | 400 | 参数缺失或非法 |
| `UNAUTHORIZED` | 401 | 缺少认证 |
| `FORBIDDEN` | 403 | 无工作区或项目权限 |
| `NOT_FOUND` | 404 | 文档、chunk、任务不存在 |
| `CONFLICT` | 409 | 重复索引、状态冲突 |
| `SOURCE_NOT_FOUND` | 422 | 原始文件不存在 |
| `PARSE_FAILED` | 422 | 文档解析失败 |
| `EMBEDDING_FAILED` | 502 | 向量生成失败 |
| `DEPENDENCY_UNAVAILABLE` | 503 | 数据库、向量库不可用 |
| `INTERNAL_ERROR` | 500 | 未预期异常 |

## 7. 配置项

推荐配置：

```yaml
server:
  port: 8080

knowledge:
  storage:
    provider: local
    localRoot: ./data/knowledge
  chunking:
    defaultChunkSize: 800
    defaultOverlap: 120
    maxChunkSize: 1600
  embedding:
    provider: mock
    model: mock-embedding-v1
    dimension: 384
  search:
    defaultTopK: 8
    maxTopK: 50
    defaultMode: hybrid
  upload:
    maxFileSizeMb: 50
    allowedExtensions:
      - .md
      - .txt
      - .java
      - .kt
      - .ts
      - .py
      - .sql
```

## 8. 并发控制

- 同一 `document_id` 同一时间只能有一个 running index job。
- 批量 embedding 应限制 batch size。
- 检索接口应限制并发和 top_k。
- 文件上传应限制大小。

## 9. 可测试性要求

模块必须易于单元测试：

- Parser 不依赖数据库。
- Chunker 不依赖数据库。
- MockEmbeddingProvider 确定性输出。
- SearchService 可注入 mock search engine。
- 时间通过 `ClockProvider` 注入。
