# template-tool 数据模型

## 1. template_package

保存模板主信息：`id`、`tenant_id`、`workspace_id`、`project_id`、`name`、`display_name`、`template_type`、`description`、`visibility`、`tags`、`frameworks`、`status`、`created_by`、`created_at`、`updated_at`。

唯一约束：同 workspace 下 `name` 唯一。

## 2. template_version

字段：

- `id`
- `template_id`
- `version`
- `package_object_key`
- `package_checksum`
- `variables`
- `manifest`
- `file_count`
- `unpacked_size_bytes`
- `status`
- `published_at`
- `created_at`

唯一约束：`template_id + version`。

## 3. template_render_job

字段：

- `id`
- `workspace_id`
- `project_id`
- `template_id`
- `template_version_id`
- `variables`
- `output_mode`
- `output_uri`
- `status`
- `file_count`
- `warnings`
- `error_message`
- `created_by`
- `created_at`
- `finished_at`

## 4. 对象存储路径

```text
templates/{workspace_id}/{template_name}/{version}/package.zip
renders/{workspace_id}/{project_id}/{render_job_id}/output.zip
```

## 5. 配置模型

```yaml
server:
  port: 18087

template:
  maxPackageBytes: 104857600
  maxFileCount: 5000
  maxPreviewFiles: 20
  maxPreviewBytesPerFile: 20000
  allowOverwrite: false

storage:
  provider: local
  localPath: ./data/templates
```

## 6. 迁移计划

| 版本 | 内容 |
|---|---|
| `V1__template_package.sql` | 模板主表 |
| `V2__template_version.sql` | 模板版本 |
| `V3__template_render_job.sql` | 渲染任务 |
| `V4__template_indexes.sql` | 检索索引 |
