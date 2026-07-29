# API Reference

## 工具调用协议 (`tool.py`)

### `GET /tool/manifest`

返回工具的注册清单：
```json
{
    "apiVersion": "aidp.dev/v1",
    "kind": "Tool",
    "metadata": { "name": "knowledge-tool", "version": "0.1.0" },
    "capabilities": ["knowledge.search", "document.index"]
}
```

### `GET /tool/capabilities`

返回所有 capability 详情，包括 input/output schema。

### `POST /tool/invoke`

统一工具调用入口。

**请求格式**:
```json
{
    "trace_id": "tr_abc123",
    "capability": "knowledge.search",
    "context": { "workspace_id": "ws1", "project_id": "proj1" },
    "input": { "query": "how to deploy", "top_k": 8 }
}
```

**响应格式**:
```json
{
    "trace_id": "tr_abc123",
    "tool": "knowledge-tool",
    "capability": "knowledge.search",
    "success": true,
    "output": { ... },
    "elapsed_ms": 42
}
```

---

## Capability 详解

### 1. `knowledge.search`

- **端点**: `POST /api/knowledge/search`
- **超时**: 3000ms
- **权限**: `knowledge:search`

**输入参数**:
| 参数 | 类型 | 必需 | 默认 | 说明 |
|------|------|------|------|------|
| `query` | string | ✓ | - | 搜索查询 |
| `top_k` | integer | | 8 | 返回结果数 |
| `min_score` | float | | 0.1 | 最低分数阈值 |

**Context 参数**:
| 参数 | 说明 |
|------|------|
| `workspace_id` | 工作区范围 |
| `project_id` | 项目范围 |
| `knowledge_base_ids` | 指定知识库列表 |
| `task_domains` | 任务领域过滤 |

### 2. `knowledge.create_document`

- **端点**: `POST /api/documents`
- **超时**: 15000ms
- **权限**: `knowledge:write`

**输入参数**:
| 参数 | 类型 | 必需 | 默认 | 说明 |
|------|------|------|------|------|
| `title` | string | ✓ | - | 文档标题 |
| `content` | string | ✓ | - | 文档内容 |
| `doc_type` | string | | `markdown` | 文档类型 |
| `tags` | string[] | | [] | 标签列表 |
| `knowledge_base_id` | string | | - | 所属知识库 |

创建文档后**自动触发索引任务** (`create_index_job`)。

### 3. `document.index`

- **端点**: `POST /api/documents/{id}/index`
- **超时**: 10000ms
- **权限**: `knowledge:index`

**输入参数**:
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `document_id` | string | ✓ | 文档 ID |

执行完整的创建索引任务 + 运行索引任务流程，返回 `IndexJobInfo`。

---

## Documents API (`documents.py`)

### `POST /api/documents`

创建文档记录。

### `GET /api/documents`

列表查询，支持参数:
- `workspace_id`, `project_id`, `kb_id`, `doc_type`, `owner_type`
- `page`（默认 1）, `page_size`（默认 20）

### `GET /api/documents/{document_id}`

获取单个文档详情。

### `DELETE /api/documents/{document_id}`

软删除文档。

### `POST /api/documents/{document_id}/index`

创建并执行索引任务。请求体 `IndexJobRequest`:
```json
{
    "workspace_id": "...",
    "chunk_size": 800,
    "overlap": 120,
    "embedding_model": "mock-embedding-v1",
    "force": false
}
```

### `GET /api/documents/{document_id}/content`

获取文档原始内容（从文件存储读取）。

### `GET /api/documents/{document_id}/chunks`

分页获取文档的所有 chunks。参数: `page`（默认 1）、`page_size`（默认 100）。

返回每个 chunk 的 `id`、`chunk_index`、`content`、`token_count`、`heading_path`、`source_start_line`、`source_end_line`、`page_number`、`created_at`。

### `GET /api/documents/{document_id}/graph`

获取文档知识图谱（调用 `KnowledgeGraph.compute_relevance`）。

### `POST /api/documents/{document_id}/link`

将文档关联到代码节点。

### `GET /api/documents/{document_id}/drift`

检测文档漂移（调用 `DriftDetector.detect_drift`）。

### 遗留端点

- `GET /api/documents/search/fts` — FTS5 全文搜索
- `GET /api/documents/search/semantic` — Jaccard 语义搜索

---

## Search API (`search.py`)

### `POST /api/knowledge/search`

标准搜索（summary + chunk 双层）。调用 `SearchService.search()`。

### `POST /api/knowledge/search/semantic`

混合搜索（Exact + Vector + BM25）。调用 `SearchService.semantic_search()`。

通过 `search_mode` 参数可选 `hybrid`/`exact`/`vector`/`bm25`。