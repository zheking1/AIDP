# AIDP 平台概述

## 什么是 AIDP

AIDP (AI DevOps Platform) 是一个私有化 AI 编程基础设施平台。它为开发者和 AI Agent 提供统一的项目管理、知识检索、代码执行、质量检查等能力，通过标准化 MCP (Model Context Protocol) 协议对外暴露服务。

仓库地址: `https://github.com/zheking1/AIDP`

## 解决什么问题

传统开发流程中，AI Agent 和开发者面临以下痛点:

| 痛点 | AIDP 的解决方案 |
|------|---------------|
| **知识碎片化** - 项目文档、代码结构、历史经验散落在不同系统 | **统一知识管理** - 知识库、记忆库、代码索引一体化检索 |
| **工具孤岛** - 代码执行、质量检查、技能路由各自独立 | **多工具架构** - 通过 Controller 统一编排 12+ 个专业工具 |
| **上下文不足** - AI Agent 缺乏项目背景和约束信息 | **5 阶段上下文管线** - 自动分析意图、检索知识、匹配技能 |
| **重复劳动** - 每次开发都要重新加载项目信息 | **项目初始化** - 一键扫描技术栈、导入文档、建立索引 |
| **缺乏标准化** - 不同 AI 工具使用不同接口 | **MCP 协议** - 基于 FastMCP 的标准化工具调用接口 |

## 谁在使用

- **AI Agent / AI 编程助手**: 通过 MCP 协议调用 AIDP 的工具能力，获取项目上下文、执行代码、检索知识
- **开发团队**: 通过 Web UI 管理项目、知识库、记忆、技能、规则等
- **平台管理员**: 管理用户、权限、工具注册、模型配置、审计日志

## 核心功能

### 1. 多工具架构

AIDP 采用 Controller + N 个可选工具的松耦合架构。Controller 负责统一的工具注册、健康检查、调用编排，各工具独立部署和扩展。

| 工具 | 端口 | 职责 |
|------|------|------|
| **controller** | `8883` | 主控服务 - 工具注册/编排、MCP 暴露、权限审计、Web UI |
| **skill-router** | `8788` | 技能路由引擎 - 意图分析、技能匹配、语义搜索 |
| **knowledge-tool** | `18081` | 文档知识库 - 文档导入、分块、向量检索 |
| **asset-tool** | `18082` | 代码资产管理 - 代码片段、模板存储和检索 |
| **sandbox-tool** | `18083` | 代码沙箱 - 安全的代码执行环境 |
| **quality-tool** | `18084` | 质量检查 - 代码规范、安全检查 |
| **memory-tool** | `18085` | 项目记忆 - 开发经验、bug 修复记录、架构决策 |
| **code-index** | `18086` | 代码索引 - AST 解析、符号搜索、调用链追踪 |
| **doc-index** | `18087` | 文档索引 - 文档结构化解析和索引 |
| **context-optimizer** | `18088` | 上下文优化 - 多工具结果去重、排序、Token 预算管理 |
| **evolution-engine** | `18089` | 自演进引擎 - 分析工具调用结果、自动化技能和规则更新 |
| **project-importer** | `18090` | 项目导入器 - 一键导入项目(扫描、索引、创建记忆) |
| **file-watcher** | `18091` | 文件监听 - 监控项目文件变更，自动触发重新索引 |

### 2. MCP 协议

AIDP Controller 通过 FastMCP 对外暴露标准化的 MCP Server (`apps/controller/app/mcp/server.py`)，AI Agent 通过 MCP Client 连接即可调用所有工具能力。

核心 MCP 工具:
- `aidp_context` - 5 阶段上下文管线(必须先调用)
- `invoke_tool_mcp` - 通用工具调用器
- `list_registered_tools` - 查看可用工具
- `check_tool_health` - 健康检查
- `aidp_init` - 项目初始化
- `aidp_instructions` - 生成 Subagent 指令
- `manage_models` - 模型管理

### 3. 5 阶段上下文管线

`aidp_context` 在每次开发任务前自动执行 (`apps/controller/app/services/context_pipeline.py:62`):

```
Stage 0: 从数据库加载 Agent Instructions(角色定义、约束规则)
Stage 1: 通过 skill-router 分析用户意图(识别所需工具、查询词)
Stage 2: 从 memory/knowledge/asset 并行检索知识
Stage 3: 技能匹配(自动选择最佳 skill)
Stage 4: 上下文组装(输出精炼后的上下文)
```

### 4. 统一知识管理

- **knowledge-tool**: 支持 Markdown/代码文件导入，自动分块(`chunk_size=800, overlap=120`)，向量检索(`hybrid` 模式)
- **memory-tool**: 项目级别的记忆存储，支持语义搜索和图谱关系
- **code-index**: AST 级别的代码符号索引，支持符号搜索、调用链、影响分析
- **doc-index**: 文档结构化索引(Markdown/HTML 解析)
- **context-optimizer**: 多工具检索结果融合，Token 预算管理(`default_budget=8000`)

### 5. 项目初始化

`project-importer` 提供一键导入功能:
1. 扫描项目目录，识别语言(`Python/Java/TypeScript/Go/Rust`)
2. 识别框架(`FastAPI/Spring Boot/React/Vue/Django/Flask`)
3. 分析技术栈，自动获取官方文档
4. 索引代码到 code-index
5. 导入文档到 knowledge-tool
6. 导入配置文件到 Controller
7. 创建项目记忆

## 快速开始

### 前置条件

- Python 3.13+
- PostgreSQL 16+ (含 pgvector 扩展)
- Redis 7+
- Docker & Docker Compose

### 部署步骤

```bash
# 1. 克隆仓库
git clone https://github.com/zheking1/AIDP.git
cd openCode

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置数据库密码、LLM API Key 等

# 3. 全量部署到 NAS
powershell deploy/deploy-nas.ps1

# 4. 验证服务
curl http://localhost:8883/health
```

### 独立启动某一工具

```bash
# SkillRouter 独立启动
cd tools/skill-router
cp .env.example .env
docker compose up -d

# Code Index 独立启动
cd tools/code-index
docker compose up -d
```

### 接入 AI Agent

在 AI Agent 的 MCP 配置中添加:

```json
{
  "mcpServers": {
    "aidp": {
      "url": "http://your-server:8883/mcp",
      "transport": "streamable-http"
    }
  }
}
```

Agent 连接后，首先调用 `aidp_context` 加载项目上下文，然后通过 `invoke_tool_mcp` 调用具体工具。