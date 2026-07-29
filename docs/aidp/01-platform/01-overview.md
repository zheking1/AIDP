# AIDP 平台概述

## 什么是 AIDP

AIDP (AI DevOps Platform) 是一个私有化 AI 编程基础设施平台。它通过标准 MCP 协议为 AI Agent 提供项目上下文、知识检索、代码索引、质量检查等能力，由一个统一的 Controller 服务承载所有功能。

## 设计理念

```
单一入口，全部能力

  AI Agent → MCP → Controller (:8883)
                         │
                         ├─ 5 阶段上下文管线 (aidp_context)
                         ├─ 15 个模块 (知识/记忆/技能/规则/Agent/流程...)
                         ├─ 13 个 MCP 工具
                         ├─ 统一模型管理 (8 个 LLM)
                         ├─ 用户/项目绑定 + 会话认证
                         ├─ Evolution 两级进化系统
                         └─ 三层文件索引系统
                         
  外部独立工具 (剩余 1 个):
    └─ file-watcher (:18091) — 本地文件监控守护进程
```

## 核心架构

| 层级 | 组件 | 说明 |
|------|------|------|
| **入口层** | MCP Server + Web UI | AI Agent 通过 MCP 协议调用，开发者通过浏览器管理 |
| **管线层** | 5 阶段上下文管线 | 指令加载 → 意图分析 → 知识检索 → 技能匹配 → 上下文组装 |
| **模块层** | 15 个功能模块 | 知识库、记忆、技能、规则、Agent、流程、沙箱、质量、资产、进化等 |
| **数据层** | PostgreSQL | 所有模块共享同一数据库，统一事务和查询 |

## 功能模块

### 知识管理 (4 个模块)

| 模块 | 说明 | 数据隔离 |
|------|------|:---:|
| **knowledge** | 知识库、文档管理、分块索引、搜索 | 用户/项目/可见性三级 |
| **memory** | 项目记忆、经验沉淀、图谱可视化 | 项目级 |
| **skills** | 技能库、意图匹配、语义搜索 | global/personal/project |
| **rules** | 编码规范、安全规则、审查流程 | global/personal/project |

### 开发工具 (3 个模块)

| 模块 | 说明 |
|------|------|
| **sandbox** | 代码沙箱 — 安全的 Python/Bash 执行环境 |
| **quality** | 质量检查 — 代码规范、安全漏洞、硬编码密钥检测 |
| **assets** | 代码资产 — 代码片段、模板存储和检索 |

### 编排管理 (4 个模块)

| 模块 | 说明 |
|------|------|
| **agents** | Agent 管理 — 组合 Instructions/Skills/Rules/Knowledge |
| **workflows** | 流程管理 — 多步骤多 Agent 协作流程 |
| **evolution** | 进化系统 — 项目级经验 → 审核 → 系统级最佳实践 |
| **instructions** | 指令模板 — 每个项目的 Agent 角色和约束 |

### 文件索引 (3 层防御)

| 层级 | 触发方式 | 可靠性 |
|:---:|------|:---:|
| Layer 1 | git post-commit hook | 最可靠 |
| Layer 2 | Agent MCP `index_changes` | 最智能 |
| Layer 3 | file_watcher.py (watchdog) | 最实时 |

## 5 阶段上下文管线

每次 `aidp_context()` 调用自动执行：

```
Stage 0: 加载项目 Agent Instructions (角色、约束、规则)
Stage 1: 意图分析 (识别领域、复杂度、需要的工具)
Stage 2: 并行检索 (Memory → Knowledge → Asset)
Stage 3: 技能匹配 (从 SkillRouter 获取最佳技能)
Stage 4: 上下文组装 (Token 预算管理, 优先排序)
```

## MCP 工具 (13 个)

### 核心工作流

| 工具 | 作用 | 认证 |
|------|------|:---:|
| `aidp_context` | 加载项目上下文（必须先调用）| api_key |
| `invoke_tool_mcp` | 调用任意已注册工具 | 需 context |
| `index_changes` | 增量索引代码变更 + 模式分析 | session 绑定 |

### 项目初始化

| 工具 | 作用 |
|------|------|
| `aidp_init` | 一键初始化项目（代码索引、文档导入、记忆创建）|
| `install_local_scripts` | 生成本地 git hook + file_watcher 配置 |
| `aidp_instructions` | 生成 Subagent 专用指令 |

### 进化与知识沉淀

| 工具 | 作用 |
|------|------|
| `promote_evolution` | 提交项目经验为系统级进化提案 |
| `list_evolutions` | 查看系统级最佳实践 |
| `analyze_and_evolve` | LLM 自动分析代码变更、提取模式 |

### 管理与监控

| 工具 | 作用 |
|------|------|
| `list_registered_tools` | 查看所有可用工具 |
| `check_tool_health` | 检查工具健康状态 |
| `manage_models` | 统一管理 LLM 模型配置 |
| `sync_tool_capabilities` | 同步工具能力定义 |

## 统一模型管理

所有 LLM 调用统一由 Controller 的模型管理页面配置：

| 模型 | 用途 |
|------|------|
| GLM-5 / GLM-5.1 | 通用聊天 |
| ERNIE 4.5 Turbo | 代码分析 |
| DeepSeek V4 Flash / Pro / V3.2 | 多场景 |
| BGE-M3 | 向量嵌入 |
| BGE-Reranker V2-M3 | 检索重排 |

## 部署

### 当前部署（单容器）

```bash
# 唯一容器
docker compose up -d controller

# 验证
curl http://192.168.0.100:8883/health
```

### 接入 AI Agent

```json
{
  "mcpServers": {
    "aidp": {
      "url": "http://192.168.0.100:8883/mcp",
      "transport": "streamable-http",
      "headers": { "x-api-key": "your-api-key" }
    }
  }
}
```

## 文档导航

| 目录 | 内容 |
|------|------|
| `01-platform/` | 平台架构、部署、认证、模型管理 |
| `02-controller/` | Controller API、上下文管线、MCP 服务 |
| `09-file-indexing/` | 三层文件索引系统 |
| `plans/` | 开发计划文档 |