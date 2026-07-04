# memory-tool 数据模型

## 1. 数据库选择

MVP 使用 PostgreSQL。原因：

- 记忆数据强依赖结构化过滤和事务。
- 可以用 `jsonb` 保存灵活元数据。
- 可以用全文索引支持关键词检索。
- 后续可启用 `pgvector`，无需单独部署向量数据库。

## 2. 表：memory_item

```sql
create table memory_item (
  id varchar(64) primary key,
  tenant_id varchar(64),
  workspace_id varchar(64),
  project_id varchar(64),
  session_id varchar(64),
  scope varchar(32) not null,
  memory_type varchar(64) not null,
  memory_key varchar(128),
  title varchar(255) not null,
  content text not null,
  summary text,
  content_hash varchar(64) not null,
  tags jsonb not null default '[]',
  importance integer not null default 50,
  confidence numeric(4,3) not null default 0.800,
  status varchar(32) not null default 'pending_review',
  source_type varchar(64) not null default 'manual',
  source_ref varchar(512),
  metadata jsonb not null default '{}',
  expires_at timestamptz,
  reviewed_at timestamptz,
  reviewed_by varchar(64),
  created_by varchar(64),
  updated_by varchar(64),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

### 2.1 约束

```sql
alter table memory_item
  add constraint ck_memory_scope
  check (scope in ('global', 'workspace', 'project', 'session'));

alter table memory_item
  add constraint ck_memory_status
  check (status in ('pending_review', 'approved', 'rejected', 'expired', 'archived'));

alter table memory_item
  add constraint ck_memory_importance
  check (importance >= 0 and importance <= 100);

alter table memory_item
  add constraint ck_memory_confidence
  check (confidence >= 0 and confidence <= 1);
```

### 2.2 索引

```sql
create index idx_memory_scope
  on memory_item (tenant_id, workspace_id, project_id, session_id, scope);

create index idx_memory_type_status
  on memory_item (workspace_id, project_id, memory_type, status);

create index idx_memory_expiry
  on memory_item (expires_at)
  where expires_at is not null;

create index idx_memory_importance
  on memory_item (workspace_id, project_id, importance desc);

create unique index uq_memory_key
  on memory_item (coalesce(workspace_id, ''), coalesce(project_id, ''), coalesce(session_id, ''), scope, memory_key)
  where memory_key is not null;

create unique index uq_memory_hash
  on memory_item (coalesce(workspace_id, ''), coalesce(project_id, ''), coalesce(session_id, ''), scope, content_hash)
  where memory_key is null;
```

全文检索：

```sql
alter table memory_item
  add column search_vector tsvector;

create index idx_memory_search_vector
  on memory_item using gin(search_vector);
```

应用层在写入时维护：

```text
search_vector = to_tsvector('simple', title || ' ' || coalesce(summary, '') || ' ' || content)
```

## 3. 表：session_summary

```sql
create table session_summary (
  id varchar(64) primary key,
  tenant_id varchar(64),
  workspace_id varchar(64) not null,
  project_id varchar(64),
  session_id varchar(64) not null,
  version integer not null,
  title varchar(255) not null,
  summary text not null,
  decisions jsonb not null default '[]',
  changed_files jsonb not null default '[]',
  next_steps jsonb not null default '[]',
  risks jsonb not null default '[]',
  metadata jsonb not null default '{}',
  active boolean not null default true,
  token_estimate integer not null default 0,
  created_by varchar(64),
  created_at timestamptz not null default now()
);
```

索引：

```sql
create unique index uq_session_summary_version
  on session_summary (workspace_id, project_id, session_id, version);

create unique index uq_session_summary_active
  on session_summary (workspace_id, project_id, session_id)
  where active = true;
```

保存新摘要时：

1. 查询当前最大 version。
2. 将旧 active 置为 false。
3. 插入新 version，active=true。

## 4. 表：context_package_log

记录上下文包生成历史，用于调试和审计，不要求长期保存。

```sql
create table context_package_log (
  id varchar(64) primary key,
  trace_id varchar(128),
  tenant_id varchar(64),
  workspace_id varchar(64) not null,
  project_id varchar(64),
  session_id varchar(64),
  task text not null,
  max_tokens integer not null,
  token_estimate integer not null,
  selected_memory_ids jsonb not null default '[]',
  omitted_memory_ids jsonb not null default '[]',
  rendered_markdown text,
  created_by varchar(64),
  created_at timestamptz not null default now()
);
```

索引：

```sql
create index idx_context_package_scope
  on context_package_log (workspace_id, project_id, session_id, created_at desc);
```

## 5. 表：memory_event

审计所有写入、审核、过期、删除动作。

```sql
create table memory_event (
  id varchar(64) primary key,
  trace_id varchar(128),
  memory_id varchar(64),
  event_type varchar(64) not null,
  old_value jsonb,
  new_value jsonb,
  actor_id varchar(64),
  actor_type varchar(32) not null default 'user',
  created_at timestamptz not null default now()
);
```

事件类型：

- `created`
- `updated`
- `approved`
- `rejected`
- `expired`
- `archived`
- `context_selected`

## 6. 可选表：memory_embedding

启用 pgvector 后再创建。

```sql
create table memory_embedding (
  id varchar(64) primary key,
  memory_id varchar(64) not null references memory_item(id) on delete cascade,
  embedding_model varchar(128) not null,
  embedding vector(768) not null,
  content_hash varchar(64) not null,
  created_at timestamptz not null default now()
);
```

## 7. 配置模型

`config.example.yaml`：

```yaml
server:
  port: 18085

database:
  url: jdbc:postgresql://localhost:5432/aidp
  username: aidp
  password: aidp

memory:
  maxContentBytes: 16384
  defaultMaxTokens: 3000
  maxContextTokens: 12000
  aiGeneratedDefaultStatus: pending_review
  includePendingByDefault: false
  keywordSearch:
    enabled: true
  vectorSearch:
    enabled: false
    provider: pgvector
    embeddingModel: bge-small-zh

retention:
  contextPackageLogDays: 30
```

## 8. 数据隔离策略

- 所有查询必须从 `RequestContext` 派生 scope，不允许调用方直接传任意 `workspace_id` 覆盖上下文。
- `global` 记忆只允许平台管理员写入。
- `workspace` 记忆只允许 workspace 成员读取。
- `project` 记忆只允许项目成员读取。
- `session` 记忆必须同时匹配 `session_id`。
- `memory.get_context` 默认不跨 project 合并记忆。

## 9. 迁移策略

推荐使用 SQL migration；TypeScript 实现可用 Drizzle migration，Python 实现可用 Alembic：

| 版本 | 内容 |
|---|---|
| `V1__memory_item.sql` | 创建 `memory_item` 和基础索引 |
| `V2__session_summary.sql` | 创建 `session_summary` |
| `V3__context_package_log.sql` | 创建上下文日志 |
| `V4__memory_event.sql` | 创建审计事件 |
| `V5__memory_search_vector.sql` | 增加全文检索列和索引 |
| `V6__memory_embedding.sql` | 可选 pgvector 支持 |
