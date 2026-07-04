# template-tool AI 实施包

## 1. 目标交付

实现模板工具，支持上传模板、定义变量、渲染模板、预览和下载结果。

## 2. 推荐模块结构

```text
template-tool/
  src/
    server.ts
    api/
      tool-protocol.routes.ts
      health.routes.ts
      templates.routes.ts
      template-render.routes.ts
    services/
      template.service.ts
      template-variable.service.ts
      template-render.service.ts
      template-preview.service.ts
    repository/
      template-package.repository.ts
      template-render-job.repository.ts
```

## 3. 数据库迁移

必须创建：

- `template_package`
- `template_variable`
- `template_render_job`

## 4. API

- `POST /api/templates`
- `GET /api/templates/{id}`
- `POST /api/templates/search`
- `POST /api/templates/{id}/validate`
- `POST /api/templates/{id}/preview`
- `POST /api/templates/{id}/render`
- `GET /api/templates/render-jobs/{id}`

## 5. 核心实现

### TemplateRenderService

必须支持：

- Zip 解压。
- `{{variable}}` 替换。
- 文件名替换。
- 变量缺失检查。
- 渲染结果重新打包。

### TemplateVariableService

变量定义字段：

- name
- type
- required
- default_value
- description
- pattern

## 6. 测试

- 变量校验测试。
- 文本替换测试。
- 文件名替换测试。
- Zip 渲染测试。

## 7. Definition of Done

- 可独立启动。
- 可被 controller 安装。
- 可上传模板。
- 可渲染模板。
- 变量缺失返回结构化错误。
- 渲染结果可下载。
