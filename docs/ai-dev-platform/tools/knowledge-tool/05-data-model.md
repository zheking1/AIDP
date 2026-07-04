# knowledge-tool 数据模型设计

## 1. 数据存储范围

`knowledge-tool` 管理自己的业务数据。controller 只保存工具注册、capability 和调用审计，不直接读写本工具业务表。

默认数据库：

- PostgreSQL 15+
- 可选 PGVector
- migration 管理迁移，Python 默认 Alembic 或纯 SQL

默认对象存储：

- 本地文件系统
- 后续可配置 MinIO/S3

## 2. 表清单

| 表 | 用途 | MVP |
|---|---|---|
| `kt_document` | 文档元数据 | 是 |
| `kt_document_chunk` | 文档切片和向量 | 是 |
| `kt_document_index_job` | 索引任务 | 是 |
| `kt_document_version` | 文档版本 | 否，增强 |
| `kt_import_batch` | 批量导入任务 | 否，增强 |
| `kt_parser_registry` | 解析器配置 | 否，增强 |

表名前缀 `kt_` 用于避免与 controller 或其它工具冲突。

## 3. 枚举定义

### 3.1 visibility

```text
global
workspace
project
```

### 3.2 index_status

```text
created
indexing
indexed
index_failed
deleted
```

### 3.3 job_status

```text
pending
running
succeeded
failed
canceled
```

### 3.4 search_mode

```text
keyword
vector
hybrid
```

## 4. `kt_document`

用途：保存文档元数据和原始文件位置。

DDL：

```sql
create table kt_document (
  id uuid primary key,
  workspace_id varchar(128) not null,
  project_id varchar(128),
  title varchar(512) not null,
  doc_type varchar(128) not null,
  visibility varchar(32) not null,
  source_uri text,
  object_key text,
  mime_type varchar(255),
  file_name varchar(512),
  file_size bigint,
  checksum varchar(128),
  version varchar(128) not null default 'v1',
  index_status varchar(32) not null default 'created',
  tags jsonb not null default '[]',
  metadata jsonb not null default '{}',
  created_by varchar(128),
  updated_by varchar(128),
  created_at timestamptz not null,
  updated_at timestamptz not null,
  deleted_at timestamptz
);
```

约束：

```sql
alter table kt_document
  add constraint kt_document_visibility_ck
  check (visibility in ('global', 'workspace', 'project'));

alter table kt_document
  add constraint kt_document_index_status_ck
  check (index_status in ('created', 'indexing', 'indexed', 'index_failed', 'deleted'));

alter table kt_document
  add constraint kt_document_project_visibility_ck
  check (
    (visibility = 'project' and project_id is not null)
    or visibility in ('global', 'workspace')
  );
```

索引：

```sql
create index idx_kt_document_scope
  on kt_document (workspace_id, project_id, visibility)
  where deleted_at is null;

create index idx_kt_document_doc_type
  on kt_document (doc_type)
  where deleted_at is null;

create index idx_kt_document_index_status
  on kt_document (index_status)
  where deleted_at is null;

create index idx_kt_document_tags
  on kt_document using gin (tags);

create index idx_kt_document_metadata
  on kt_document using gin (metadata);
```

## 5. `kt_document_chunk`

用途：保存文档切片、文本、向量和来源位置。

DDL：

```sql
create table kt_document_chunk (
  id uuid primary key,
  document_id uuid not null references kt_document(id),
  workspace_id varchar(128) not null,
  project_id varchar(128),
  chunk_index int not null,
  content text not null,
  content_hash varchar(128) not null,
  token_count int not null,
  heading_path jsonb not null default '[]',
  source_start_line int,
  source_end_line int,
  page_number int,
  embedding_model varchar(128),
  embedding_provider varchar(128),
  embedding_dimension int,
  embedding vector,
  keyword_tsv tsvector,
  metadata jsonb not null default '{}',
  created_at timestamptz not null,
  updated_at timestamptz not null,
  deleted_at timestamptz,
  unique (document_id, chunk_index)
);
```

说明：

- 如果未启用 PGVector，`embedding` 字段可不创建，或使用单独迁移脚本。
- `workspace_id`、`project_id` 冗余保存是为了检索过滤性能。
- `keyword_tsv` 可由触发器或应用层维护。

索引：

```sql
create index idx_kt_chunk_document
  on kt_document_chunk (document_id)
  where deleted_at is null;

create index idx_kt_chunk_scope
  on kt_document_chunk (workspace_id, project_id)
  where deleted_at is null;

create index idx_kt_chunk_keyword
  on kt_document_chunk using gin (keyword_tsv);

create index idx_kt_chunk_metadata
  on kt_document_chunk using gin (metadata);
```

PGVector 索引示例：

```sql
create index idx_kt_chunk_embedding
  on kt_document_chunk
  using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);
```

## 6. `kt_document_index_job`

用途：保存索引任务。

DDL：

```sql
create table kt_document_index_job (
  id uuid primary key,
  document_id uuid not null references kt_document(id),
  workspace_id varchar(128) not null,
  project_id varchar(128),
  status varchar(32) not null,
  trigger_type varchar(32) not null default 'manual',
  force_reindex boolean not null default false,
  chunk_size int,
  overlap_size int,
  embedding_model varchar(128),
  chunk_count int,
  error_code varchar(128),
  error_message text,
  error_details jsonb not null default '{}',
  trace_id varchar(128),
  created_by varchar(128),
  created_at timestamptz not null,
  started_at timestamptz,
  finished_at timestamptz
);
```

约束：

```sql
alter table kt_document_index_job
  add constraint kt_index_job_status_ck
  check (status in ('pending', 'running', 'succeeded', 'failed', 'canceled'));
```

索引：

```sql
create index idx_kt_index_job_document
  on kt_document_index_job (document_id, created_at desc);

create index idx_kt_index_job_status
  on kt_document_index_job (status, created_at);

create index idx_kt_index_job_trace
  on kt_document_index_job (trace_id);
```

## 7. 对象存储路径

### 7.1 本地存储

默认路径：

```text
{localRoot}/files/{workspace_id}/{project_id_or_global}/{document_id}/{version}/{safe_file_name}
```

示例：

```text
./data/knowledge/files/ws_001/proj_erp/doc_001/v1/order-approval.md
```

### 7.2 MinIO/S3

对象 key：

```text
knowledge/files/{workspace_id}/{project_id_or_global}/{document_id}/{version}/{safe_file_name}
```

metadata：

- `document_id`
- `workspace_id`
- `project_id`
- `checksum`
- `mime_type`

## 8. 配置模型

`config.example.yaml` 必须包含：

```yaml
database:
  url: jdbc:postgresql://localhost:5432/aidp
  username: aidp
  password: aidp

knowledge:
  storage:
    provider: local
    localRoot: ./data/knowledge
  vectorStore:
    provider: pgvector
  embedding:
    provider: mock
    model: mock-embedding-v1
    dimension: 384
  chunking:
    defaultChunkSize: 800
    defaultOverlap: 120
    maxChunkSize: 1600
  search:
    defaultTopK: 8
    maxTopK: 50
    keywordWeight: 0.25
    vectorWeight: 0.60
    scopeBoostWeight: 0.10
    freshnessBoostWeight: 0.05
  upload:
    maxFileSizeMb: 50
```

## 9. 数据隔离规则

### 9.1 写入

- 所有文档必须写入 `workspace_id`。
- `visibility=project` 必须写入 `project_id`。
- `visibility=workspace` 可以没有 `project_id`。
- `visibility=global` 只能由管理员创建。

### 9.2 检索

检索条件必须始终包含：

```text
deleted_at is null
and (
  visibility = 'global'
  or (visibility = 'workspace' and workspace_id = :workspace_id)
  or (visibility = 'project' and workspace_id = :workspace_id and project_id = :project_id)
)
```

### 9.3 读取 chunk

通过 `chunk_id` 读取时也必须 join document 或使用 chunk 冗余 scope 字段校验权限，不能只按 ID 返回。

## 10. 数据库迁移计划

推荐迁移文件：

```text
V1__create_knowledge_document.sql
V2__create_knowledge_chunk.sql
V3__create_knowledge_index_job.sql
V4__enable_pgvector_optional.sql
V5__create_keyword_search_indexes.sql
```

MVP 如果不确定目标数据库是否启用 PGVector，可以拆成两种 profile：

- `postgres-basic`
- `postgres-pgvector`

## 11. 数据保留策略

- 软删除文档默认保留 30 天。
- 索引任务日志默认保留 90 天。
- 原始文件默认随文档软删除保留，purge 后物理删除。
- chunk 可在 purge 时物理删除。

## 12. 备份与恢复

备份必须包含：

- PostgreSQL 表。
- 对象存储文件。
- 配置文件。

恢复后必须支持：

- 文档列表可见。
- 已索引 chunk 可检索。
- 如果向量索引损坏，可通过 reindex 重建。
