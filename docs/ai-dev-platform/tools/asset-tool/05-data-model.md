# asset-tool 数据模型设计

## 1. 数据存储范围

`asset-tool` 管理自己的业务数据。controller 只保存工具注册、capability 和调用审计，不直接读写本工具业务表。

默认数据库：

- PostgreSQL 15+
- migration 管理迁移，Python 默认纯 SQL migration

## 2. 表清单

| 表 | 用途 | MVP |
|---|---|---|
| `at_asset` | 资产元数据和内容 | 是 |
| `at_asset_tag` | 资产标签 | 是 |

表名前缀 `at_` 用于避免与 controller 或其它工具冲突。

## 3. 枚举定义

### 3.1 asset_type

```text
snippet
config
command
pattern
```

### 3.2 visibility

```text
global
workspace
project
```

## 4. `at_asset`

用途：保存资产元数据和内容。

DDL：

```sql
create table at_asset (
  id uuid primary key,
  workspace_id varchar(128) not null,
  project_id varchar(128),
  title varchar(512) not null,
  asset_type varchar(32) not null,
  language varchar(64),
  format varchar(64),
  visibility varchar(32) not null,
  content text not null,
  description text,
  variables jsonb not null default '{}',
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
alter table at_asset
  add constraint at_asset_type_ck
  check (asset_type in ('snippet', 'config', 'command', 'pattern'));

alter table at_asset
  add constraint at_asset_visibility_ck
  check (visibility in ('global', 'workspace', 'project'));

alter table at_asset
  add constraint at_asset_project_visibility_ck
  check (
    (visibility = 'project' and project_id is not null)
    or visibility in ('global', 'workspace')
  );
```

索引：

```sql
create index idx_at_asset_scope
  on at_asset (workspace_id, project_id, visibility)
  where deleted_at is null;

create index idx_at_asset_type
  on at_asset (asset_type)
  where deleted_at is null;

create index idx_at_asset_language
  on at_asset (language)
  where deleted_at is null;

create index idx_at_asset_metadata
  on at_asset using gin (metadata);
```

全文检索索引：

```sql
create index idx_at_asset_content_tsv
  on at_asset using gin (to_tsvector('english', content));

create index idx_at_asset_title_tsv
  on at_asset using gin (to_tsvector('english', title));
```

## 5. `at_asset_tag`

用途：保存资产标签，支持标签检索。

DDL：

```sql
create table at_asset_tag (
  id uuid primary key,
  asset_id uuid not null references at_asset(id),
  tag varchar(128) not null,
  created_at timestamptz not null,
  unique (asset_id, tag)
);
```

索引：

```sql
create index idx_at_asset_tag_asset
  on at_asset_tag (asset_id);

create index idx_at_asset_tag_tag
  on at_asset_tag (tag);
```

## 6. 数据隔离规则

### 6.1 写入

- 所有资产必须写入 `workspace_id`。
- `visibility=project` 必须写入 `project_id`。
- `visibility=workspace` 可以没有 `project_id`。
- `visibility=global` 只能由管理员创建。

### 6.2 检索

检索条件必须始终包含：

```text
deleted_at is null
and (
  visibility = 'global'
  or (visibility = 'workspace' and workspace_id = :workspace_id)
  or (visibility = 'project' and workspace_id = :workspace_id and project_id = :project_id)
)
```

## 7. 数据库迁移计划

推荐迁移文件：

```text
V1__create_asset.sql
V2__create_asset_tag.sql
V3__create_asset_search_indexes.sql
```

## 8. 数据保留策略

- 软删除资产默认保留 30 天。
- purge 后物理删除资产和标签。
