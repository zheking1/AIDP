# quality-tool 数据模型设计

## 1. 表清单

表名前缀统一为 `qt_`。

| 表 | 用途 | MVP |
|---|---|---|
| `qt_quality_ruleset` | 质量规则集 | 是 |
| `qt_quality_result` | 检查结果 | 是 |
| `qt_quality_issue` | 结构化问题 | 是 |

## 2. `qt_quality_ruleset`

```sql
create table qt_quality_ruleset (
  id uuid primary key,
  workspace_id varchar(128),
  project_id varchar(128),
  ruleset_key varchar(128) not null,
  name varchar(256) not null,
  project_type varchar(128) not null,
  visibility varchar(32) not null default 'global',
  config jsonb not null,
  enabled boolean not null default true,
  created_by varchar(128),
  created_at timestamptz not null,
  updated_at timestamptz not null,
  unique (workspace_id, project_id, ruleset_key)
);
```

## 3. `qt_quality_result`

```sql
create table qt_quality_result (
  id uuid primary key,
  workspace_id varchar(128) not null,
  project_id varchar(128),
  ruleset_id uuid,
  sandbox_job_id varchar(128),
  passed boolean not null,
  summary jsonb not null default '{}',
  raw_log_object_key text,
  report_object_key text,
  trace_id varchar(128),
  created_by varchar(128),
  created_at timestamptz not null
);
```

索引：

```sql
create index idx_qt_result_scope on qt_quality_result (workspace_id, project_id, created_at desc);
create index idx_qt_result_trace on qt_quality_result (trace_id);
```

## 4. `qt_quality_issue`

```sql
create table qt_quality_issue (
  id uuid primary key,
  result_id uuid not null references qt_quality_result(id),
  workspace_id varchar(128) not null,
  project_id varchar(128),
  severity varchar(32) not null,
  check_type varchar(64) not null,
  rule_id varchar(128),
  file_path text,
  line int,
  column_no int,
  message text not null,
  raw_message text,
  suggested_fix text,
  source varchar(128),
  fingerprint varchar(128),
  metadata jsonb not null default '{}',
  created_at timestamptz not null
);
```

索引：

```sql
create index idx_qt_issue_result on qt_quality_issue (result_id);
create index idx_qt_issue_scope on qt_quality_issue (workspace_id, project_id);
create index idx_qt_issue_fingerprint on qt_quality_issue (fingerprint);
```

## 5. 对象存储路径

```text
quality/results/{workspace_id}/{result_id}/raw.log
quality/results/{workspace_id}/{result_id}/report.json
```

## 6. 配置模型

```yaml
quality:
  sandbox:
    endpoint: http://sandbox-tool:8080
    timeoutSeconds: 900
  parsers:
    maxLogSizeMb: 20
  rulesets:
    builtinPath: ./rulesets
```

## 7. 数据隔离

查询 result 和 issue 时必须按以下范围过滤：

```text
workspace_id = :workspace_id
and (project_id is null or project_id = :project_id)
```

