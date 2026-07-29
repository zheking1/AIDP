# AIDP 2026 年综合开发计划总览

> **文档整理说明**：本文档整合了 2024-2025 年的所有历史计划文档，包括 DEV-PLAN-V3、UNIFIED_WEB_UI_DESIGN、MASTER-DEVELOPMENT-PLAN 等。旧文档已归档至 `docs/archived/2024-2025/` 目录。

## 文档信息

| 属性 | 值 |
|------|-----|
| 版本 | v1.1 |
| 创建日期 | 2026-07-07 |
| 最后更新 | 2026-07-28 |
| 状态 | 进行中 |
| 编写者 | AIDP Team |

### 相关文档

| 文档 | 路径 | 说明 |
|------|------|------|
| **本计划** | `docs/MASTER-PLAN-2026.md` | 综合开发计划总览（当前文档） |
| **未完成任务** | `docs/UNFINISHED-TASKS.md` | 详细的待办任务清单 |
| **计划总结** | `docs/PLANS-SUMMARY.md` | 已完成和待完成工作汇总 |
| **Knowledge计划** | `docs/plans/KNOWLEDGE-WEB-UI-PLAN.md` | Knowledge Tool Web UI 详细计划 |
| **Memory计划** | `docs/plans/MEMORY-WEB-UI-PLAN.md` | Memory Tool Web UI 详细计划 |
| **Evolution计划** | `docs/plans/EVOLUTION-REFACTOR-PLAN.md` | Evolution Engine 重构计划 |
| **历史归档** | `docs/archived/2024-2025/` | 已完成的旧文档归档 |

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

### Phase 2: Web UI 生产级改造 (统一 Controller UI) 🚧 (进行中)

| 任务 | 优先级 | 预估工时 | 状态 |
|------|--------|----------|------|
| **Knowledge Tool Web UI** | P0 | 3 周 | ✅ 基本完成 |
| **Memory Tool Web UI** | P0 | 2 周 | ✅ 基本完成 |
| **Evolution Engine 重构** | P1 | 2 周 | ⚠️ 骨架阶段 |
| Asset Tool Web UI | P2 | 1 周 | ⚠️ 基础版 |
| Quality Tool Web UI | P2 | 3 天 | ⚠️ 基础版 |

> 注：所有工具 Web UI 已整合至 Controller 统一 UI（`apps/controller/app/web/templates/modules/`），不再维护独立工具 UI。

### Phase 3: 上下文优化管线 ✅ (已完成)

| 任务 | 优先级 | 预估工时 | 状态 |
|------|--------|----------|------|
| Agent Instructions 系统 | P0 | 1 周 | ✅ 已完成 |
| 分段检索管线 (Stage 0-4) | P0 | 2 周 | ✅ 已完成 |
| Intent Analysis 增强 | P0 | 3 天 | ✅ 已完成 |
| MCP 集成优化 | P1 | 1 周 | ✅ 已完成 |

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

### 4.2 需要进一步完善的模块

| 工具 | 当前 Web UI (统一 Controller 内) | 待完善功能 | 优先级 |
|------|------------|---------|--------|
| **Knowledge** | 完整（stats/层级树/文档CRUD/搜索/导入） | 分块可视化、知识图谱 | P2 |
| **Memory** | 完整（CRUD/D3.js图谱/stats/搜索） | 时间轴、上下文包生成器、向量搜索UI | P2 |
| **Asset** | 基础（列表/stats/搜索/创建） | 详情弹窗、模板预览 | P2 |
| **Quality** | 基础（表单/执行/结果） | 趋势图表、报告页面 | P2 |
| **Evolution** | 骨架（18行路由） | 两级进化系统、审核流程、版本管理 | P1 |

### 4.3 后台服务工具（无需 Web UI）

| 工具 | 类型 | 说明 |
|------|------|------|
| File Watcher | 后台服务 | 文件监控、自动触发 |
| Code Index | 索引服务 | AST 解析、符号索引 |
| Evolution | 分析服务 | 事件分析、模式提取 |
| Doc Index | 索引服务 | 文档索引、Wiki 生成 |

---

## 5. 详细开发计划

### 5.1 Knowledge Tool (P0) ✅ 基本完成

**已完成**：在 Controller 统一 UI 中实现了知识库管理层级树、文档CRUD（新建/上传/网页导入）、分类筛选、搜索和统计仪表盘。

**待完善**：
- 文档分块可视化
- 知识图谱

**文档**：详见 `docs/plans/KNOWLEDGE-WEB-UI-PLAN.md` (v2.0)

---

### 5.2 Memory Tool Web UI (P0) ✅ 基本完成

**已完成**：在 Controller 统一 UI 中实现了记忆条目 CRUD、统计仪表盘、D3.js 力导向图谱可视化（含缩放/物理模拟控制/图例）。

**待完善**：
- 时间轴视图
- 上下文包生成器
- 向量搜索 UI

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

### 8.1 高优先级 (P0) - 已完成

- [x] **Knowledge Tool Web UI** - 知识库管理、文档CRUD、搜索、统计
- [x] **Memory Tool Web UI** - 记忆CRUD、D3.js图谱、统计
- [x] **Agent Instructions 系统** - Stage 0-4 完整管线
- [x] **Intent Analysis 增强** - 意图分析 + fallback
- [x] **MCP 集成优化** - aidp_context / aidp_instructions

### 8.2 中优先级 (P1)

- [ ] **Evolution Engine 重构** - 两级进化系统（目前仅骨架）
- [ ] Knowledge Tool 分块可视化
- [ ] Memory Tool 时间轴/上下文包生成器
- [ ] **Asset Tool Web UI 完善** - 详情弹窗、模板预览
- [ ] **Quality Tool Web UI 完善** - 趋势图表、报告页面

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
