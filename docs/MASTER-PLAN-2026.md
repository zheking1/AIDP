# AIDP 2026 年综合开发计划总览

## 文档信息

| 属性 | 值 |
|------|-----|
| 版本 | v1.0 |
| 创建日期 | 2026-07-07 |
| 最后更新 | 2026-07-07 |
| 状态 | 进行中 |
| 编写者 | AIDP Team |

---

## 1. 项目愿景

构建一个完整的 **AI 驱动开发平台 (AIDP)**，包含统一的工作区界面和多个专业化工具，为 AI 辅助编程提供基础设施支持。

### 1.1 核心目标

1. **统一工作区**：单点登录、统一的 Web UI 体验
2. **工具生态**：专业化工具各司其职，协同工作
3. **知识管理**：完整的知识库、记忆、资产管理体系
4. **智能路由**：基于意图的技能匹配和任务分发
5. **持续进化**：平台自我学习和改进能力

---

## 2. 系统架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                     AIDP 统一工作区                          │
│                  (Controller + Web UI)                       │
│                          端口: 8883                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  认证服务    │  │  共享服务    │  │    工具管理         │  │
│  │             │  │             │  │                     │  │
│  │ • 用户/角色 │  │ • 模型配置  │  │ • 工具发现         │  │
│  │ • SSO      │  │ • API 密钥  │  │ • 健康监控         │  │
│  │ • 审计日志  │  │ • 系统设置  │  │ • 权限控制         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                      专业化工具层                            │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │ SkillRouter  │ │  Knowledge   │ │    Memory    │        │
│  │   端口: 8788 │ │   端口:18081 │ │   端口:18085 │        │
│  │              │ │              │ │              │        │
│  │ • 技能路由   │ │ • 文档管理   │ │ • 记忆管理   │        │
│  │ • 意图分析   │ │ • 向量搜索   │ │ • 图谱可视化 │        │
│  │ • LLM 编排  │ │ • 知识图谱   │ │ • 上下文包   │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │    Asset     │ │   Sandbox    │ │   Quality    │        │
│  │   端口:18082 │ │   端口:18083 │ │   端口:18084 │        │
│  │              │ │              │ │              │        │
│  │ • 代码模板   │ │ • 代码执行   │ │ • 质量检查   │        │
│  │ • 资产配置   │ │ • 沙箱隔离   │ │ • 安全扫描   │        │
│  │ • 变量渲染   │ │ • 执行历史   │ │ • 报告生成   │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │  Code-Index  │ │ File-Watcher │ │   Evolution  │        │
│  │   端口:18086 │ │   端口:18091 │ │   端口:18089 │        │
│  │              │ │              │ │              │        │
│  │ • AST 索引   │ │ • 文件监控   │ │ • 事件分析   │        │
│  │ • 符号搜索   │ │ • 自动索引   │ │ • 模式提取   │        │
│  │ • 调用追踪   │ │ • 变更检测   │ │ • 系统进化   │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌──────────┐    ┌──────────┐    ┌──────────┐
        │PostgreSQL│    │  Redis   │    │  NAS     │
        │  主数据库 │    │  缓存    │    │  存储    │
        └──────────┘    └──────────┘    └──────────┘
```

---

## 3. 开发阶段总览

### Phase 1: 基础设施完善 ✅ (已完成)

| 任务 | 状态 | 说明 |
|------|------|------|
| Controller 统一 Web UI | ✅ | Workspace + Tab 系统 |
| 用户认证与权限 | ✅ | RBAC、Session、API Key |
| 工具注册与监控 | ✅ | 健康检查、自动发现 |
| SQLite 兼容性 | ✅ | 所有工具支持 SQLite |
| File Watcher 服务 | ✅ | 自动代码索引 |

### Phase 2: Web UI 生产级改造 🚧 (进行中)

| 任务 | 优先级 | 预估工时 | 状态 |
|------|--------|----------|------|
| **Knowledge Tool Web UI** | P0 | 3 周 | 🚧 计划中 |
| **Memory Tool Web UI** | P0 | 2 周 | 🚧 计划中 |
| **Evolution Engine 重构** | P1 | 2 周 | 🚧 计划中 |
| Asset Tool Web UI | P2 | 1 周 | ⏳ 待排期 |
| Quality Tool Web UI | P2 | 3 天 | ⏳ 待排期 |

### Phase 3: 上下文优化管线 🚧 (进行中)

| 任务 | 优先级 | 预估工时 | 状态 |
|------|--------|----------|------|
| Agent Instructions 系统 | P0 | 1 周 | 🚧 开发中 |
| 分段检索管线 (Stage 0-4) | P0 | 2 周 | 🚧 开发中 |
| Intent Analysis 增强 | P0 | 3 天 | 🚧 开发中 |
| MCP 集成优化 | P1 | 1 周 | ⏳ 待排期 |

### Phase 4: 高级功能 ⏳ (待排期)

| 任务 | 优先级 | 预估工时 | 状态 |
|------|--------|----------|------|
| 团队协作功能 | P1 | 2 周 | ⏳ 待排期 |
| 多租户支持 | P1 | 2 周 | ⏳ 待排期 |
| 高级统计分析 | P2 | 1 周 | ⏳ 待排期 |
| 自动化工作流 | P2 | 2 周 | ⏳ 待排期 |

---

## 4. 工具详细状态

### 4.1 已完成工具

| 工具 | Web UI | API | 数据持久化 | 备注 |
|------|--------|-----|-----------|------|
| **SkillRouter** | ✅ 生产级 | ✅ 完整 | ✅ PostgreSQL | 标杆工具 |
| **Controller** | ✅ 生产级 | ✅ 完整 | ✅ PostgreSQL | 统一入口 |
| **Sandbox** | ✅ 完整 | ✅ 完整 | ✅ SQLite | 代码执行 |

### 4.2 需要生产级 Web UI 的工具

| 工具 | 当前 Web UI | 目标 | 关键功能 | 优先级 |
|------|------------|------|---------|--------|
| **Knowledge** | 基础列表 | 生产级 | 文档预览、分块可视化、搜索中心 | P0 |
| **Memory** | 基础 CRUD | 生产级 | 记忆图谱、时间轴、上下文包 | P0 |
| **Asset** | 基础列表 | 完整 | 模板预览、变量配置、资产市场 | P2 |
| **Quality** | 基础表单 | 完整 | 质量报告、历史趋势、规则配置 | P2 |

### 4.3 后台服务工具（无需 Web UI）

| 工具 | 类型 | 说明 |
|------|------|------|
| File Watcher | 后台服务 | 文件监控、自动触发 |
| Code Index | 索引服务 | AST 解析、符号索引 |
| Evolution | 分析服务 | 事件分析、模式提取 |
| Doc Index | 索引服务 | 文档索引、Wiki 生成 |

---

## 5. 详细开发计划

### 5.1 Knowledge Tool Web UI (P0)

**目标**：构建生产级文档知识库管理界面

**核心功能**：
- 文档管理仪表盘（项目/分类/标签视图）
- 文档预览与分块可视化
- 高级搜索中心（语义+关键词）
- 索引状态监控
- 知识图谱（文档关联）

**参考 SkillRouter 功能**：
- 类似 Skill 管理的文档列表
- 类似 Test Bench 的搜索测试
- 类似 Statistics 的索引监控

**文档**：详见 `docs/plans/KNOWLEDGE-WEB-UI-PLAN.md`

---

### 5.2 Memory Tool Web UI (P0)

**目标**：构建生产级记忆管理和可视化界面

**核心功能**：
- 记忆管理器（列表/卡片/图谱视图）
- 记忆图谱可视化（D3.js 力导向图）
- 时间轴视图（记忆演变）
- 上下文包生成器（交互式）
- 记忆审核队列

**参考项目**：
- AgentMemory / MemGPT 的记忆分层
- LLM Memory 的向量检索

**增强功能**：
- 向量搜索（pgvector）
- 记忆合并（相似记忆自动合并）
- 记忆关联推荐

**文档**：详见 `docs/plans/MEMORY-WEB-UI-PLAN.md`

---

### 5.3 Evolution Engine 重构 (P1)

**目标**：实现两级进化系统（项目级 + 系统级）

**核心设计**：
```
项目级进化（用户私有）
    ↓ 提交审核
管理员审核
    ↓ 批准
系统级进化（全平台共享）
    ↓ 版本发布
Evolution v1.2.3
```

**关键功能**：
- 版本管理（创建/发布/回退）
- 管理员审核工作流
- 影响范围分析
- 回退机制（多级）
- 进化效果追踪

**文档**：详见 `docs/plans/EVOLUTION-REFACTOR-PLAN.md`

---

## 6. 技术规范

### 6.1 Web UI 技术标准

| 项目 | 技术 | 说明 |
|------|------|------|
| 前端框架 | Alpine.js 3 | 轻量级响应式框架 |
| CSS 框架 | Tailwind CSS | 原子化 CSS |
| 图表库 | D3.js / Chart.js | 数据可视化 |
| 代码编辑器 | Monaco Editor | VS Code 编辑器核心 |
| 语法高亮 | Prism.js / highlight.js | 代码高亮 |

### 6.2 后端技术标准

| 项目 | 技术 | 说明 |
|------|------|------|
| Web 框架 | FastAPI | Python 异步 Web 框架 |
| 数据库 | PostgreSQL + SQLite | 主从数据库 |
| ORM | SQLAlchemy 2.0 | 异步 ORM |
| 缓存 | Redis | 分布式缓存 |
| 消息队列 | Redis Pub/Sub | 实时通知 |

### 6.3 部署标准

| 项目 | 技术 | 说明 |
|------|------|------|
| 容器化 | Docker + Docker Compose | 服务容器化 |
| 反向代理 | Nginx / Traefik | 负载均衡 |
| 监控 | Prometheus + Grafana | 指标监控 |
| 日志 | ELK Stack / Loki | 日志聚合 |

---

## 7. 已完成工作汇总

### 7.1 已完成的主要功能

#### ✅ 统一 Web UI 平台
- Workspace 工作区布局
- Tab 标签页管理系统
- 侧边栏导航
- 用户认证与授权
- 工具管理与健康监控

#### ✅ 核心工具
- SkillRouter：完整的技能路由和管理
- Sandbox：代码执行沙箱
- Controller：统一入口和管理

#### ✅ 基础设施
- 工具注册与发现机制
- 健康监控与自动重启
- SQLite/PostgreSQL 兼容
- File Watcher 自动索引

### 7.2 已完成的文档

| 文档 | 说明 | 位置 |
|------|------|------|
| DEV-PLAN-V3.md | Instructions-First 分段上下文引擎 | docs/ |
| DEV-PLAN-2026-07-06.md | 近期开发记录 | docs/ |
| UNIFIED_WEB_UI_DESIGN.md | 统一 Web UI 设计 | docs/ |
| MASTER-DEVELOPMENT-PLAN.md | 综合开发计划 | docs/ |

---

## 8. 未完成工作清单

### 8.1 高优先级 (P0)

- [ ] **Knowledge Tool Web UI** - 生产级文档管理界面
- [ ] **Memory Tool Web UI** - 生产级记忆管理界面
- [ ] **Agent Instructions 系统** - 完整的 Stage 0-4 管线
- [ ] **Intent Analysis 增强** - 意图分析扩展

### 8.2 中优先级 (P1)

- [ ] **Evolution Engine 重构** - 两级进化系统
- [ ] **Asset Tool Web UI** - 模板管理界面
- [ ] **Quality Tool Web UI** - 质量报告界面
- [ ] **MCP 集成优化** - 完整的 MCP 协议支持

### 8.3 低优先级 (P2)

- [ ] 团队协作功能
- [ ] 多租户支持
- [ ] 高级统计分析
- [ ] 自动化工作流

---

## 9. 参考文档索引

### 9.1 开发计划文档

| 文档 | 说明 |
|------|------|
| `docs/plans/KNOWLEDGE-WEB-UI-PLAN.md` | Knowledge Tool Web UI 详细计划 |
| `docs/plans/MEMORY-WEB-UI-PLAN.md` | Memory Tool Web UI 详细计划 |
| `docs/plans/EVOLUTION-REFACTOR-PLAN.md` | Evolution Engine 重构计划 |
| `docs/plans/ASSET-WEB-UI-PLAN.md` | Asset Tool Web UI 计划 |
| `docs/plans/QUALITY-WEB-UI-PLAN.md` | Quality Tool Web UI 计划 |

### 9.2 架构设计文档

| 文档 | 说明 |
|------|------|
| `docs/UNIFIED_WEB_UI_DESIGN.md` | 统一 Web UI 设计文档 |
| `docs/DEV-PLAN-V3.md` | V3 开发计划 |
| `docs/18-MASTER-DEVELOPMENT-PLAN.md` | 综合开发计划 |

### 9.3 工具文档

| 工具 | 文档位置 |
|------|----------|
| SkillRouter | `docs/ai-dev-platform/tools/template-tool/` |
| Sandbox | `docs/ai-dev-platform/tools/sandbox-tool/` |
| Quality | `docs/ai-dev-platform/tools/quality-tool/` |
| Memory | `docs/ai-dev-platform/tools/memory-tool/` |

---

## 10. 附录

### 10.1 术语表

| 术语 | 说明 |
|------|------|
| AIDP | AI-Driven Development Platform |
| MCP | Model Context Protocol |
| RBAC | Role-Based Access Control |
| SSO | Single Sign-On |
| Web UI | Web 用户界面 |
| API | Application Programming Interface |
| AST | Abstract Syntax Tree |
| pgvector | PostgreSQL 向量扩展 |

### 10.2 联系信息

- **项目管理**: AIDP Team
- **技术负责人**: [待填写]
- **产品负责人**: [待填写]

---

**文档结束**

*本计划将根据实际开发进度定期更新*
