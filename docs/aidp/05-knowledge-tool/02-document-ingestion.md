# Document Ingestion & Indexing

## 文档服务 (`document_service.py`)

### 核心函数

#### `create_document(db, req) → DocumentInfo`

接收 `DocumentCreateRequest` 并创建 `KtDocument` 记录。关键字段：

| 参数 | 说明 |
|------|------|
| `workspace_id` | 工作区 ID |
| `project_id` | 项目 ID |
| `knowledge_base_id` | 所属知识库 ID |
| `title` | 文档标题 |
| `doc_type` | 文档类型（`markdown`/`md`/`text`） |
| `visibility` | 可见性级别 |
| `version` | 版本号（默认 `v1`） |
| `tags` | 标签列表（存储为 JSON 字符串） |
| `source_uri` | 来源 URI |
| `metadata_` | 元数据 JSON |

初始 `index_status` 设为 `"created"`。

#### `get_document(db, doc_id, workspace_id)`

按 ID 查询文档（可过滤 `workspace_id`），返回 `DocumentInfo` 或 `None`。

#### `list_documents(db, workspace_id, project_id, knowledge_base_id, doc_type, page, page_size, owner_type)`

分页列表查询，支持按 workspace、project、knowledge_base、doc_type、owner_type 多维度过滤。返回 `DocumentInfo` 列表。

#### `delete_document(db, doc_id, workspace_id)`

软删除：设置 `deleted_at = datetime.now(timezone.utc)`。

#### `get_document_content(db, doc_id)`

从本地存储读取原始文档内容（`STORAGE_LOCAL_ROOT + object_key`）。

### DocumentInfo 结构

转换时：
- `tags` 字段自动从 JSON 字符串解析为列表
- `created_at`/`updated_at` 格式化为 ISO 字符串
- 返回 `id`、`title`、`doc_type`、`visibility`、`version`、`index_status`、`checksum`、`file_name`、`mime_type`、`file_size`、`object_key` 等完整信息

---

## 索引服务 (`indexing_service.py`)

### 解析器与分块器

模块级单例:
- **MarkdownParser** — 解析 `markdown`/`md` 类型文档
- **PlainTextParser** — 解析纯文本文档
- **MarkdownChunker** — 基于标题结构的分块器
- **LocalObjectStorage** — 本地文件存储读写

### 嵌入提供者工厂

`_get_embedding_provider()` 根据 `EMBEDDING_PROVIDER` 配置返回：
- `"openai"` → `OpenAIEmbeddingProvider`（调用 OpenAI API）
- `"local"` → `LocalEmbeddingProvider`（本地模型 `all-MiniLM-L6-v2`）
- 默认（`mock`） → `MockEmbeddingProvider`（返回模拟向量，维度可配置）

### 索引流程

#### Step 1: `create_index_job(db, document_id, workspace_id, project_id, chunk_size, overlap, embedding_model, force)`

创建 `KtDocumentIndexJob` 记录：
- 状态: `"pending"`
- 触发类型: `"manual"`
- 配置: `chunk_size`（默认 800）、`overlap`（默认 120）

#### Step 2: `run_index_job(db, job_id)`

完整流程：

1. **加载文档内容**: 通过 `storage.get(object_key)` 从本地文件系统读取 UTF-8 内容
2. **解析**: 根据 `doc_type` 选择 Markdown/PlainText 解析器
3. **分块**: 使用 `MarkdownChunker.split(parsed.sections, ChunkingOptions)` 生成块候选列表
4. **清理旧块**: 删除该文档已有的所有 `KtDocumentChunk` 记录
5. **生成嵌入**: 对每个块调用嵌入提供者
   - OpenAI: 支持批量 (`embed_batch`)
   - 其他: 单条调用 (`embed`)
6. **写入块记录**: 保存 `content`、`content_hash`、`token_count`、`heading_path`、`source_start_line`/`source_end_line`、`embedding`（JSON 序列化）、`embedding_model`、`embedding_provider`、`embedding_dimension`
7. **更新状态**: 文档 `index_status → "indexed"`，任务 `status → "succeeded"`，记录 `chunk_count`
8. **错误处理**: 失败时 `status → "failed"`，记录 `error_code` 和 `error_message`

### ChunkingOptions

```python
class ChunkingOptions:
    chunk_size: int  # 默认 800
    overlap: int     # 默认 120
```

### IndexJobInfo 输出

| 字段 | 说明 |
|------|------|
| `id` | 任务 ID |
| `document_id` | 关联文档 ID |
| `status` | `pending`/`running`/`succeeded`/`failed` |
| `chunk_count` | 生成的分块数 |
| `error_code` / `error_message` | 错误信息 |
| `started_at` / `finished_at` | 时间戳 |