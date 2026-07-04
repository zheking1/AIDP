# template-tool 需求说明

## 1. 背景

AI 经常需要初始化 TypeScript 服务模块、Fastify 路由、React 页面、Docker Compose、Nginx 配置、数据库迁移脚本等。如果完全由 AI 从零生成，容易出现目录结构不统一、依赖版本不一致、命名不符合团队规范的问题。

`template-tool` 通过模板包和变量渲染，把成熟结构沉淀成可复用资产。

## 2. 模板类型

| 类型 | 说明 | 示例 |
|---|---|---|
| `project` | 完整项目脚手架 | TypeScript API 服务、React 管理台 |
| `module` | 项目内模块 | RuoYi 子模块、订单服务模块 |
| `component` | UI 或后端组件 | Flutter 页面、Vue 组件 |
| `config` | 配置文件 | Docker Compose、Nginx、pnpm |
| `migration` | 数据库迁移 | Flyway SQL |
| `script` | 工具脚本 | Frida、ADB、Python 批处理 |

## 3. 使用场景

- AI 根据需求选择模板并生成模块。
- 用户上传团队标准模板。
- controller 调用 `template.preview` 给 AI 检查生成文件。
- 渲染后交给 `sandbox-tool` 编译验证。
- 高价值模板可由 `asset-tool` 关联检索。

## 4. 功能需求

### 4.1 模板注册

必须支持上传或引用 Zip 包、解析 `template.yaml`、保存模板名称/类型/版本/变量定义/标签/适用技术栈。模板版本不可覆盖，发布新版本必须新增记录。

### 4.2 模板检索

支持 query、template_type、language/framework、tags、visibility、version。

### 4.3 变量校验

变量 schema 支持 string、number、boolean、enum、array、required、default、regex、min/max、description、secret。

### 4.4 预览与渲染

preview 不生成正式产物，返回文件树、变更摘要、前 N 个文本文件内容。render 生成完整产物，返回 output_uri，可选择写入指定工作目录或仅生成压缩包。

## 5. 非目标

MVP 不做复杂 Cookiecutter 语法，不执行模板内脚本，不自动覆盖用户工作区文件，不直接提交 Git。

## 6. 非功能需求

- 1000 文件以内模板渲染 P95 小于 3 秒。
- 单模板包默认最大 100MB。
- 输出路径必须限制在 job workspace 内。
- secret 变量不得写入日志。

## 7. MVP 验收

- 能注册模板。
- 能检索模板。
- 能校验变量。
- 能预览渲染。
- 能生成 Zip 产物。
- 能防止 `../` 目录穿越。
