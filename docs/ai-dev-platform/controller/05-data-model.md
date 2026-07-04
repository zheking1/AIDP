# aidp-controller 数据模型

## 1. workspace/project/session

核心表：

- `tenant`
- `workspace`
- `project`
- `session`
- `user`
- `role`
- `permission`
- `user_workspace_role`

MVP 个人模式可以创建默认 tenant/workspace/user。

## 2. tool_registry

字段：

- `id`
- `workspace_id`
- `name`
- `display_name`
- `version`
- `status`
- `install_mode`
- `base_url`
- `manifest`
- `config`
- `last_health_status`
- `installed_at`
- `updated_at`

## 3. tool_capability

字段：

- `id`
- `tool_id`
- `name`
- `description`
- `endpoint`
- `permission`
- `input_schema`
- `output_schema`
- `timeout_ms`
- `risk_level`
- `enabled`

## 4. tool_invocation

字段：

- `id`
- `trace_id`
- `workspace_id`
- `project_id`
- `session_id`
- `tool_name`
- `capability_name`
- `status`
- `input_summary`
- `output_summary`
- `error_code`
- `error_message`
- `elapsed_ms`
- `created_by`
- `created_at`

## 5. workflow_definition / workflow_run / workflow_step

`workflow_definition` 保存 YAML/JSON 定义。

`workflow_run` 保存一次执行。

`workflow_step` 保存每一步状态、输入、输出、错误和审批状态。

## 6. approval_request

字段：

- `id`
- `workspace_id`
- `project_id`
- `resource_type`
- `resource_id`
- `action`
- `risk_level`
- `status`
- `request_summary`
- `decision_comment`
- `requested_by`
- `decided_by`
- `created_at`
- `decided_at`

## 7. secret_entry

字段：

- `id`
- `workspace_id`
- `project_id`
- `name`
- `scope`
- `encrypted_value`
- `allowed_tools`
- `created_by`
- `created_at`
- `updated_at`

## 8. audit_log

字段：

- `id`
- `trace_id`
- `workspace_id`
- `project_id`
- `actor_type`
- `actor_id`
- `action`
- `resource_type`
- `resource_id`
- `request_summary`
- `response_summary`
- `ip`
- `created_at`

## 9. 迁移策略

推荐 migration 文件：

- `001_workspace.sql`
- `002_auth.sql`
- `003_tool_registry.sql`
- `004_tool_invocation.sql`
- `005_workflow.sql`
- `006_approval.sql`
- `007_secret.sql`
- `008_audit.sql`
