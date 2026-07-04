# sandbox-tool 数据模型设计

## 1. 存储范围

`sandbox-tool` 管理执行任务、日志摘要、产物和清理状态。日志全文和产物文件保存到对象存储或本地文件系统。

表名前缀统一为 `st_`。

## 2. 表清单

| 表 | 用途 | MVP |
|---|---|---|
| `st_sandbox_job` | 执行任务主表 | 是 |
| `st_sandbox_log` | 日志摘要和 URI | 是 |
| `st_sandbox_artifact` | 产物记录 | 是 |
| `st_sandbox_cleanup_task` | 清理重试 | 增强 |
| `st_image_policy` | 镜像策略 | 增强，MVP 可配置文件 |

## 3. 枚举

### 3.1 job_type

```text
shell
python
sql_validate
node_build
python_test
generic
```

### 3.2 job_status

```text
pending
running
succeeded
failed
timeout
canceled
lost
```

### 3.3 network_mode

```text
none
limited
default
```

MVP 默认只允许 `none`。

## 4. `st_sandbox_job`

```sql
create table st_sandbox_job (
  id uuid primary key,
  workspace_id varchar(128) not null,
  project_id varchar(128),
  session_id varchar(128),
  job_type varchar(64) not null,
  image varchar(256) not null,
  command jsonb not null,
  environment jsonb not null default '{}',
  input_object_key text,
  status varchar(32) not null,
  exit_code int,
  timeout_seconds int not null,
  resource_limits jsonb not null default '{}',
  network_mode varchar(32) not null default 'none',
  stdout_object_key text,
  stderr_object_key text,
  resource_usage jsonb not null default '{}',
  failure_summary text,
  error_code varchar(128),
  error_message text,
  trace_id varchar(128),
  created_by varchar(128),
  created_at timestamptz not null,
  started_at timestamptz,
  finished_at timestamptz
);
```

索引：

```sql
create index idx_st_job_scope on st_sandbox_job (workspace_id, project_id, created_at desc);
create index idx_st_job_status on st_sandbox_job (status, created_at);
create index idx_st_job_trace on st_sandbox_job (trace_id);
```

## 5. `st_sandbox_log`

```sql
create table st_sandbox_log (
  id uuid primary key,
  job_id uuid not null references st_sandbox_job(id),
  stream varchar(32) not null,
  object_key text,
  summary text,
  truncated boolean not null default false,
  size_bytes bigint,
  created_at timestamptz not null,
  unique (job_id, stream)
);
```

`stream`：

```text
stdout
stderr
combined
```

## 6. `st_sandbox_artifact`

```sql
create table st_sandbox_artifact (
  id uuid primary key,
  job_id uuid not null references st_sandbox_job(id),
  artifact_type varchar(64) not null,
  file_name varchar(512) not null,
  object_key text not null,
  file_size bigint not null,
  checksum varchar(128),
  metadata jsonb not null default '{}',
  created_at timestamptz not null
);
```

索引：

```sql
create index idx_st_artifact_job on st_sandbox_artifact (job_id);
```

## 7. 对象存储路径

工作目录不暴露给外部，只保存日志和产物：

```text
sandbox/jobs/{workspace_id}/{job_id}/logs/stdout.log
sandbox/jobs/{workspace_id}/{job_id}/logs/stderr.log
sandbox/jobs/{workspace_id}/{job_id}/artifacts/{artifact_id}/{file_name}
```

## 8. 配置模型

```yaml
sandbox:
  runtime:
    provider: docker
    endpoint: unix:///var/run/docker.sock
  storage:
    provider: local
    localRoot: ./data/sandbox
  security:
    defaultNetwork: none
    allowPrivileged: false
    allowLatestTag: false
    allowedImages:
      - aidp/shell:ubuntu-22.04
      - aidp/python:3.12
      - aidp/node:20
      - aidp/python:3.12
      - aidp/postgres-test:16
  limits:
    maxTimeoutSeconds: 900
    maxMemoryMb: 4096
    maxCpu: 2
    maxDiskMb: 10240
    maxLogMb: 20
    maxArtifactMb: 200
```

## 9. 数据保留策略

- job 记录保留 90 天。
- 日志默认保留 30 天。
- 产物默认保留 7 天。
- failed job 的日志可保留更久，默认 30 天。

## 10. 重启恢复

服务启动时必须扫描 `running` 任务：

- 如果容器还在运行，可继续跟踪或标记为 running。
- 如果容器不存在，标记为 `lost`。
- 对应临时目录进入清理队列。
