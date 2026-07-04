# asset-tool 文档索引

`asset-tool` 负责代码资产和模板管理能力，包括代码片段、配置模板、命令模板、设计模式的存储、检索和复用。它既可以独立运行，也可以被 `aidp-controller` 安装后作为 MCP Skill 能力来源。

## 1. 必读文档

| 文档 | 内容 |
|---|---|
| [01-requirements.md](./01-requirements.md) | 需求说明、用户场景、功能范围、MVP 边界 |
| [02-architecture.md](./02-architecture.md) | 工具内部架构、运行模式、部署形态 |
| [03-module-design.md](./03-module-design.md) | 模块划分、服务职责、配置项 |
| [04-api-capabilities.md](./04-api-capabilities.md) | HTTP API、工具协议接口、capability |
| [05-data-model.md](./05-data-model.md) | PostgreSQL 表、索引、数据隔离 |
| [06-development-plan.md](./06-development-plan.md) | 里程碑、AI 开发任务拆分 |
| [07-testing-acceptance.md](./07-testing-acceptance.md) | 测试和验收标准 |
| [AI_IMPLEMENTATION.md](./AI_IMPLEMENTATION.md) | 给 AI 编码工具的实施提示 |

## 2. 工具定位

`asset-tool` 的核心职责：

- 代码片段（snippet）存储和检索。
- 配置模板（config）管理。
- 命令模板（command）管理。
- 设计模式（pattern）管理。
- 关键词和语义检索。
- 模板渲染。
- 工作区和项目级权限隔离。

## 3. MVP Capability

| capability | 权限 | 说明 |
|---|---|---|
| `asset.create` | `asset:write` | 创建资产 |
| `asset.update` | `asset:write` | 更新资产 |
| `asset.delete` | `asset:delete` | 删除资产 |
| `asset.get` | `asset:read` | 查询资产详情 |
| `asset.search` | `asset:search` | 检索资产 |
| `asset.list` | `asset:read` | 列出资产 |
| `asset.render` | `asset:read` | 渲染模板 |

## 4. 完成定义

该工具实现完成后必须满足：

- 可 standalone 启动。
- 可被 `aidp-controller` 托管安装。
- `/tool/manifest` 和 `/tool/capabilities` 可被 controller 解析。
- `/tool/invoke` 可调用 `asset.search`。
- 支持 snippet/config/command/pattern 四种资产类型。
- 检索结果包含来源引用。
- 项目 A 不能搜索项目 B 的私有资产。
