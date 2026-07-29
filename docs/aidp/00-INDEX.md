# AIDP (AI DevOps Platform) 项目文档索引

## 平台概述

AIDP 是一个 AI DevOps Platform，提供 AI 辅助的代码开发、知识管理、文档索引、代码质量检查等能力。
平台由 1 个中央调度器（Controller）+ 8 个微服务工具组成。

### 架构速览
```
┌─────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  code-index │   │  skill-router │   │knowledge-tool │   │  memory-tool │
│  (18086)    │   │  (8788)       │   │  (18081)      │   │  (18085)     │
└──────┬──────┘   └──────┬───────┘   └──────┬───────┘   └──────┬──────┘
       └────────────┬─────┴─────────┬───────┴───────────┬────────┘
                    │               │                   │
              ┌─────┴───────────────┴───────────────────┴─────┐
              │          aidp-controller (8883)                │
              │   中央调度器 / API 网关 / MCP 端点             │
              └─────┬───────────────┬───────────────────┬─────┘
                    │               │                   │
       ┌────────────┴───┐   ┌──────┴───────┐   ┌──────┴───────┐
       │  doc-index     │   │sandbox-tool  │   │quality-tool  │
       │  (18087)       │   │  (18083)     │   │  (18084)     │
       └────────────────┘   └──────────────┘   └──────────────┘
```

### 技术栈
| 类别 | 技术 |
|------|------|
| 后端框架 | FastAPI (Python 3.13) |
| 数据库 | PostgreSQL 16 + pgvector / SQLite |
| 前端 | Vue 3 + Element Plus + Pinia |
| MCP 协议 | FastMCP (streamable-http) |
| 部署 | Docker + docker-compose / NAS (192.168.0.100) |
| LLM | DeepSeek / GLM / ERNIE (via BaiduBCE) |
| Embedding | BGE-M3 (SiliconFlow, 1024-dim) |
| Web Server | Uvicorn (async) |
| ORM | SQLAlchemy 2.0 (async) |

---

## 文档导航

### 快速入口
| 文档 | 说明 |
|------|------|
| [system-reference.md](system-reference.md) | **系统参考手册** — 12 个模块的完整设计、流程、API |

### 平台级文档
| 文档 | 说明 |
|------|------|
| [01-overview.md](01-platform/01-overview.md) | AIDP 项目总览 |
| [02-architecture.md](01-platform/02-architecture.md) | 整体架构设计 |
| [03-communication.md](01-platform/03-communication.md) | 组件间通信机制 |
| [04-mcp-protocol.md](01-platform/04-mcp-protocol.md) | MCP 工具协议规范 |
| [05-tech-stack.md](01-platform/05-tech-stack.md) | 全平台技术栈清单 |
| [06-deployment.md](01-platform/06-deployment.md) | 部署架构 |
| [07-init-flow.md](01-platform/07-init-flow.md) | aidp init 完整流程 |
| [08-verify-flow.md](01-platform/08-verify-flow.md) | 初始化自检机制 |
| [09-authentication.md](01-platform/09-authentication.md) | 认证体系 |
| [10-model-management.md](01-platform/10-model-management.md) | 统一模型管理 |

### Controller
| 文档 | 说明 |
|------|------|
| [01-overview.md](02-controller/01-overview.md) | Controller 总览 |
| [02-api-index.md](02-controller/02-api-index.md) | 全部 API 端点索引 |
| [03-module-system.md](02-controller/03-module-system.md) | 模块系统设计 |
| [04-context-pipeline.md](02-controller/04-context-pipeline.md) | 5 阶段上下文管道 |
| [05-tool-registry.md](02-controller/05-tool-registry.md) | 工具注册/调用 |
| [06-database.md](02-controller/06-database.md) | 数据库设计 |
| [07-project-management.md](02-controller/07-project-management.md) | 项目管理 |
| [08-document-classification.md](02-controller/08-document-classification.md) | 文档自动分类 |
| [09-semantic-search.md](02-controller/09-semantic-search.md) | 语义搜索 |
| [10-config.md](02-controller/10-config.md) | 配置项 |
| [11-mcp-server.md](02-controller/11-mcp-server.md) | MCP 工具详细设计 |

### 各工具
| 工具 | 文档目录 |
|------|---------|
| code-index | [03-code-index/](03-code-index/) |
| skill-router | [04-skill-router/](04-skill-router/) |
| knowledge-tool | [05-knowledge-tool/](05-knowledge-tool/) |
| memory-tool | [06-memory-tool/](06-memory-tool/) |
| doc-index | [07-doc-index/](07-doc-index/) |
| sandbox-tool | [09-sandbox-tool/](09-sandbox-tool/) |
| quality-tool | [10-quality-tool/](10-quality-tool/) |

### 三层文件索引系统
| 文档 | 说明 |
|------|------|
| [01-overview.md](09-file-indexing/01-overview.md) | 三层索引系统概述 |
| [02-layer1-git-hook.md](09-file-indexing/02-layer1-git-hook.md) | Layer 1 — Git Post-Commit Hook |
| [03-layer2-agent.md](09-file-indexing/03-layer2-agent.md) | Layer 2 — Agent MCP index_changes |
| [04-layer3-file-watcher.md](09-file-indexing/04-layer3-file-watcher.md) | Layer 3 — file_watcher 实时监控 |
| [05-integration-guide.md](09-file-indexing/05-integration-guide.md) | Agent/开发者集成指南 |
| [06-auto-install.md](09-file-indexing/06-auto-install.md) | 本地脚本自动安装（零手动） |

### 前端
| 文档 | 说明 |
|------|------|
| [01-overview.md](08-web-ui/01-overview.md) | 前端技术栈 |
| [02-architecture.md](08-web-ui/02-architecture.md) | 前端架构 |
| [03-pages/](08-web-ui/pages/) | 页面详细设计 |
| [04-components.md](08-web-ui/04-components.md) | 公共组件 |
| [05-api-layer.md](08-web-ui/05-api-layer.md) | API 层设计 |
| [06-state.md](08-web-ui/06-state.md) | 状态管理 |
| [07-styles.md](08-web-ui/07-styles.md) | 样式规范 |

### 开发指南
| 文档 | 说明 |
|------|------|
| [01-workflow.md](11-development/01-workflow.md) | 开发流程 |
| [02-code-style.md](11-development/02-code-style.md) | 编码规范 |
| [03-testing.md](11-development/03-testing.md) | 测试规范 |

### 附录
| 文档 | 说明 |
|------|------|
| [01-known-issues.md](12-appendix/01-known-issues.md) | 已知问题清单 |
| [02-glossary.md](12-appendix/02-glossary.md) | 术语表 |
| [03-port-mapping.md](12-appendix/03-port-mapping.md) | 服务端口表 |
| [04-db-relationships.md](12-appendix/04-db-relationships.md) | 数据库 ER 关系图 |
| [05-quick-ref.md](12-appendix/05-quick-ref.md) | 常用命令速查 |