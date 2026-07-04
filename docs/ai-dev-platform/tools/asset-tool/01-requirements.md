# asset-tool 需求说明

## 1. 背景

`asset-tool` 是 AI 编程平台的代码资产管理工具。它负责把可复用的代码片段、配置模板、命令模板、设计模式等资料存储并提供检索能力，通过统一工具协议提供给 `aidp-controller` 和 MCP Agent 调用。

在完整平台中，`asset-tool` 与 `knowledge-tool` 互补。`knowledge-tool` 检索文档知识，`asset-tool` 检索可直接复用的代码资产。

## 2. 产品目标

### 2.1 核心目标

- 提供代码片段、配置模板、命令模板、设计模式的 CRUD。
- 支持独立运行，用户可以只部署 `asset-tool` 当作私有代码资产库。
- 支持被 `aidp-controller` 托管，能力可以被注册为 MCP Skill。
- 支持工作区和项目级权限隔离。
- 检索结果必须提供可追溯引用。
- MVP 优先支持关键词检索，后续支持语义检索。

### 2.2 非目标

MVP 不实现以下能力：

- 不做完整代码编辑器。
- 不做复杂代码分析。
- 不做跨租户公共资产市场。
- 不默认强依赖外部向量数据库。
- 不直接负责 AI 生成代码，只负责提供可复用资产。

## 3. 用户角色

| 角色 | 使用方式 | 关键诉求 |
|---|---|---|
| 个人开发者 | 独立启动工具，积累代码片段和模板 | 快速检索，不要复杂部署 |
| 团队管理员 | 通过 controller 安装工具，配置项目资产库 | 权限隔离、可维护、可审计 |
| AI Agent | 通过 MCP Skill 或 `/tool/invoke` 调用检索能力 | 稳定输入输出、引用来源、低延迟 |

## 4. 使用场景

### 4.1 代码片段检索

用户积累常用代码片段（如 FastAPI 路由模板、SQL 查询模式、错误处理模式）。AI Agent 在编码前调用 `asset.search`，检索当前任务相关代码片段。

验收口径：

- 可以按 `asset_type=snippet` 和 `language` 过滤。
- 返回片段必须包含标题、代码内容和来源。
- 同一查询下，关键词匹配优先返回。

### 4.2 配置模板检索

用户存储常用配置文件模板（如 Docker Compose 模板、nginx 配置、CI/CD 配置）。AI Agent 需要生成配置时检索相关模板。

验收口径：

- 可以按 `asset_type=config` 和 `format` 过滤。
- 返回模板必须包含配置内容和变量说明。

### 4.3 命令模板检索

用户存储常用命令模板（如 Docker 命令、git 命令、部署命令）。AI Agent 需要执行命令时检索相关模板。

验收口径：

- 可以按 `asset_type=command` 过滤。
- 返回命令必须包含命令内容和说明。

### 4.4 设计模式检索

用户存储项目中使用的设计模式（如单例模式、工厂模式、中间件模式）。AI Agent 需要实现类似功能时检索相关模式。

验收口径：

- 可以按 `asset_type=pattern` 和 `language` 过滤。
- 返回模式必须包含模式描述和示例代码。

## 5. 功能需求

### 5.1 资产 CRUD

系统必须支持创建、读取、更新、删除资产：

- 标题。
- 资产类型（snippet/config/command/pattern）。
- 所属工作区。
- 所属项目，可为空，表示工作区公共资产。
- 可见性（global/workspace/project）。
- 标签。
- 语言/格式。
- 内容。
- 元数据 JSON。

### 5.2 资产检索

必须提供 `asset.search` capability。

检索能力必须支持：

- query（关键词）。
- asset_type filter。
- language filter。
- tag filter。
- workspace filter。
- project filter。
- visibility filter。
- search_mode：`keyword`（MVP）、`vector`（增强）。
- top_k。

默认检索流程：

```text
权限过滤
  -> metadata filter
  -> keyword search
  -> score merge
  -> source refs
```

### 5.3 模板渲染

必须提供 `asset.render` capability。

渲染能力必须支持：

- asset_id。
- variables（JSON）。

渲染流程：

```text
获取资产内容
  -> 解析模板变量
  -> 替换变量
  -> 返回渲染结果
```

### 5.4 权限隔离

权限规则：

- `visibility=global`：平台公共资产，可被所有工作区搜索，默认仅管理员可写。
- `visibility=workspace`：工作区共享资产，同一 `workspace_id` 可搜索。
- `visibility=project`：项目私有资产，必须匹配 `workspace_id` 和 `project_id`。

工具内部必须二次校验权限，不能完全信任 controller。

## 6. 非功能需求

### 6.1 性能

MVP 目标：

- 1000 条资产，P95 检索延迟小于 500ms。
- `top_k <= 20` 时响应体默认小于 128KB。

### 6.2 可靠性

- 删除资产必须软删除优先。
- 更新资产不影响正在进行的检索。

### 6.3 可观测性

日志必须包含：

- `trace_id`
- `workspace_id`
- `project_id`
- `asset_id`
- `capability`
- `elapsed_ms`
- `error_code`

### 6.4 安全

- 禁止读取未授权本地路径。
- 上传内容大小必须限制。
- 源代码内容不能出现在错误日志中。

## 7. MVP 验收范围

MVP 完成时必须支持：

- 独立启动 `asset-tool`。
- controller 托管安装。
- `tool.yaml`、`openapi.yaml`、`config.example.yaml`。
- `GET /health`。
- `GET /tool/manifest`。
- `GET /tool/capabilities`。
- `POST /tool/invoke`。
- snippet/config/command/pattern CRUD。
- `asset.search` 关键词检索。
- `asset.render` 模板渲染。
- 跨项目隔离测试通过。
