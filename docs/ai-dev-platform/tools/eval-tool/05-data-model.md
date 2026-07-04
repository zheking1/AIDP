# eval-tool 数据模型

## 1. eval_dataset

字段：`id`、`workspace_id`、`project_id`、`name`、`description`、`tags`、`created_by`、`created_at`。

## 2. eval_case

字段：

- `id`
- `dataset_id`
- `name`
- `target_type`
- `target_config`
- `input`
- `expected`
- `scorers`
- `tags`
- `enabled`
- `created_at`

## 3. eval_run

字段：

- `id`
- `dataset_id`
- `status`
- `target_version`
- `config_snapshot`
- `metrics`
- `started_at`
- `finished_at`

## 4. eval_case_result

字段：

- `id`
- `run_id`
- `case_id`
- `status`
- `input`
- `output`
- `error`
- `scores`
- `latency_ms`
- `trace_id`
- `created_at`

## 5. 配置

```yaml
server:
  port: 18090

eval:
  defaultTimeoutMs: 30000
  maxParallelism: 4
  storeFullOutput: true
```

## 6. 迁移

`V1__eval_dataset.sql`、`V2__eval_case.sql`、`V3__eval_run.sql`、`V4__eval_case_result.sql`。
