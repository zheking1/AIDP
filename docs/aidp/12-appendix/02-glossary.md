# AIDP 术语表

## 核心概念

| 术语 | 英文 | 说明 |
|------|------|------|
| AIDP | AI DevOps Platform | AI DevOps 平台, 提供 AI 辅助的代码开发、知识管理、代码执行等能力的基础设施 |
| Controller | 主控服务 | 中央调度器, 端口 8883, 负责工具注册/编排、MCP 端点暴露、Web UI、权限审计 |
| FastMCP | - | 基于 FastAPI 的 MCP 协议实现, 通过 streamable-http 传输 |

## 工具类

| 术语 | 定义 | 端口 |
|------|------|------|
| Tool | 工具 | 实现特定能力的微服务, 通过 Controller 注册并被编排调用 |
| Tool Registry | 工具注册表 | Controller 维护的所有已注册工具的列表, 存储于 PostgreSQL `tool_registry` 表 |
| Tool Manifest | 工具声明 | JSON 格式的元数据, 包含名称、版本、能力、Docker 镜像等 (`/tool/manifest`) |
| Tool Capabilities | 工具能力 | 工具暴露的具体功能端点, 附带输入/输出 schema (`/tool/capabilities`) |
| Tool Invoke | 工具调用 | 通过 Controller 代理调用工具能力 (`/tool/invoke`) |
| Tool Health | 工具健康状态 | 各工具的状态: `healthy` (健康), `registered` (已注册), `unhealthy` (异常), `unreachable` (不可达), `disabled` (已禁用) |
| Proxy Route | 代理路由 | Controller 转发前端请求到目标工具的机制 (`/api/proxy/{tool}/{path}`) |

## 各工具

| 术语 | 说明 | 端口 |
|------|------|------|
| skill-router | 技能路由引擎 - 意图分析 + 技能匹配 + 语义搜索 | 8788 |
| knowledge-tool | 知识工具 - 文档导入/分块/向量检索 | 18081 |
| asset-tool | 资产管理 - 代码片段、模板存储和检索 | 18082 |
| sandbox-tool | 代码沙箱 - 安全执行 Python/Bash/Shell 代码 | 18083 |
| quality-tool | 质量工具 - Lint 检查 + 安全扫描 | 18084 |
| memory-tool | 记忆工具 - 项目级知识/经验/决策存储与检索 | 18085 |
| code-index | 代码索引 - AST 解析 + 符号搜索 + 调用链追踪 | 18086 |
| doc-index | 文档索引 - 文档结构化解析和索引 | 18087 |
| context-optimizer | 上下文优化 - 多工具结果去重/排序/Token 预算管理 | 18088 |
| evolution-engine | 自演进引擎 - 分析工具调用结果, 自动化技能和规则更新 | 18089 |
| project-importer | 项目导入器 - 一键导入项目 (扫描/索引/记忆) | 18090 |
| file-watcher | 文件监听 - 监控项目文件变更, 自动触发重新索引 | 18091 |

## MCP 协议

| 术语 | 说明 |
|------|------|
| MCP | Model Context Protocol - AI Agent 与工具服务之间的标准化通信协议 |
| MCP Server | Controller 通过 FastMCP 暴露的标准化服务端点 |
| MCP Client | AI Agent / 编程助手通过 MCP 协议连接的客户端 |
| MCP Tool | Controller 暴露的 MCP 工具: `aidp_context`, `invoke_tool_mcp`, `list_registered_tools`, `check_tool_health`, `aidp_init`, `aidp_instructions`, `manage_models` |
| `aidp_context` | 5 阶段上下文管线入口 - **每次开发任务必须先调用** |
| `invoke_tool_mcp` | 通用工具调用器 - 传入工具名、能力、参数 |
| streamable-http | FastMCP 使用的传输协议 |
| CONTEXT_REQUIRED | 未先调用 `aidp_context` 而直接调用 `invoke_tool_mcp` 时返回的错误码 |

## 上下文管线

| 术语 | 说明 |
|------|------|
| 5 阶段上下文管线 | Controller 的核心处理流程: 意图分析 → 知识检索 → 技能匹配 → 上下文组装 → 指令输出 |
| context_pipeline | Controller 的上下文管线实现 (`apps/controller/app/services/context_pipeline.py`) |
| context_cache | 上下文缓存, TTL 300 秒 |
| context_assembly | 上下文组装, Token 预算上限 8000 |
| Token 预算 | LLM 调用的输入上限, 由 context-optimizer 管理 (min=1000, max=32000) |

## 知识管理

| 术语 | 说明 |
|------|------|
| Knowledge Base | 知识库 - 项目文档的结构化存储, 支持向量检索 |
| Knowledge Hub | 知识中心 - Web UI 中的统一知识管理入口 (`/hub/knowledge`) |
| Document Chunking | 文档分块 - 将文档切分为 800 字符的块, 重叠量 120 字符 |
| Embedding | 向量嵌入 - 使用 BGE-M3 模型 (SiliconFlow, 1024-dim) |
| Vector Search | 向量检索 - 在 pgvector 中基于语义相似度搜索文档 |
| Document Classification | 文档自动分类 - Controller 的文档自动归类功能 |

## 记忆管理

| 术语 | 说明 |
|------|------|
| Memory | 项目记忆 - 开发经验、Bug 修复记录、架构决策等 |
| Memory Hub | 记忆中心 - Web UI 中的统一记忆管理入口 (`/hub/memory`) |
| Memory Graph | 记忆图谱 - 可视化记忆之间的关联关系 (`/memory/graph`) |
| Memory Search | 记忆检索 - 基于关键词搜索存储的记忆 |

## 技能/规则

| 术语 | 说明 |
|------|------|
| Skill | 技能 - 可复用的开发能力/操作流程, 注册到技能路由器 |
| Skill Router | 技能路由 - 分析任务意图并匹配最佳技能 |
| Skill Hub | 技能库 - Web UI 中的统一技能管理入口 (`/hub/skills`) |
| Rule | 规则 - 必须遵守的开发约束 (如禁止硬编码密钥) |
| Global Rule | 全局规则 - 对所有项目生效的规则 |
| Personal Rule | 个人规则 - 仅对特定用户生效的规则 |
| Classification Import | 分类导入 - 将规则/知识文档存入分类系统的 API |

## Agent/Workflow

| 术语 | 说明 |
|------|------|
| Agent | AI Agent - 平台管理的 AI 执行单元, 可有特定配置 |
| Subagent | 子 Agent - 由 `aidp_instructions()` 创建的专用 Agent |
| agent_type | Agent 类型参数 - 传递给 `aidp_instructions()` 以生成专属指令 |
| Workflow | 工作流 - 定义复杂自动化操作流程 |
| Agent Instructions | Agent 指令 - 存储在数据库中的 Agent 角色配置 |

## 项目相关

| 术语 | 说明 |
|------|------|
| Project | 项目 - AIDP 管理的基本工作单元, 关联知识库、记忆、技能、规则 |
| Project Dashboard | 项目仪表盘 - 单个项目的统计视图 |
| Project Settings | 项目设置 - 基本信息、AI 配置、知识库配置、成员管理、集成 |
| Project Importer | 项目导入器 - `project-importer` 工具, 一键扫描/导入项目 |
| aidp_init | 项目初始化 MCP 工具 - 扫描技术栈、导入文档、建立索引 |
| Onboarding | 入门引导 - 新用户的引导流程 |

## Web UI 术语

| 术语 | 说明 |
|------|------|
| Workspace | 工作区 - 多标签页界面, Controller 的主页面 (`/`) |
| Dashboard | 仪表盘 - 平台/项目统计数据总览 |
| Layout | 布局模板 - base, unified_base, workspace, embed |
| Partial Rendering | 片段渲染 - `?partial=1` 参数控制只返回内容片段 |
| Frame Page | 框架页面 - 用于 iframe 嵌入的内容片段, 路由带 `-frame` 后缀 |
| Alpine.js | 轻量前端响应式框架 (CDN 引入) |
| Tailwind CSS | CSS 工具框架 (CDN 引入) |
| Font Awesome | 图标库 (CDN 引入) |
| CSRF Token | 跨站请求伪造令牌 - `<meta name="csrf-token">` |
| aidp_session | 用户 Session Cookie |

## Sandbox 术语

| 术语 | 说明 |
|------|------|
| Sandbox | 代码沙箱 - 安全执行用户代码的环境 |
| Execution | 代码执行记录 - 存储在 `sb_execution` 表的执行历史 |
| SecurityEngine | 安全检查引擎 - 扫描危险函数: `eval`, `exec`, `os.system`, `subprocess`, `socket` |
| ContainerPool | 容器池管理器 - 管理执行容器 (当前为模拟实现) |
| TimeoutManager | 超时管理器 - 30 秒超时控制 |
| ContextManager | 执行上下文管理器 - 管理多步骤执行的变量和状态 |
| stdin | 标准输入 - 可选的用户输入数据 |

## Quality 术语

| 术语 | 说明 |
|------|------|
| Lint Check | 代码规范检查 - 行长度 (120)，尾部空格，文件末尾换行符 |
| Security Scan | 安全扫描 - 硬编码密钥，SQL 注入，危险函数 (eval/exec/os.system/pickle) |
| Issue Severity | 问题严重性: `critical` (严重), `high` (高), `medium` (中), `warning` (警告), `info` (信息) |
| CheckResult | 检查结果 - 存储在 `ql_check_result` 表 |
| Semantic Duplication | 语义重复检测 - 基于余弦相似度 (>0.85) 检测代码重复 |
| Incremental Analyzer | 增量分析器 - 基于 MD5 hash 的变更检测 + 缓存 |
| Language Adapter | 语言适配器 - 按语言提供分析: `PythonAdapter`, `JavaScriptAdapter` |

## 技术栈

| 术语 | 说明 |
|------|------|
| FastAPI | Python async Web 框架, 所有服务的基础 |
| Pydantic | 数据校验库, 用于 Settings 和 Request/Response 模型 |
| SQLAlchemy 2.0 | 异步 ORM, 所有服务的数据库层 |
| Uvicorn | ASGI web server |
| asyncpg | PostgreSQL 异步驱动 |
| pgvector | PostgreSQL 向量扩展, 用于文档 Embedding 检索 |
| PostgreSQL 16 | 主数据库 |
| Redis 7 | 缓存服务 |
| Docker | 容器化部署 |
| Docker Compose | 多容器编排 |
| Network Mode: host | Docker 容器使用宿主机网络, 端口直接暴露 |
| NAS | Network Attached Storage - 部署目标: `192.168.0.100` |
| SSO | Single Sign-On - 统一认证 (`auth/login.html`) |

## LLM/Embedding

| 术语 | 说明 |
|------|------|
| DeepSeek | 默认 LLM 模型 (`deepseek-v4-flash-free`) |
| GLM | 备用 LLM 模型 (ZhipuAI) |
| ERNIE | 备用 LLM 模型 (BaiduBCE) |
| BGE-M3 | Embedding 模型 (SiliconFlow, 1024-dim) |
| LLM Endpoint | LLM API 调用端点 |
| Embedding Endpoint | Embedding API 调用端点 |
| BaiduBCE | 百度百舸 - LLM 托管平台 |

## 部署相关

| 术语 | 说明 |
|------|------|
| NAS | 部署目标服务器: `192.168.0.100` |
| deploy-nas.ps1 | NAS 全量部署脚本 |
| Docker Image | 容器镜像, 命名规范: `aidp/{tool_name}:{version}` |
| Dockerfile | 各工具根目录下的容器构建文件 |
| .env | 环境变量配置文件 |
| environment variables | 所有密钥/密码通过环境变量管理, 禁止硬编码 |

## 认证/授权

| 术语 | 说明 |
|------|------|
| User Role | 用户角色: `super_admin`, `admin`, `user` |
| Session Token | 会话令牌 - 存储在 `aidp_session` cookie 中 |
| API Key | API 密钥 - 用于 MCP 调用的认证令牌 |
| Permission Service | 权限服务 - 检查用户角色和权限 |
| Auth Decorator | 认证装饰器: `@require_login`, `@require_admin` |
| Audit Log | 审计日志 - 记录用户操作轨迹 |

## 事件总线事件

| 术语 | 说明 |
|------|------|
| TOOLS_LOADED | 工具列表加载完成事件 |
| TOOL_STATUS_CHANGED | 工具状态变化事件 |
| PAGE_CHANGED | 页面切换事件 |
| NOTIFICATION_SHOW | 通知显示事件 |
| NAVIGATE | 页面导航事件 |
| ERROR_OCCURRED | 错误发生事件 |
| LOADING_START / LOADING_END | 加载状态事件 |

## 关键数值常量

| 术语 | 数值 | 说明 |
|------|------|------|
| Session Timeout | 30 分钟 | 用户会话超时 |
| Context Cache TTL | 300 秒 | 上下文缓存过期时间 |
| Token Budget | 8000 (min=1000, max=32000) | LLM 输入上限 |
| Tool Call Timeout | 30 秒 | 工具调用超时 |
| Tool Call Retry | 3 次 | 指数退避重试 |
| Execution Timeout | 30 秒 | 代码执行超时 |
| Execution Max Output | 10240 字节 (10KB) | 执行输出上限 |
| Document Chunk Size | 800 | 文档分块大小 |
| Chunk Overlap | 120 | 分块重叠量 |
| Embedding Dimension | 1024 | 向量维度 (BGE-M3) |
| Knowledge Top-K | 8 | 知识检索返回数 |
| Skill Top-K | 5 | 技能检索返回数 |
| Store Cache TTL | 30 秒 | 工具列表缓存时间 |
| Auto Refresh Interval | 60 秒 | 健康检查间隔 |