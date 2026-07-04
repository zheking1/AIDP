# knowledge-tool 文档索引

`knowledge-tool` 负责文档知识库能力，包括文档上传、解析、切片、向量化、索引和检索。它既可以独立运行，也可以被 `aidp-controller` 安装后作为 MCP Skill 能力来源。

本目录已经按“AI 可直接开发”的方式拆分为多份详细文档。开发者或 AI 编码工具应按下面顺序阅读。

## 1. 必读文档

| 文档 | 内容 |
|---|---|
| [01-requirements.md](./01-requirements.md) | 需求说明、用户场景、功能范围、非功能需求、MVP 边界 |
| [02-architecture.md](./02-architecture.md) | 工具内部架构、运行模式、部署形态、关键流程、扩展点 |
| [03-module-design.md](./03-module-design.md) | 模块划分、服务职责、状态机、异常处理、配置项 |
| [04-api-capabilities.md](./04-api-capabilities.md) | HTTP API、工具协议接口、capability、请求响应、错误码 |
| [05-data-model.md](./05-data-model.md) | PostgreSQL 表、索引、对象存储路径、配置模型、数据隔离 |
| [06-development-plan.md](./06-development-plan.md) | 里程碑、AI 开发任务拆分、交付物、风险控制 |
| [07-testing-acceptance.md](./07-testing-acceptance.md) | 单元测试、集成测试、端到端测试、性能和安全验收 |
| [AI_IMPLEMENTATION.md](./AI_IMPLEMENTATION.md) | 给 AI 编码工具的实施提示 |

## 2. 工具定位

`knowledge-tool` 的核心职责：

- 文档登记和上传。
- Markdown/TXT/源码文本解析。
- 文档切片。
- embedding 抽象和 mock provider。
- PGVector 或 mock vector store 检索。
- keyword/vector/hybrid search。
- citation 和 source refs。
- 工作区、项目、可见性隔离。

## 3. MVP Capability

| capability | 权限 | 说明 |
|---|---|---|
| `document.create` | `knowledge:write` | 创建文档元数据 |
| `document.upload` | `knowledge:write` | 上传文件并创建文档 |
| `document.index` | `knowledge:index` | 创建索引任务 |
| `document.reindex` | `knowledge:index` | 重建索引 |
| `document.delete` | `knowledge:delete` | 删除文档 |
| `document.get` | `knowledge:read` | 查询文档详情 |
| `knowledge.search` | `knowledge:search` | 检索知识片段 |
| `knowledge.get_chunk` | `knowledge:read` | 获取 chunk 详情 |

## 4. 完成定义

该工具实现完成后必须满足：

- 可 standalone 启动。
- 可被 `aidp-controller` 托管安装。
- `/tool/manifest` 和 `/tool/capabilities` 可被 controller 解析。
- `/tool/invoke` 可调用 `knowledge.search`。
- 上传 Markdown/TXT 后可索引和检索。
- 检索结果包含 `citation_id`、`document_id`、`chunk_id`、版本和来源。
- 项目 A 不能搜索项目 B 的私有文档。
- 无真实 embedding provider 时可使用 mock provider 完成开发和测试。

