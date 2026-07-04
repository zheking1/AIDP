# AI 编程基础设施平台（AIDP）

Controller + N 个可选工具的私有化 AI 编程平台。

## 架构

```text
aidp-controller + optional tools
```

- Controller: Python + FastAPI + FastMCP
- 工具: Python + FastAPI，可独立运行

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.13 + FastAPI + FastMCP |
| 数据库 | PostgreSQL + pgvector |
| 缓存 | Redis |
| Web UI | Jinja2 + Alpine.js + Tailwind CSS |
| 部署 | Docker Compose |

## 文档

| 文档 | 用途 |
|------|------|
| [INTEGRATED-ARCHITECTURE.md](./INTEGRATED-ARCHITECTURE.md) | 集成架构 |
| [09-technology-stack.md](./09-technology-stack.md) | 技术栈 |
| [08-controller-plus-tools-architecture.md](./08-controller-plus-tools-architecture.md) | 架构 |
| [01-requirements.md](./01-requirements.md) | 需求 |
| [DEVELOPMENT_PROMPT.md](./DEVELOPMENT_PROMPT.md) | AI 开发指南 |
| [common/tool-contract.md](./common/tool-contract.md) | 工具协议 |
| [common/engineering-standards.md](./common/engineering-standards.md) | 工程规范 |
| [tools/README.md](./tools/README.md) | 工具设计 |

## 工具

| 工具 | 用途 | 状态 |
|------|------|------|
| skill-router | 技能路由 | ✅ 已有 |
| knowledge-tool | 文档知识库 | ⏳ 待开发 |
| sandbox-tool | 沙箱执行 | ⏳ 待开发 |
| quality-tool | 质量校验 | ⏳ 待开发 |
| memory-tool | 项目记忆 | ⏳ 待开发 |

## 项目结构

```text
openCode/
├── apps/controller/         # 主服务
├── tools/
│   ├── skill-router/        # 已有
│   ├── knowledge-tool/
│   ├── sandbox-tool/
│   ├── quality-tool/
│   └── memory-tool/
├── packages/sdk/
├── deploy/compose/
├── docs/ai-dev-platform/
└── tests/
```
