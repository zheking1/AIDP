# error-tool 数据模型

## 1. 表：error_case

```sql
create table error_case (
  id varchar(64) primary key,
  tenant_id varchar(64),
  workspace_id varchar(64) not null,
  project_id varchar(64),
  session_id varchar(64),
  source_tool varchar(64),
  source_run_id varchar(128),
  error_type varchar(64) not null,
  title varchar(255) not null,
  raw_log_uri varchar(512),
  raw_log_hash varchar(64),
  normalized_message text,
  fingerprint varchar(128) not null,
  status varchar(32) not null default 'open',
  severity varchar(32) not null default 'error',
  tags jsonb not null default '[]',
  environment jsonb not null default '{}',
  normalized_fields jsonb not null default '{}',
  project_private boolean not null default true,
  occurrence_count integer not null default 1,
  last_seen_at timestamptz not null default now(),
  created_by varchar(64),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

索引：

```sql
create index idx_error_scope on error_case (workspace_id, project_id, status);
create index idx_error_type on error_case (workspace_id, project_id, error_type);
create index idx_error_fingerprint on error_case (workspace_id, project_id, fingerprint);
create index idx_error_last_seen on error_case (workspace_id, project_id, last_seen_at desc);
```

## 2. 表：error_solution

```sql
create table error_solution (
  id varchar(64) primary key,
  error_case_id varchar(64) not null references error_case(id) on delete cascade,
  root_cause text not null,
  fix_steps jsonb not null default '[]',
  changed_files jsonb not null default '[]',
  patch_summary text,
  applicable_versions jsonb not null default '{}',
  risk_notes text,
  related_commit varchar(128),
  verified_count integer not null default 0,
  failed_count integer not null default 0,
  rating numeric(3,2) not null default 0,
  last_verified_at timestamptz,
  created_by varchar(64),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

## 3. 表：error_event

```sql
create table error_event (
  id varchar(64) primary key,
  trace_id varchar(128),
  error_case_id varchar(64) not null,
  event_type varchar(64) not null,
  payload jsonb not null default '{}',
  actor_id varchar(64),
  created_at timestamptz not null default now()
);
```

事件：

- `recorded`
- `searched`
- `solution_linked`
- `resolved`
- `ignored`
- `exported`

## 4. 可选表：error_embedding

```sql
create table error_embedding (
  id varchar(64) primary key,
  error_case_id varchar(64) not null references error_case(id) on delete cascade,
  embedding_model varchar(128) not null,
  embedding vector(768) not null,
  content_hash varchar(64) not null,
  created_at timestamptz not null default now()
);
```

## 5. 原始日志存储路径

本地或 MinIO 路径：

```text
error-logs/{workspace_id}/{project_id}/{yyyy}/{mm}/{error_case_id}.log
```

脱敏后的日志保存。原始未脱敏日志不进入持久化。

## 6. 配置模型

```yaml
server:
  port: 18086

database:
  url: jdbc:postgresql://localhost:5432/aidp

storage:
  provider: local
  localPath: ./data/error-logs
  minio:
    endpoint: http://localhost:9000
    bucket: aidp

error:
  maxRawLogBytes: 10485760
  defaultSearchTopK: 5
  enableVectorSearch: false
  redactPatterns:
    - "(?i)password\\s*=\\s*[^\\s]+"
    - "(?i)token\\s*=\\s*[^\\s]+"
```

## 7. 迁移计划

| 版本 | 内容 |
|---|---|
| `V1__error_case.sql` | 创建错误案例表 |
| `V2__error_solution.sql` | 创建解决方案表 |
| `V3__error_event.sql` | 创建事件表 |
| `V4__error_fulltext.sql` | 增加全文检索 |
| `V5__error_embedding.sql` | 可选向量检索 |
