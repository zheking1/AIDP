# AIDP 完整架构

## 总体架构图

```
                              AI Agent / 开发者
                                    │
                                    │ MCP (Streamable-HTTP) + Web UI
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│           aidp-controller :8883 (Python 3.13 + FastAPI + FastMCP)             │
│           ═══════════════ 唯一容器 ═══════════════                             │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │ Context Pipe  │  │ Session Mgr  │  │ Tool Invoker │  │ MCP Server       │ │
│  │ (5-Stage)     │  │ (user/proj)  │  │ (本地调用)     │  │ (13 tools)       │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘ │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │ 15 Modules   │  │ Evolution    │  │ Model Service│  │ Web Routes       │ │
│  │ (知识/记忆...) │  │ (两级进化)    │  │ (统一模型)    │  │ (Jinja2模板)     │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘ │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────────┐│
│  │  已整合工具 (app/tools/): skill-router, knowledge, memory, asset,        ││
│  │  sandbox, quality, context-optimizer, evolution-engine                   ││
│  └──────────────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │ (仅 code-index 仍在独立容器)
                                     ▼
                          ┌──────────────────┐
                          │   PostgreSQL 16   │
                          │   (全模块共享)      │
                          └──────────────────┘
```

## 整合状态

### 已整合到 Controller (8 个)

| 工具 | 原端口 | 当前状态 |
|------|:---:|------|
| skill-router | 8788 | ✅ 已整合, 旧容器已删除 |
| knowledge-tool | 18081 | ✅ 已整合, 旧容器已删除 |
| memory-tool | 18085 | ✅ 已整合, 旧容器已删除 |
| asset-tool | 18082 | ✅ 已整合 |
| sandbox-tool | 18083 | ✅ 已整合 |
| quality-tool | 18084 | ✅ 已整合 |
| context-optimizer | 18088 | ✅ 已整合, 旧容器已删除 |
| evolution-engine | 18089 | ✅ 已整合, 旧容器已删除 |

### 保持独立 (1 个)

| 工具 | 端口 | 原因 |
|------|:---:|------|
| file-watcher | 18091 | 需要 watchdog 进程在本地运行, 不适合服务端整合 |

### 未部署 (4 个——备用)

| 工具 | 端口 | 说明 |
|------|:---:|------|
| code-index | 18086 | 代码索引, 按需启动 |
| doc-index | 18087 | 文档索引, 按需启动 |
| importer-tool | 18085 | 批量导入, 按需启动 |
| project-importer | 18090 | 项目导入, 按需启动 |

## 数据流

```
MCP Agent 调用:

1. aidp_context(project_name, task, api_key)
   └─ Session Manager: api_key → 用户 → 绑定 session
   └─ 5-Stage Pipeline:
       Stage 0: 加载项目 Instructions (Controller DB)
       Stage 1: 意图分析 (SkillRouter → LLM)
       Stage 2: 并行检索 (Memory + Knowledge + Asset)
       Stage 3: 技能匹配 (SkillRouter)
       Stage 4: 上下文组装 (ContextAssembler)

2. invoke_tool_mcp(tool_name, capability, arguments)
   └─ Session Manager: 检查认证 + 上下文加载
   └─ 自动注入: project_id, user_id (从 session)
   └─ Tool Invoker: 优先本地调用, 回退 HTTP

3. index_changes(task, changed_files, summary)
   └─ 解析文件 → code-index 增量索引
   └─ 文档分类 → knowledge-tool 导入
   └─ LLM 模式分析 → auto-propose evolution

4. promote_evolution / analyze_and_evolve
   └─ Evolution Engine: LLM 分析 → 提案 → 审核
```

## 15 个功能模块

```
modules/
├── knowledge/     知识库 (框架/模板/项目三级, 分块索引, 搜索)
├── memory/        记忆 (经验, bugfix, 架构决策, D3图谱)
├── skills/        技能库 (global/personal/project, 审核流程)
├── rules/         规则 (global/personal/project, 安全/规范)
├── agents/        Agent (Instructions+Skills+Rules+Knowledge组合)
├── workflows/     流程 (多步骤多Agent协作)
├── evolution/     进化 (项目级→审核→系统级)
├── sandbox/       沙箱 (Python/Bash执行)
├── quality/       质量 (代码规范, 安全扫描, 趋势图表)
├── assets/        资产 (代码片段, 模板存储)
└── instructions/  指令模板 (每个项目的Agent角色和约束)
```

## MCP 会话管理

```
Agent 连接 → session 创建
  │
  ├─ aidp_context(api_key) → 认证用户 → session 绑定 (user_id, project_id)
  │
  ├─ 白名单工具 (无需认证): aidp_context, list_registered_tools, check_tool_health, index_changes
  │
  └─ invoke_tool_mcp → 检查认证 → 自动注入 project_id/user_id → 执行
```