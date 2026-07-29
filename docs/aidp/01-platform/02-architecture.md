# AIDP 完整架构

## 总体架构图

```
                             用户 / AI Agent
                                   |
                                   | MCP (Streamable-HTTP)
                                   | Web UI (Jinja2 + Alpine.js + Tailwind CSS)
                                   |
                                   v
┌──────────────────────────────────────────────────────────────────────────────┐
│                     aidp-controller :8883 (Python 3.13 + FastAPI + FastMCP)   │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │ Tool Registry │  │ Context Pipe │  │ Auth Service │  │ MCP Server       │ │
│  │ (注册/健康)    │  │ (5-Stage)    │  │ (JWT/Cookie) │  │ (FastMCP)        │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘ │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │ Tool Invoker │  │ Session Mgr  │  │ Config Svc   │  │ Web Routes       │ │
│  │ (HTTP 调用)   │  │ (上下文强制)  │  │ (YAML菜单)   │  │ (Jinja2模板)     │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
          |                    |                    |
          | HTTP REST          | HTTP REST          | HTTP REST
          v                    v                    v
┌─────────────────┐  ┌─────────────────┐  ┌───────────────────┐
│  PostgreSQL 16   │  │    Redis 7      │  │  External Tools    │
│  + pgvector      │  │  (Caching)      │  │  (各工具服务)       │
└─────────────────┘  └─────────────────┘  └───────────────────┘
                                                    |
          ┌─────────────────────────────────────────┼─────────────────────────────┐
          │                                         │                             │
          v                                         v                             v
┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐  ┌──────────────────────┐
│ skill-router :8788  │  │ knowledge-tool     │  │ asset-tool :18082   │  │ sandbox-tool :18083   │
│ FastAPI + FastMCP   │  │ :18081             │  │ 代码资产管理          │  │ 代码沙箱执行            │
│ PostgreSQL+pgvector │  │ 文档知识库           │  │ SQLite              │  │ 子进程隔离              │
│ + Redis             │  │ SQLite + Sentence  │  │                     │  │                        │
│ 技能路由+意图分析     │  │ Transformers       │  │                     │  │                        │
└────────────────────┘  └────────────────────┘  └────────────────────┘  └──────────────────────┘

┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐  ┌──────────────────────┐
│ quality-tool :18084 │  │ memory-tool :18085  │  │ code-index :18086   │  │ doc-index :18087      │
│ 代码质量/安全检查     │  │ 项目记忆/SQLite      │  │ AST索引/SQLite       │  │ 文档索引/SQLite         │
│ 正则分析器           │  │ 图谱关系             │  │ Tree-Sitter+BGE-M3  │  │ Markdown/LXML           │
└────────────────────┘  └────────────────────┘  └────────────────────┘  └──────────────────────┘

┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐  ┌──────────────────────┐
│ context-optimizer  │  │ evolution-engine   │  │ project-importer   │  │ file-watcher :18091    │
│ :18088              │  │ :18089              │  │ :18090              │  │ 文件变更监控            │
│ 上下文去重+Token管理 │  │ 自演进优化           │  │ 一键项目导入           │  │ 自动重新索引            │
│ SQLite              │  │ SQLite + LLM        │  │ 技术栈分析+文档导入    │  │ SQLite                  │
└────────────────────┘  └────────────────────┘  └────────────────────┘  └──────────────────────┘
```

## 服务详细说明

### 1. Controller (`apps/controller/`) - 端口 8883

**角色**: 平台核心，统一 API 网关和服务编排器。

**容器**: `aidp-controller`
**镜像**: `aidp/controller:0.1.0`
**启动**: `uvicorn app.main:app --host 0.0.0.0 --port 8883`

**核心模块**:

| 模块 | 文件 | 职责 |
|------|------|------|
| MCP Server | `app/mcp/server.py` | FastMCP 实例 `"aidp-controller"`，暴露 7 个 MCP 工具 |
| Session Manager | `app/mcp/session_manager.py` | 强制 `aidp_context` 调用顺序，30 分钟超时 |
| Tool Registry | `app/services/tool_registry.py` | 工具 CRUD、健康检查、能力同步 |
| Tool Invoker | `app/services/tool_invoker.py` | 通过 HTTP 调用各工具的 `/tool/invoke` 端点 |
| Context Pipeline | `app/services/context_pipeline.py` | 5 阶段上下文管线 (`ContextPipeline` 类) |
| Context Assembler | `app/services/context_assembly.py` | 上下文组装，最大 8000 tokens |
| Context Cache | `app/services/context_cache.py` | 检索结果缓存，TTL 300 秒 |
| Auth Service | `app/services/auth_service.py` | JWT + Cookie 会话管理 |
| Web Routes | `app/web/routes.py` | Jinja2 模板渲染，60+ 页面路由，代理转发 |

**MCP 工具列表** (`app/mcp/server.py`):

| 工具名 | 说明 |
|--------|------|
| `aidp_context` | 5 阶段上下文管线 (必须先调用) |
| `invoke_tool_mcp` | 通用工具调用器 |
| `list_registered_tools` | 查看所有已注册工具 |
| `check_tool_health` | 健康检查 |
| `aidp_init` | 项目初始化 |
| `aidp_instructions` | 生成 subagent 指令 |
| `manage_models` | 模型管理 (CRUD) |

**主要 API 端点**:

| 路由 | 说明 |
|------|------|
| `/mcp` | MCP Server (Streamable-HTTP) |
| `/health` | 健康检查 |
| `/api/tools` | 工具列表 |
| `/api/projects` | 项目管理 |
| `/api/auth/login` | 用户登录 |
| `/api/proxy/{tool}/{path}` | 工具请求代理 |
| `/ws/logs` | WebSocket 日志流 |
| `/` | Web UI 主页 |

### 2. Skill Router (`tools/skill-router/`) - 端口 8788

**角色**: 技能路由引擎，提供意图分析、技能匹配、语义搜索能力。

**容器**: 通过 `docker-compose.yml` (network_mode: host)
**镜像**: 自定义构建 (Python 3.13-slim)
**启动**: `uvicorn app.main:app --host 0.0.0.0 --port 8788`

**核心模块**:

| 模块 | 文件 | 职责 |
|------|------|------|
| FastMCP Server | `app/main.py:25` | `FastMCP("SkillRouter")`，MCP 工具注册 |
| MCP Tools | `app/mcp/tools.py` | 注册所有 MCP 工具 |
| Model Client | `app/model_client.py` | LLM 调用客户端 |
| Web Auth | `app/web/auth.py` | 登录认证 |
| API Routes | `app/api/routes.py` | REST API 端点 |

**数据库依赖**: PostgreSQL + pgvector (向量存储) + Redis (缓存)

**配置** (`app/config.py`):
- `llm_model`: 默认 `deepseek-v4-flash-free`
- `embedding_model`: 默认 `text-embedding-3-small`
- `embedding_dim`: 默认 `1024`
- `cache_ttl_seconds`: 默认 `3600`
- `resolve_top_k_default`: 默认 `5`

### 3. Knowledge Tool (`tools/knowledge-tool/`) - 端口 18081

**角色**: 文档知识库管理，支持文档导入、分块、向量检索。

**容器**: 通过 `docker-compose.yml`
**镜像**: 自定义构建 (Python 3.13-slim)
**启动**: `uvicorn app.main:app --host 0.0.0.0 --port 18081`

**核心模块**:

| 模块 | 目录 | 职责 |
|------|------|------|
| Chunk Engine | `app/chunk/` | 文档分块 (`chunk_size=800, overlap=120`) |
| Embedding | `app/embedding/` | 向量化 (Mock/OpenAI/Local 三种 Provider) |
| Search Engine | `app/search/` | 混合检索 (`hybrid` 模式，`top_k=8`) |
| Parser | `app/parser/` | 文档解析 (Markdown 等格式) |
| Storage | `app/storage/` | 文件存储 (`local` Provider) |
| Web UI | `app/web/` | 内嵌 Web 管理界面 |

**数据库**: SQLite (`data/knowledge.db`) 或 PostgreSQL

**配置** (`app/config.py`):
- `CHUNK_DEFAULT_SIZE`: `800`
- `CHUNK_DEFAULT_OVERLAP`: `120`
- `SEARCH_DEFAULT_TOP_K`: `8`
- `SEARCH_DEFAULT_MODE`: `hybrid`
- `UPLOAD_MAX_FILE_SIZE_MB`: `50`

### 4. Asset Tool (`tools/asset-tool/`) - 端口 18082

**角色**: 代码片段、模板等可复用资产的管理和检索。

**容器**: 通过 `docker-compose.yml`
**镜像**: 自定义构建 (Python 3.13-slim)
**启动**: `uvicorn app.main:app --host 0.0.0.0 --port 18082`

**核心模块**:

| 模块 | 路径 | 职责 |
|------|------|------|
| API | `app/api/assets.py` | 资产 CRUD |
| Web UI | `app/web/routes.py` | 管理界面 |

**数据库**: SQLite 或 PostgreSQL
**配置**: `SEARCH_DEFAULT_TOP_K=8`, `UPLOAD_MAX_CONTENT_SIZE_MB=10`

### 5. Sandbox Tool (`tools/sandbox-tool/`) - 端口 18083

**角色**: 安全的代码执行环境，通过子进程隔离执行代码。

**容器**: `aidp-sandbox`
**镜像**: `aidp/sandbox-tool:0.1.0`
**启动**: `uvicorn app.main:app --host 0.0.0.0 --port 18083`

**核心模块**:

| 模块 | 路径 | 职责 |
|------|------|------|
| Execute API | `app/api/execute.py` | 代码执行端点 |
| Web UI | `app/web/routes.py` | 沙箱界面 |

**配置** (`app/config.py`):
- `EXECUTION_TIMEOUT`: `30` 秒
- `EXECUTION_MAX_OUTPUT`: `10240` 字节

### 6. Quality Tool (`tools/quality-tool/`) - 端口 18084

**角色**: 代码质量检查，包括代码规范(lint)和安全检查。

**容器**: `aidp-quality`
**镜像**: `aidp/quality-tool:0.1.0`
**启动**: `uvicorn app.main:app --host 0.0.0.0 --port 18084`

**核心模块**:

| 模块 | 文件 | 职责 |
|------|------|------|
| Rule Engine | `app/analyzers/rule_engine.py` | 规则匹配引擎 |
| Language Adapter | `app/analyzers/language_adapter.py` | 多语言适配 |
| Duplication Check | `app/analyzers/semantic_duplication.py` | 语义重复检测 |
| Check API | `app/api/check.py` | 检查端点 |

**配置** (`app/config.py`):
- `LINT_MAX_LINE_LENGTH`: `120`
- `LINT_CHECK_TRAILING_WHITESPACE`: `True`
- `LINT_CHECK_MISSING_NEWLINE`: `True`
- `SECURITY_CHECK_HARDCODED_SECRETS`: `True`
- `SECURITY_CHECK_SQL_INJECTION`: `True`
- `SECURITY_CHECK_DANGEROUS_FUNCTIONS`: `True`

### 7. Memory Tool (`tools/memory-tool/`) - 端口 18085

**角色**: 项目级别的开发经验记忆，支持语义搜索和图谱关系。

**容器**: 通过 `docker-compose.yml`
**镜像**: 自定义构建 (Python 3.13-slim)
**启动**: `uvicorn app.main:app --host 0.0.0.0 --port 18085`

**核心模块**:

| 模块 | 路径 | 职责 |
|------|------|------|
| Memory API | `app/api/memory.py` | 记忆 CRUD |
| Memories V2 | `app/api/memories.py` | V2 版记忆 API |
| Graph API | `app/api/graph.py` | 记忆图谱关系 |
| Search API | `app/api/search.py` | 语义搜索 |
| Context API | `app/api/context.py` | 上下文获取 |
| Review API | `app/api/review.py` | 记忆审核 |

**数据库**: SQLite 或 PostgreSQL (含 pgvector `>=0.2.0`)
**配置**: `MEMORY_DEFAULT_LIMIT=50`, `MEMORY_MAX_LIMIT=200`

### 8. Code Index (`tools/code-index/`) - 端口 18086

**角色**: 代码结构索引，支持 AST 解析、符号搜索、调用链追踪、影响分析。

**容器**: 通过 `docker-compose.yml`
**镜像**: 自定义构建 (Python 3.13-slim)
**启动**: `uvicorn app.main:app --host 0.0.0.0 --port 18086`

**核心模块**:

| 模块 | 路径 | 职责 |
|------|------|------|
| Code Index API | `app/api/code_index.py` | 索引和查询端点 |
| Services | `app/services/` | 索引逻辑 |
| Model Client | `app/model_client.py` | 嵌入模型客户端 |

**数据库**: SQLite (`data/code_index.db`)
**能力** (`tool.yaml`): `code.explore`, `search`, `scan`, `calls`, `dependents`, `structure`
**依赖**: Tree-Sitter (AST 解析), BGE-M3 (代码嵌入)

### 9. Doc Index (`tools/doc-index/`) - 端口 18087

**角色**: 文档结构化索引，支持 Markdown 和 HTML 解析。

**容器**: 独立 Docker 容器
**镜像**: 自定义构建 (Python 3.13-slim)
**启动**: `uvicorn app.main:app --host 0.0.0.0 --port 18087`

**核心模块**:

| 模块 | 路径 | 职责 |
|------|------|------|
| Doc Index API | `app/api/doc_index.py` | 文档索引端点 |
| Services | `app/services/` | 索引逻辑 |

**数据库**: SQLite (`data/doc_index.db`)
**依赖**: `markdown>=3.5`, `beautifulsoup4>=4.12`, `lxml>=5.0`

### 10. Context Optimizer (`tools/context-optimizer/`) - 端口 18088

**角色**: 多工具检索结果融合、去重排序、Token 预算管理。

**容器**: 独立 Docker 容器
**镜像**: 自定义构建 (Python 3.13-slim)
**启动**: `uvicorn app.main:app --host 0.0.0.0 --port 18088`

**配置** (`app/config.py`):
- `DEFAULT_BUDGET`: `8000` tokens
- `MIN_BUDGET`: `1000`
- `MAX_BUDGET`: `32000`
- `SIMILARITY_THRESHOLD`: `0.7`
- `MAX_RESULTS_PER_TOOL`: `10`
- `SUMMARY_RATIO`: `0.3`
- `CACHE_TTL`: `3600` 秒

**工具优先级权重**:
- `TOOL_PRIORITY_CODE_INDEX`: `1.5` (最高)
- `TOOL_PRIORITY_KNOWLEDGE`: `1.2`
- `TOOL_PRIORITY_MEMORY`: `1.0`
- `TOOL_PRIORITY_ASSET`: `0.8`
- `TOOL_PRIORITY_QUALITY`: `0.5`
- `TOOL_PRIORITY_SANDBOX`: `0.3`

### 11. Evolution Engine (`tools/evolution-engine/`) - 端口 18089

**角色**: 分析工具调用成败数据，自动化更新技能和规则。

**容器**: 独立 Docker 容器
**镜像**: 自定义构建 (Python 3.13-slim)
**启动**: `uvicorn app.main:app --host 0.0.0.0 --port 18089`

**配置** (`app/config.py`):
- `LLM_MODEL`: `qwen2.5:7b`
- `BATCH_SIZE`: `10`
- `ANALYSIS_TIMEOUT`: `30` 秒
- `ROUTE_ERROR`: `["memory"]` - 错误时路由到 memory
- `ROUTE_SUCCESS`: `["memory", "asset"]` - 成功时路由到 memory + asset
- `ROUTE_OPTIMIZATION`: `["knowledge", "code_index"]` - 优化建议路由

### 12. Project Importer (`tools/project-importer/`) - 端口 18090

**角色**: 一键导入项目，自动扫描、索引代码、导入文档和配置。

**容器**: 独立 Docker 容器
**镜像**: 自定义构建 (Python 3.13-slim)
**启动**: `uvicorn app.main:app --host 0.0.0.0 --port 18090`

**主要 API**:
- `GET /api/onboarding/scan?path=` - 扫描项目，识别语言和框架
- `POST /api/onboarding/import` - 完整导入流程
- `POST /api/import/project` - 一键导入（旧版）
- `GET /api/scan?path=` - 快速扫描

**框架检测信号** (`FRAMEWORK_SIGNALS`):
- FastAPI: `requirements.txt`, `fastapi`, `uvicorn`
- Spring Boot: `pom.xml`, `Application.java`, `application.yml`
- React: `package.json`, `react`, `tsx`
- Vue: `vue`, `package.json`
- Django/Flask/Go Gin/Rust Actix/NestJS

### 13. File Watcher (`tools/file-watcher/`) - 端口 18091

**角色**: 监控项目文件变更，自动触发重新索引。

**容器**: 独立 Docker 容器
**镜像**: 自定义构建 (Python 3.13-slim)
**启动**: `uvicorn app.main:app --host 0.0.0.0 --port 18091`

**配置** (`app/config.py`):
- `CODE_INDEX_URL`: `http://127.0.0.1:18086`
- `CONTROLLER_URL`: `http://127.0.0.1:8883`
- `DEBOUNCE_SECONDS`: `1.0`
- `IGNORED_DIRS`: `.git`, `__pycache__`, `node_modules`, `.venv`, `venv`, `.idea`, `.vscode`


## 通信模式

### 1. Controller → 工具

Controller 通过 `ToolInvoker` (`apps/controller/app/services/tool_invoker.py:23`) 调用工具:

```
POST /tool/invoke
{
  "capability": "memory.search",
  "input": { "query": "...", "limit": 5 },
  "trace_id": "abc12345"
}
```

Controller 从 `ToolRegistry` 表中获取工具的 `endpoint`，然后构造请求 URL。工具必须实现 `/tool/invoke` 端点来接收调用。

### 2. 工具 → 工具 (独立注册)

每个工具在 `tool.yaml` 中声明自己的端点和能力:
- Controller: `apps/controller/tool.yaml` - 声明 `controller.list_tools`, `controller.invoke`, `controller.health`
- Code Index: `tools/code-index/tool.yaml` - 声明 `code.explore`, `search`, `scan`, `calls`, `dependents`, `structure`
- Knowledge: `tools/knowledge-tool/tool.yaml`
- Memory: `tools/memory-tool/tool.yaml`
- Asset: `tools/asset-tool/tool.yaml`
- Sandbox: `tools/sandbox-tool/tool.yaml`
- Quality: `tools/quality-tool/tool.yaml`
- Doc Index: `tools/doc-index/tool.yaml`
- Context Optimizer: `tools/context-optimizer/tool.yaml`
- Evolution Engine: `tools/evolution-engine/tool.yaml`
- File Watcher: `tools/file-watcher/tool.yaml`

### 3. MCP Client → Controller

AI Agent 通过 MCP 协议连接 Controller:

```
Streamable-HTTP: POST /mcp
-> FastMCP Server (app/mcp/server.py)
-> MCP Tool 函数 (aidp_context / invoke_tool_mcp / ...)
-> 业务逻辑
-> 返回 JSON 结果
```

**会话强制规则** (`MCPSessionManager`):
- 必须先调用 `aidp_context`，否则其他工具调用返回 `CONTEXT_REQUIRED` 错误
- 免检工具: `aidp_context`, `aidp_init`, `list_registered_tools`, `check_tool_health`, `sync_tool_capabilities`, `aidp_instructions`
- 会话超时: 30 分钟

### 4. Web UI

统一 Web UI 架构 (详见 `apps/controller/WEB_UI_ARCHITECTURE.md`):

```
浏览器 -> / -> layouts/workspace.html -> Jinja2 渲染
         |--- /login -> auth/login.html
         |--- /tools -> pages/tools.html (Alpine.js SPA)
         |--- /projects -> pages/projects_new.html
         |--- /api/proxy/{tool}/{path} -> 代理转发到工具
```

**前端技术**: Alpine.js 3.x + Tailwind CSS + Jinja2 + Font Awesome 6
**核心 JS**:
- `static/js/core/api.js` - API 客户端
- `static/js/core/store.js` - 状态管理
- `static/js/core/events.js` - 事件总线
- `static/js/services/toolService.js` - 工具服务
- `static/js/services/proxyService.js` - 代理服务


## 数据流: 用户查询处理全过程

以下展示一个完整的用户查询 "修复登录页 cookie 问题" 的处理流程:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MCP Client (AI Agent)                        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ POST /mcp (Streamable-HTTP)
                               │ tool: "aidp_context" (必须第一步)
                               v
┌─────────────────────────────────────────────────────────────────────┐
│  Controller :: SessionManager                                         │
│  -> 检查/创建 MCPSession                                                │
│  -> mark_context_loaded                                                │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               v
┌─────────────────────────────────────────────────────────────────────┐
│  Controller :: ContextPipeline.execute()                              │
│                                                                       │
│  Stage 0: _stage_0_load_instructions                                  │
│  -> SELECT FROM agent_instructions WHERE project_id=? AND agent_type=? │
│  -> 获取角色定义: "You are a helpful AI assistant..."                   │
│  -> 获取约束规则: [{"Always provide code examples",...}]               │
│                                                                       │
│  Stage 1: _stage_1_intent_analysis                                    │
│  -> ToolInvoker.invoke("skill-router", "analyze_intent", {...})        │
│  -> 意图: "bugfix", 领域: ["security","frontend"], 复杂度: "simple"     │
│                                                                       │
│  Stage 2: _stage_2_staged_retrieval (并行调用)                         │
│  |-- memory-tool "memory.search"     -> 2 条相关记忆                     │
│  |-- knowledge-tool "knowledge.search" -> 4 篇相关文档                   │
│  |-- asset-tool "search"              -> 1 个代码片段                    │
│  -> ContextCache 缓存结果 (TTL 300s)                                    │
│                                                                       │
│  Stage 3: _stage_3_skill_matching                                     │
│  -> ToolInvoker.invoke("skill-router", "skill_run", {...})             │
│  -> 匹配 3 个 skill, 2 条 rule                                          │
│                                                                       │
│  Stage 4: _stage_4_assembly                                            │
│  -> ContextAssembler.assemble(contexts, max_tokens=8000)               │
│  -> 去重、排序、截断、生成 system_prompt                                │
│  -> Token 估算: ~1800 tokens                                           │
│                                                                       │
│  返回: PipelineContext(trace_id, instructions, intent, memories,      │
│         knowledge, assets, skills, rules, assembled_context)          │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ 返回 JSON 上下文给 Agent
                               v
┌─────────────────────────────────────────────────────────────────────┐
│  MCP Client 收到上下文，开始执行开发任务                                 │
│                                                                       │
│  -> invoke_tool_mcp("sandbox-tool", "sandbox.execute",                 │
│                    '{"code":"...","language":"python"}')              │
│                                                                       │
│  -> Controller::SessionManager.can_call_tool()                         │
│    检查: context_loaded=True -> 允许调用                                │
│                                                                       │
│  -> ToolInvoker.invoke("sandbox-tool", "sandbox.execute", args)        │
│    POST http://127.0.0.1:18083/tool/invoke                             │
│                                                                       │
│  -> invoke_tool_mcp("quality-tool", "quality.check",                    │
│                    '{"code":"...","filename":"auth.py"}')             │
│    POST http://127.0.0.1:18084/tool/invoke                             │
│                                                                       │
│  -> invoke_tool_mcp("memory-tool", "memory.create",                    │
│                    '{"project":"aidp","category":"bugfix",...}')      │
│    归档修复经验                                                        │
└─────────────────────────────────────────────────────────────────────┘
```

## 完整目录结构

```
openCode/
├── apps/
│   └── controller/                     # 主控服务
│       ├── app/
│       │   ├── main.py                 # FastAPI 应用入口, lifespan 管理
│       │   ├── _config.py              # Settings(PORT=8883)
│       │   ├── api/                    # REST API 路由
│       │   │   ├── health.py           # /health
│       │   │   ├── tools.py            # /api/tools
│       │   │   ├── auth.py             # /api/auth
│       │   │   ├── metrics.py          # /api/metrics (Prometheus)
│       │   │   ├── audit.py            # /api/audit
│       │   │   ├── configs.py          # /api/configs
│       │   │   ├── reviews.py          # /api/reviews
│       │   │   ├── nas_storage.py      # NAS 存储
│       │   │   ├── instructions.py     # Agent 指令
│       │   │   ├── models.py           # 模型 API
│       │   │   ├── settings.py         # 系统设置
│       │   │   ├── ws_logs.py          # WebSocket 日志
│       │   │   └── classification.py   # 文档分类
│       │   ├── mcp/
│       │   │   ├── server.py           # FastMCP("aidp-controller"), 7 个 MCP 工具
│       │   │   └── session_manager.py  # MCPSessionManager 强制上下文调用
│       │   ├── models/
│       │   │   ├── instructions.py     # AgentInstruction 模型
│       │   │   ├── review.py           # Review 模型
│       │   │   └── project_new.py      # Project, ProjectMember, ProjectSettings
│       │   ├── modules/                # AIDP 统一平台模块
│       │   │   ├── __init__.py         # init_all_modules, shutdown_all_modules
│       │   │   ├── knowledge/          # 知识库模块 (KnowledgeBase, KnowledgeDocument, DocumentChunk)
│       │   │   ├── memory/             # 记忆模块 (MemoryEntry, MemoryRelation, MemoryAccessLog)
│       │   │   ├── skills/             # 技能模块 (Skill, SkillGroup, SkillFile, SkillEvolution)
│       │   │   ├── assets/             # 资产模块 (Asset, AssetTag)
│       │   │   ├── sandbox/            # 沙箱模块 (Execution)
│       │   │   ├── quality/            # 质量模块 (CheckResult)
│       │   │   ├── rules/              # 规则模块 (Rule, RuleGroup)
│       │   │   ├── agents/             # Agent 模块 (Agent)
│       │   │   └── workflows/          # 工作流模块 (Workflow, WorkflowStep, WorkflowExecution)
│       │   ├── services/
│       │   │   ├── tool_registry.py    # 工具注册、健康检查、能力同步
│       │   │   ├── tool_invoker.py     # ToolInvoker 类，HTTP 调用工具
│       │   │   ├── context_pipeline.py # ContextPipeline 5 阶段管线
│       │   │   ├── context_assembly.py # ContextAssembler (max_tokens=8000)
│       │   │   ├── context_cache.py    # ContextCache (TTL=300s)
│       │   │   ├── tool_retry.py       # ToolRetryManager (max_retries=3, EXPONENTIAL)
│       │   │   ├── auth_service.py     # AuthService, PermissionService
│       │   │   ├── project_init_service.py # 项目初始化
│       │   │   ├── project_service.py  # 项目业务逻辑
│       │   │   ├── config_service.py   # 配置管理
│       │   │   ├── model_service.py    # ModelService
│       │   │   ├── semantic_search.py  # 语义搜索
│       │   │   ├── review_service.py   # 评审逻辑
│       │   │   ├── seed_data.py        # 种子数据
│       │   │   ├── doc_classifier.py   # 文档分类器
│       │   │   ├── web_import_service.py # 网页导入
│       │   │   └── nas_storage_service.py # NAS 存储
│       │   ├── db/
│       │   │   ├── database.py         # SQLAlchemy engine, async_session_factory
│       │   │   ├── models.py           # ToolRegistry 模型
│       │   │   ├── auth_models.py      # User, Project, Permission 模型
│       │   │   └── init_db.py          # 数据库初始化
│       │   ├── web/
│       │   │   ├── routes.py           # 60+ Web 路由 (Jinja2 模板)
│       │   │   ├── auth.py             # Web 认证辅助
│       │   │   ├── templates/          # Jinja2 模板
│       │   │   │   ├── layouts/        # 布局模板 (base.html, workspace.html)
│       │   │   │   ├── pages/          # 页面模板 (dashboard, tools, projects, project_dashboard...)
│       │   │   │   ├── modules/        # 模块模板 (knowledge, memory, skills, assets, sandbox, quality, rules, agents, workflows)
│       │   │   │   ├── auth/           # 认证模板 (login, profile, api_keys)
│       │   │   │   └── admin/          # 管理后台模板 (users, roles, models, settings, projects, skills, audit_logs)
│       │   │   └── static/
│       │   │       ├── js/             # Alpine.js 前端代码
│       │   │       │   ├── aidp.js     # 主入口 (AIDP 命名空间)
│       │   │       │   ├── core/       # 核心模块 (api.js, store.js, events.js)
│       │   │       │   ├── services/   # 业务服务 (toolService.js, proxyService.js)
│       │   │       │   └── components/ # 组件 (ToolCard.js, StatusBadge.js, DataTable.js)
│       │   │       ├── css/            # 样式文件
│       │   │       └── vendor/         # 第三方库 (tailwind.js)
│       │   ├── routers/
│       │   │   └── projects_new.py     # 项目 API 路由
│       │   ├── config/                 # 配置模块
│       │   │   └── menu.yaml           # 动态菜单配置
│       │   └── security/               # 安全模块
│       ├── Dockerfile                  # Python 3.13-slim, EXPOSE 8883
│       ├── docker-compose.yml          # 独立部署配置 (network_mode: host)
│       ├── requirements.txt            # 18 个依赖
│       ├── tool.yaml                   # 工具能力声明
│       └── WEB_UI_ARCHITECTURE.md      # Web UI 架构文档
│
├── tools/
│   ├── skill-router/                   # 技能路由引擎
│   │   ├── app/
│   │   │   ├── main.py                 # FastMCP("SkillRouter"), 端口 8788
│   │   │   ├── config.py               # Settings (LLM, Embedding, DB 配置, 含校验器)
│   │   │   ├── mcp/tools.py            # MCP 工具注册
│   │   │   ├── api/routes.py           # REST API (/api/...)
│   │   │   ├── api/tool.py             # /tool/invoke 端点
│   │   │   ├── model_client.py         # LLM 调用客户端
│   │   │   ├── services/               # 业务服务层
│   │   │   ├── db/init_db.py           # 数据库初始化 (PostgreSQL + pgvector + Redis)
│   │   │   ├── web/                    # Web UI (auth.py, routes.py)
│   │   │   ├── i18n/                   # 国际化
│   │   │   └── static/                 # 静态资源
│   │   ├── cli/                        # CLI 工具
│   │   ├── Dockerfile                  # Python 3.13-slim, EXPOSE 8788, 含 gcc libpq-dev
│   │   ├── docker-compose.yml          # network_mode: host
│   │   ├── requirements.txt            # 16 个依赖 (含 pgvector, redis, bcrypt, alembic)
│   │   └── README.md
│   │
│   ├── knowledge-tool/                 # 文档知识库
│   │   ├── app/
│   │   │   ├── main.py                 # FastAPI (knowledge-tool), 端口 18081
│   │   │   ├── config.py               # PORT=18081, CHUNK_SIZE=800, EMBEDDING_PROVIDER=mock
│   │   │   ├── api/                    # documents, ingest, search, knowledge_bases, bindings, import_web
│   │   │   ├── chunk/                  # 文档分块引擎 (chunk_size=800, overlap=120)
│   │   │   ├── embedding/              # 向量化 (mock/openai/local 三种 Provider)
│   │   │   ├── search/                 # 混合检索 (hybrid 模式, top_k=8)
│   │   │   ├── parser/                 # 文档解析 (Markdown)
│   │   │   ├── storage/                # 文件存储 (local Provider)
│   │   │   ├── schemas/                # Pydantic 模型
│   │   │   └── web/                    # 内嵌 Web UI
│   │   ├── Dockerfile                  # Python 3.13-slim, EXPOSE 18081
│   │   ├── requirements.txt            # 13 个依赖 (含 sentence-transformers, beautifulsoup4)
│   │   └── README.md
│   │
│   ├── asset-tool/                     # 代码资产管理
│   │   ├── app/
│   │   │   ├── main.py                 # FastAPI (asset-tool), 端口 18082
│   │   │   ├── config.py               # PORT=18082, SEARCH_DEFAULT_TOP_K=8
│   │   │   ├── api/assets.py           # 资产 CRUD
│   │   │   ├── schemas/                # Pydantic 模型
│   │   │   └── web/                    # Web UI
│   │   ├── Dockerfile                  # EXPOSE 18082
│   │   └── requirements.txt
│   │
│   ├── sandbox-tool/                   # 代码沙箱
│   │   ├── app/
│   │   │   ├── main.py                 # FastAPI (sandbox-tool), 端口 18083
│   │   │   ├── config.py               # PORT=18083, EXECUTION_TIMEOUT=30, MAX_OUTPUT=10240
│   │   │   ├── api/execute.py          # 代码执行端点
│   │   │   ├── services/               # 执行逻辑
│   │   │   └── web/                    # Web UI
│   │   ├── Dockerfile                  # aidp/sandbox-tool:0.1.0, EXPOSE 18083
│   │   ├── docker-compose.yml          # network_mode: host, PostgreSQL
│   │   └── requirements.txt            # 9 个依赖
│   │
│   ├── quality-tool/                   # 质量检查
│   │   ├── app/
│   │   │   ├── main.py                 # FastAPI (quality-tool), 端口 18084
│   │   │   ├── config.py               # PORT=18084, LINT_MAX_LINE_LENGTH=120
│   │   │   ├── api/check.py            # 检查端点
│   │   │   ├── analyzers/              # 分析引擎
│   │   │   │   ├── rule_engine.py      # 规则匹配引擎
│   │   │   │   ├── language_adapter.py # 多语言适配
│   │   │   │   └── semantic_duplication.py # 语义重复检测
│   │   │   ├── services/               # 服务层
│   │   │   └── web/                    # Web UI
│   │   ├── Dockerfile                  # aidp/quality-tool:0.1.0, EXPOSE 18084
│   │   ├── docker-compose.yml          # network_mode: host, PostgreSQL
│   │   └── requirements.txt            # 9 个依赖
│   │
│   ├── memory-tool/                    # 项目记忆
│   │   ├── app/
│   │   │   ├── main.py                 # FastAPI (memory-tool), 端口 18085
│   │   │   ├── config.py               # PORT=18085, MEMORY_DEFAULT_LIMIT=50, MAX_LIMIT=200
│   │   │   ├── api/                    # memory, memories(v2), graph, search, context, review
│   │   │   ├── schemas/                # Pydantic 模型
│   │   │   ├── services/               # 业务服务
│   │   │   └── web/                    # Web UI
│   │   ├── Dockerfile                  # EXPOSE 18085
│   │   ├── requirements.txt            # 10 个依赖 (含 pgvector)
│   │   └── README.md
│   │
│   ├── code-index/                     # 代码索引
│   │   ├── app/
│   │   │   ├── main.py                 # FastAPI (Code Index Tool), 端口 18086
│   │   │   ├── config.py               # PORT=18086, SQLite (data/code_index.db)
│   │   │   ├── api/                    # health, code_index, tool
│   │   │   ├── services/               # 索引服务
│   │   │   ├── model_client.py         # 嵌入模型客户端
│   │   │   └── db/                     # 数据库层
│   │   ├── Dockerfile                  # EXPOSE 18086
│   │   ├── requirements.txt            # 10 个依赖
│   │   └── tool.yaml                   # 能力: code.explore, search, scan, calls, dependents, structure
│   │
│   ├── doc-index/                      # 文档索引
│   │   ├── app/
│   │   │   ├── main.py                 # FastAPI (Doc Index Tool), 端口 18087
│   │   │   ├── config.py               # PORT=18087, SQLite (data/doc_index.db)
│   │   │   ├── api/doc_index.py        # 文档索引端点
│   │   │   └── services/               # 索引服务
│   │   ├── Dockerfile                  # EXPOSE 18087
│   │   ├── requirements.txt            # 11 个依赖 (含 markdown, beautifulsoup4, lxml)
│   │   └── tool.yaml
│   │
│   ├── context-optimizer/              # 上下文优化
│   │   ├── app/
│   │   │   ├── main.py                 # FastAPI (Context Optimizer), 端口 18088
│   │   │   ├── config.py               # PORT=18088, DEFAULT_BUDGET=8000, MAX_BUDGET=32000
│   │   │   ├── api/optimize.py         # 优化端点
│   │   │   └── services/               # 优化逻辑
│   │   ├── Dockerfile                  # EXPOSE 18088
│   │   └── tool.yaml
│   │
│   ├── evolution-engine/               # 自演进引擎
│   │   ├── app/
│   │   │   ├── main.py                 # FastAPI (Evolution Engine), 端口 18089
│   │   │   ├── config.py               # PORT=18089, LLM=qwen2.5:7b, BATCH_SIZE=10
│   │   │   ├── api/events.py           # 事件端点
│   │   │   └── services/               # 分析逻辑
│   │   ├── Dockerfile                  # EXPOSE 18089
│   │   └── tool.yaml
│   │
│   ├── project-importer/               # 项目导入器
│   │   ├── app/
│   │   │   ├── main.py                 # FastAPI (Project Importer), 端口 18090
│   │   │   └── tech_analyzer.py        # 技术栈分析器
│   │   ├── Dockerfile                  # EXPOSE 18090
│   │   └── requirements.txt
│   │
│   ├── file-watcher/                   # 文件监听
│   │   ├── app/
│   │   │   ├── main.py                 # FastAPI (File Watcher Tool), 端口 18091, 启动时恢复监听
│   │   │   ├── config.py               # PORT=18091, DEBOUNCE_SECONDS=1.0
│   │   │   ├── api/watcher.py          # 监听端点
│   │   │   ├── services/watcher.py     # watcher_service (文件系统观察者)
│   │   │   └── services/project_mapper.py # ProjectMapper (活动项目映射)
│   │   ├── Dockerfile                  # EXPOSE 18091
│   │   └── tool.yaml
│   │
│   └── importer-tool/                  # 内容导入工具
│       ├── app/
│       │   ├── main.py                 # FastAPI (importer-tool), 端口 18085 (与 memory 冲突)
│       │   ├── config.py               # PORT=18085, MAX_FILE_SIZE_MB=5
│       │   └── api/tool.py             # 工具端点
│       ├── Dockerfile                  # EXPOSE 18085
│       └── tool.yaml
│
├── deploy/                             # 部署脚本
│   └── deploy-nas.ps1                  # NAS 全量部署脚本
├── docs/                               # 文档
├── docker-compose.yml                  # 顶层编排 (controller + sandbox + quality)
├── .env.example                        # 环境变量模板
├── package.json                        # 项目元信息 (含 playwright)
└── README.md
```
