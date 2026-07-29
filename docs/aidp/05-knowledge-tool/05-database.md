# Database Schema

所有表使用 UUID 主键，支持软删除（`deleted_at` 字段）。

---

## `kt_knowledge_bases` — 知识库

| 列 | 类型 | 说明 |
|----|------|------|
| `id` | String(36) PK | UUID |
| `name` | String(128) | 名称 |
| `slug` | String(128) UNIQUE | URL 友好标识 |
| `description` | Text | 描述 |
| `kb_level` | String(32) | 层级: `project`/`template`/`framework` |
| `parent_id` | FK → kt_knowledge_bases.id | 父级知识库（自引用树形结构） |
| `domains` | Text | JSON 数组，知识领域 |
| `keywords` | Text | JSON 数组 |
| `tech_stack` | Text | JSON 数组 |
| `visibility` | String(20) | `private`/`public` |
| `owner_id` | String(128) | 所有者 |
| `chunk_size` | Integer | 默认 512 |
| `overlap_size` | Integer | 默认 50 |
| `embedding_model` | String(128) | 默认 `text-embedding-3-small` |
| `created_at` / `updated_at` | DateTime | 时间戳 |
| `deleted_at` | DateTime | 软删除时间 |

---

## `kt_project_knowledge_bindings` — 项目-知识库绑定

| 列 | 类型 | 说明 |
|----|------|------|
| `id` | String(36) PK | UUID |
| `project_id` | String(128) | 项目 ID |
| `knowledge_base_id` | FK → kt_knowledge_bases.id | 知识库 ID |
| `binding_type` | String(32) | `auto_matched`（默认） |
| `priority` | Integer | 优先级 |
| `created_at` | DateTime | 时间戳 |

用于项目与知识库的多对多关联。

---

## `kt_document` — 文档主表

| 列 | 类型 | 说明 |
|----|------|------|
| `id` | String(36) PK | UUID |
| `workspace_id` | String(128) | 工作区 |
| `project_id` | String(128) | 项目 |
| `knowledge_base_id` | FK → kt_knowledge_bases.id | 所属知识库 |
| `title` | String(512) | 标题 |
| `doc_type` | String(128) | `markdown`/`md`/`text` |
| `visibility` | String(32) | 可见性 |
| `owner_type` | String(32) | `personal`（默认） |
| `owner_id` | String(128) | 所有者 |
| `source_uri` | Text | 来源 URI |
| `object_key` | Text | 存储对象键（文件路径） |
| `mime_type` | String(255) | MIME 类型 |
| `file_name` | String(512) | 文件名 |
| `file_size` | Integer | 文件大小（字节） |
| `checksum` | String(128) | 内容校验和 |
| `version` | String(128) | `v1`（默认） |
| `index_status` | String(32) | `created`/`indexed` |
| `tags` | Text | JSON 数组 |
| `metadata` | Text | JSON 元数据 |
| `summary` | Text | 文档摘要 |
| `summary_embedding` | Text | 摘要向量 |
| `created_by` / `updated_by` | String(128) | 操作人 |
| `created_at` / `updated_at` | DateTime | 时间戳 |
| `deleted_at` | DateTime | 软删除 |

---

## `kt_document_chunk` — 文档分块

| 列 | 类型 | 说明 |
|----|------|------|
| `id` | String(36) PK | UUID |
| `document_id` | FK → kt_document.id | 所属文档 |
| `workspace_id` | String(128) | 工作区 |
| `project_id` | String(128) | 项目 |
| `chunk_index` | Integer | 块序号 |
| `content` | Text | 块内容 |
| `content_hash` | String(128) | 内容哈希 |
| `token_count` | Integer | Token 数 |
| `heading_path` | JSONB | 标题路径数组 |
| `source_start_line` | Integer | 源起始行号 |
| `source_end_line` | Integer | 源结束行号 |
| `page_number` | Integer | 页码 |
| `embedding_model` | String(128) | 嵌入模型名 |
| `embedding_provider` | String(128) | 嵌入提供者 |
| `embedding_dimension` | Integer | 向量维度 |
| `embedding` | Text | JSON 序列化的向量 |
| `keyword_tsv` | Text | 关键字文本检索 |
| `metadata` | JSONB | 元数据 |
| `created_at` / `updated_at` | DateTime | 时间戳 |
| `deleted_at` | DateTime | 软删除 |

**约束**: `UNIQUE(document_id, chunk_index)`

---

## `kt_document_index_job` — 索引任务

| 列 | 类型 | 说明 |
|----|------|------|
| `id` | String(36) PK | UUID |
| `document_id` | FK → kt_document.id | 关联文档 |
| `workspace_id` | String(128) | 工作区 |
| `project_id` | String(128) | 项目 |
| `status` | String(32) | `pending`/`running`/`succeeded`/`failed` |
| `trigger_type` | String(32) | `manual`（默认） |
| `force_reindex` | Boolean | 是否强制重建索引 |
| `chunk_size` | Integer | 分块大小 |
| `overlap_size` | Integer | 重叠字数 |
| `embedding_model` | String(128) | 嵌入模型 |
| `chunk_count` | Integer | 生成块数 |
| `error_code` | String(128) | 错误码 |
| `error_message` | Text | 错误信息 |
| `error_details` | JSONB | 错误详情 |
| `trace_id` | String(128) | 追踪 ID |
| `created_by` | String(128) | 创建人 |
| `created_at` | DateTime | 创建时间 |
| `started_at` | DateTime | 开始时间 |
| `finished_at` | DateTime | 完成时间 |

---

## 辅助函数

| 函数 | 说明 |
|------|------|
| `utcnow()` | 返回 UTC 当前时间 |
| `gen_uuid()` | 生成 UUID 字符串 |
| `_json_default(value)` | JSON 序列化（用于 SQLite） |
| `_json_loads(value)` | JSON 反序列化（用于 SQLite） |

---

## ER 关系图

```
kt_knowledge_bases (1) ──< (N) kt_project_knowledge_bindings (N) >── project
       │
       │ (parent_id 自引用)
       │
       └──< (N) kt_document (1) ──< (N) kt_document_chunk
                    │
                    └──< (N) kt_document_index_job
```