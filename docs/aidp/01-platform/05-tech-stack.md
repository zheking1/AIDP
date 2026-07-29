# AIDP 技术栈

## 运行时环境

| 组件 | 版本 | 说明 |
|------|------|------|
| **Python** | 3.13 | 所有服务的基础运行时 |
| **Docker** | 24+ | 容器化部署 |
| **Docker Compose** | v2 | 多服务编排 |

## 服务技术栈详情

### 1. Controller (`apps/controller/`)

| 技术 | 版本 | 用途 | 来源 |
|------|------|------|------|
| FastAPI | >=0.115.0 | Web 框架 | `requirements.txt:1` |
| Uvicorn | >=0.30.0 (standard) | ASGI 服务器 | `requirements.txt:2` |
| SQLAlchemy | >=2.0 (asyncio) | 异步 ORM | `requirements.txt:5` |
| asyncpg | >=0.30.0 | PostgreSQL 异步驱动 | `requirements.txt:6` |
| aiosqlite | >=0.19.0 | SQLite 异步驱动 | `requirements.txt:7` |
| FastMCP | >=3.0.0 | MCP Server 框架 | `requirements.txt:10` |
| httpx | >=0.27.0 | HTTP 客户端 (工具调用) | `requirements.txt:8` |
| Jinja2 | >=3.0.0 | 模板引擎 | `requirements.txt:11` |
| Pydantic | >=2.0 | 数据验证 | `requirements.txt:3` |
| Pydantic-Settings | >=2.0 | 配置管理 | `requirements.txt:4` |
| python-multipart | >=0.0.9 | 文件上传 | `requirements.txt:9` |
| prometheus-client | >=0.20.0 | 指标暴露 | `requirements.txt:12` |
| Redis | >=5.0.0 | 缓存 | `requirements.txt:13` |
| PyJWT | >=2.8.0 | JWT 令牌 | `requirements.txt:14` |
| itsdangerous | >=2.1.0 | 会话签名 | `requirements.txt:15` |
| bcrypt | >=4.1.0 | 密码哈希 | `requirements.txt:16` |
| beautifulsoup4 | >=4.12.0 | HTML 解析 | `requirements.txt:17` |
| lxml | >=5.0.0 | XML/HTML 解析 | `requirements.txt:18` |

**数据库**: PostgreSQL (通过 `asyncpg`)，SQLite (通过 `aiosqlite`)

### 2. Skill Router (`tools/skill-router/`)

| 技术 | 版本 | 用途 | 来源 |
|------|------|------|------|
| FastAPI | >=0.115.0 | Web 框架 | `requirements.txt:1` |
| Uvicorn | >=0.30.0 (standard) | ASGI 服务器 | `requirements.txt:2` |
| FastMCP | >=0.3.0 | MCP Server 框架 | `requirements.txt:3` |
| SQLAlchemy | >=2.0.0 (asyncio) | 异步 ORM | `requirements.txt:4` |
| greenlet | >=3.0.0 | 协程支持 | `requirements.txt:5` |
| asyncpg | >=0.30.0 | PostgreSQL 异步驱动 | `requirements.txt:6` |
| pgvector | >=0.3.0 | PostgreSQL 向量扩展 | `requirements.txt:7` |
| Redis | >=5.0.0 (hiredis) | 缓存 | `requirements.txt:8` |
| httpx | >=0.27.0 | HTTP 客户端 | `requirements.txt:9` |
| bcrypt | >=4.2.0 | 密码哈希 | `requirements.txt:10` |
| Jinja2 | >=3.1.0 | 模板引擎 | `requirements.txt:11` |
| python-multipart | >=0.0.12 | 文件上传 | `requirements.txt:12` |
| Pydantic | >=2.0.0 | 数据验证 | `requirements.txt:13` |
| Pydantic-Settings | >=2.0.0 | 配置管理 | `requirements.txt:14` |
| alembic | >=1.13.0 | 数据库迁移 | `requirements.txt:15` |
| itsdangerous | >=2.2.0 | 会话签名 | `requirements.txt:16` |

**数据库**: PostgreSQL + pgvector + Redis
**配置** (`app/config.py`):
- LLM 端点: 可配置 (默认 `http://localhost:8000/v1`)
- LLM 模型: 默认 `deepseek-v4-flash-free`
- Embedding 模型: 默认 `text-embedding-3-small`
- Embedding 维度: 默认 `1024`
- 缓存 TTL: 默认 `3600` 秒

### 3. Code Index (`tools/code-index/`)

| 技术 | 版本 | 用途 | 来源 |
|------|------|------|------|
| FastAPI | >=0.100.0 | Web 框架 | `requirements.txt:1` |
| Uvicorn | >=0.24.0 (standard) | ASGI 服务器 | `requirements.txt:2` |
| SQLAlchemy | >=2.0 | ORM | `requirements.txt:5` |
| aiosqlite | >=0.19 | SQLite 异步驱动 | `requirements.txt:6` |
| Pydantic | >=2.0 | 数据验证 | `requirements.txt:3` |
| Pydantic-Settings | >=2.0 | 配置管理 | `requirements.txt:4` |
| Jinja2 | >=3.1.0 | 模板引擎 | `requirements.txt:7` |
| aiofiles | >=23.0 | 异步文件 I/O | `requirements.txt:8` |
| python-multipart | >=0.0.6 | 文件上传 | `requirements.txt:9` |
| httpx | >=0.27.0 | HTTP 客户端 | `requirements.txt:10` |

**额外依赖**:
- **Tree-Sitter**: AST 解析 (代码结构提取，符号索引)
- **BGE-M3**: 代码嵌入模型 (通过 SiliconFlow API, 1024-dim)

**数据库**: SQLite (`data/code_index.db`)
**配置** (`app/config.py`): `PORT=18086`

### 4. Knowledge Tool (`tools/knowledge-tool/`)

| 技术 | 版本 | 用途 | 来源 |
|------|------|------|------|
| FastAPI | >=0.115.0 | Web 框架 | `requirements.txt:1` |
| Uvicorn | >=0.30.0 (standard) | ASGI 服务器 | `requirements.txt:2` |
| SQLAlchemy | >=2.0 (asyncio) | 异步 ORM | `requirements.txt:5` |
| asyncpg | >=0.30.0 | PostgreSQL 异步驱动 | `requirements.txt:6` |
| aiosqlite | >=0.20.0 | SQLite 异步驱动 | `requirements.txt:7` |
| httpx | >=0.27.0 | HTTP 客户端 | `requirements.txt:8` |
| python-multipart | >=0.0.9 | 文件上传 | `requirements.txt:9` |
| Jinja2 | >=3.1.0 | 模板引擎 | `requirements.txt:10` |
| aiofiles | >=24.0.0 | 异步文件 I/O | `requirements.txt:11` |
| beautifulsoup4 | >=4.12.0 | HTML 解析 | `requirements.txt:12` |
| sentence-transformers | >=3.0.0 | 本地向量化 | `requirements.txt:13` |
| Pydantic | >=2.0 | 数据验证 | `requirements.txt:3` |
| Pydantic-Settings | >=2.0 | 配置管理 | `requirements.txt:4` |

**数据库**: SQLite (默认) 或 PostgreSQL
**配置** (`app/config.py`):
- `CHUNK_DEFAULT_SIZE`: `800`
- `CHUNK_DEFAULT_OVERLAP`: `120`
- `SEARCH_DEFAULT_TOP_K`: `8`
- `SEARCH_DEFAULT_MODE`: `"hybrid"` (BM25 + Vector)
- `UPLOAD_MAX_FILE_SIZE_MB`: `50`

### 5. Memory Tool (`tools/memory-tool/`)

| 技术 | 版本 | 用途 | 来源 |
|------|------|------|------|
| FastAPI | >=0.115.0 | Web 框架 | `requirements.txt:1` |
| Uvicorn | >=0.30.0 (standard) | ASGI 服务器 | `requirements.txt:2` |
| SQLAlchemy | >=2.0 (asyncio) | 异步 ORM | `requirements.txt:5` |
| asyncpg | >=0.30.0 | PostgreSQL 异步驱动 | `requirements.txt:6` |
| httpx | >=0.27.0 | HTTP 客户端 | `requirements.txt:7` |
| python-multipart | >=0.0.9 | 文件上传 | `requirements.txt:8` |
| Jinja2 | >=3.1.0 | 模板引擎 | `requirements.txt:9` |
| pgvector | >=0.2.0 | PostgreSQL 向量扩展 | `requirements.txt:10` |
| Pydantic | >=2.0 | 数据验证 | `requirements.txt:3` |
| Pydantic-Settings | >=2.0 | 配置管理 | `requirements.txt:4` |

**数据库**: SQLite 或 PostgreSQL + pgvector
**配置** (`app/config.py`): `PORT=18085`, `MEMORY_DEFAULT_LIMIT=50`, `MEMORY_MAX_LIMIT=200`

### 6. Doc Index (`tools/doc-index/`)

| 技术 | 版本 | 用途 | 来源 |
|------|------|------|------|
| FastAPI | >=0.100.0 | Web 框架 | `requirements.txt:1` |
| Uvicorn | >=0.24.0 (standard) | ASGI 服务器 | `requirements.txt:2` |
| SQLAlchemy | >=2.0 | ORM | `requirements.txt:5` |
| aiosqlite | >=0.19 | SQLite 异步驱动 | `requirements.txt:6` |
| Pydantic | >=2.0 | 数据验证 | `requirements.txt:3` |
| Pydantic-Settings | >=2.0 | 配置管理 | `requirements.txt:4` |
| Jinja2 | >=3.1.0 | 模板引擎 | `requirements.txt:7` |
| aiofiles | >=23.0 | 异步文件 I/O | `requirements.txt:8` |
| markdown | >=3.5 | Markdown 解析 | `requirements.txt:9` |
| beautifulsoup4 | >=4.12 | HTML 解析 | `requirements.txt:10` |
| lxml | >=5.0 | XML/HTML 解析 | `requirements.txt:11` |

**数据库**: SQLite (`data/doc_index.db`)
**配置** (`app/config.py`): `PORT=18087`

### 7. Sandbox Tool (`tools/sandbox-tool/`)

| 技术 | 版本 | 用途 | 来源 |
|------|------|------|------|
| FastAPI | >=0.115.0 | Web 框架 | `requirements.txt:1` |
| Uvicorn | >=0.30.0 (standard) | ASGI 服务器 | `requirements.txt:2` |
| SQLAlchemy | >=2.0 (asyncio) | 异步 ORM | `requirements.txt:5` |
| asyncpg | >=0.30.0 | PostgreSQL 异步驱动 | `requirements.txt:6` |
| httpx | >=0.27.0 | HTTP 客户端 | `requirements.txt:7` |
| python-multipart | >=0.0.9 | 文件上传 | `requirements.txt:8` |
| Jinja2 | >=3.1.0 | 模板引擎 | `requirements.txt:9` |
| Pydantic | >=2.0 | 数据验证 | `requirements.txt:3` |
| Pydantic-Settings | >=2.0 | 配置管理 | `requirements.txt:4` |

**执行方式**: subprocess 子进程隔离
**配置** (`app/config.py`):
- `EXECUTION_TIMEOUT`: `30` 秒
- `EXECUTION_MAX_OUTPUT`: `10240` 字节

### 8. Quality Tool (`tools/quality-tool/`)

| 技术 | 版本 | 用途 | 来源 |
|------|------|------|------|
| FastAPI | >=0.115.0 | Web 框架 | `requirements.txt:1` |
| Uvicorn | >=0.30.0 (standard) | ASGI 服务器 | `requirements.txt:2` |
| SQLAlchemy | >=2.0 (asyncio) | 异步 ORM | `requirements.txt:5` |
| asyncpg | >=0.30.0 | PostgreSQL 异步驱动 | `requirements.txt:6` |
| httpx | >=0.27.0 | HTTP 客户端 | `requirements.txt:7` |
| python-multipart | >=0.0.9 | 文件上传 | `requirements.txt:8` |
| Jinja2 | >=3.1.0 | 模板引擎 | `requirements.txt:9` |
| Pydantic | >=2.0 | 数据验证 | `requirements.txt:3` |
| Pydantic-Settings | >=2.0 | 配置管理 | `requirements.txt:4` |

**分析引擎** (`app/analyzers/`):
- `rule_engine.py` - 规则匹配引擎 (正则检查)
- `language_adapter.py` - 多语言适配器
- `semantic_duplication.py` - 语义重复检测

**检查项目** (`app/config.py`):
- `LINT_MAX_LINE_LENGTH`: `120`
- `LINT_CHECK_TRAILING_WHITESPACE`: `True`
- `LINT_CHECK_MISSING_NEWLINE`: `True`
- `SECURITY_CHECK_HARDCODED_SECRETS`: `True`
- `SECURITY_CHECK_SQL_INJECTION`: `True`
- `SECURITY_CHECK_DANGEROUS_FUNCTIONS`: `True`


### 9. Asset Tool (`tools/asset-tool/`)

| 技术 | 版本 | 用途 |
|------|------|------|
| FastAPI | >=0.115.0 | Web 框架 |
| Uvicorn | >=0.30.0 (standard) | ASGI 服务器 |
| SQLAlchemy | >=2.0 (asyncio) | 异步 ORM |
| Pydantic | >=2.0 | 数据验证 |

**数据库**: SQLite 或 PostgreSQL
**配置**: `PORT=18082`, `SEARCH_DEFAULT_TOP_K=8`, `UPLOAD_MAX_CONTENT_SIZE_MB=10`

### 10. Context Optimizer (`tools/context-optimizer/`)

| 技术 | 版本 | 用途 |
|------|------|------|
| FastAPI | >=0.100.0 | Web 框架 |
| Uvicorn | >=0.24.0 | ASGI 服务器 |
| SQLAlchemy | >=2.0 | ORM |
| aiosqlite | >=0.19 | SQLite 异步驱动 |

**数据库**: SQLite (`data/context_optimizer.db`)
**配置**: `PORT=18088`, `DEFAULT_BUDGET=8000`, `MAX_BUDGET=32000`
**工具优先级**: code_index(1.5) > knowledge(1.2) > memory(1.0) > asset(0.8) > quality(0.5) > sandbox(0.3)

### 11. Evolution Engine (`tools/evolution-engine/`)

| 技术 | 版本 | 用途 |
|------|------|------|
| FastAPI | >=0.100.0 | Web 框架 |
| Uvicorn | >=0.24.0 | ASGI 服务器 |
| SQLAlchemy | >=2.0 | ORM |
| aiosqlite | >=0.19 | SQLite 异步驱动 |

**数据库**: SQLite (`data/evolution_engine.db`)
**配置**: `PORT=18089`, `LLM_MODEL=qwen2.5:7b`, `BATCH_SIZE=10`

### 12. Project Importer (`tools/project-importer/`)

| 技术 | 版本 | 用途 |
|------|------|------|
| FastAPI | - | Web 框架 |
| Uvicorn | - | ASGI 服务器 |
| httpx | - | HTTP 客户端 (调用各工具端点) |

**运行时**: Python 3.13-slim
**配置**: `PORT=18090`, 内部调用 Controller(8883), Code Index(18086), Knowledge(18081), Memory(18085)

### 13. File Watcher (`tools/file-watcher/`)

| 技术 | 版本 | 用途 |
|------|------|------|
| FastAPI | >=0.100.0 | Web 框架 |
| Uvicorn | >=0.24.0 | ASGI 服务器 |
| SQLAlchemy | >=2.0 | ORM |
| aiosqlite | >=0.19 | SQLite 异步驱动 |

**数据库**: SQLite (`data/file_watcher.db`)
**配置**: `PORT=18091`, `DEBOUNCE_SECONDS=1.0`, 监控 Controller(8883) 和 Code Index(18086)

## Web UI 前端栈

| 技术 | 用途 | 说明 |
|------|------|------|
| **Alpine.js** 3.x | 响应式前端框架 | 轻量级 SPA，声明式数据绑定 |
| **Tailwind CSS** | 样式框架 | 通过 vendor/tailwind.js (CDN) 引入 |
| **Jinja2** >=3.0.0 | 服务端模板 | 页面布局和渲染 (apps/controller/app/web/templates/) |
| **Font Awesome** 6 | 图标库 | Web UI 图标 |
| **Fetch API** (Native) | HTTP 客户端 | 前端 API 调用 |

**前端架构** (详见 `apps/controller/WEB_UI_ARCHITECTURE.md`):
```
Layer 4: Presentation Layer  (layouts, pages, components)
Layer 3: Application Layer   (ToolService, ProxyService, Store, EventBus)
Layer 2: API Layer           (REST Client, Proxy API)
Layer 1: Infrastructure      (Fetch API, Auth Middleware)
```

**核心 JS 模块** (`apps/controller/app/web/static/js/`):
- `core/api.js` - API 客户端 (统一错误处理、自动重试、超时控制)
- `core/store.js` - 中心化状态管理 (get/set/subscribe)
- `core/events.js` - 事件总线 (组件通信)
- `services/toolService.js` - 工具管理业务逻辑
- `services/proxyService.js` - 工具 Web UI 代理
- `components/ToolCard.js` - 工具卡片组件
- `components/StatusBadge.js` - 状态徽章组件
- `components/DataTable.js` - 数据表格组件

## 基础设施

### Docker 镜像

所有服务统一使用 Python 3.13-slim 基础镜像:
- 镜像仓库: `docker.1ms.run/library/python:3.13-slim`
- 工作目录: `/app`
- 数据目录: `/app/data`

**有预构建镜像的服务**:
- `aidp/controller:0.1.0` (controller)
- `aidp/sandbox-tool:0.1.0` (sandbox-tool)
- `aidp/quality-tool:0.1.0` (quality-tool)

其余工具通过各自目录下的 `Dockerfile` 本地构建。

### 容器网络

所有 docker-compose 配置均使用 `network_mode: host`，直接暴露服务端口。

### 数据库

| 数据库 | 版本 | 用途 | 使用服务 |
|--------|------|------|---------|
| PostgreSQL | 16+ | 主数据库 (asyncpg) | controller, skill-router, sandbox, quality |
| pgvector | >=0.2.0 | 向量存储扩展 | skill-router, memory-tool |
| Redis | 7+ | 缓存 | controller (>=5.0.0), skill-router (>=5.0.0+hiredis) |
| SQLite | - (aiosqlite) | 轻量本地存储 | code-index, doc-index, knowledge-tool(可选), memory-tool(可选), asset-tool(可选), context-optimizer, evolution-engine, file-watcher |

### 连接字符串

默认连接配置 `docker-compose.yml`:
```
DATABASE_URL=postgresql+asyncpg://novel_os:CHANGE_ME@127.0.0.1:5432/aidp
REDIS_URL=redis://127.0.0.1:6379/0
CONTROLLER_SESSION_KEY=change-me-in-production
```

## LLM / AI 模型

### 大语言模型

| 模型 | 提供商 | 用途 | 配置位置 |
|------|--------|------|---------|
| **DeepSeek V4** | BaiduBCE | 主 LLM (chat, code) | skill-router `llm_model=deepseek-v4-flash-free` |
| **DeepSeek V3** | BaiduBCE | 备选 LLM | 可配置 |
| **GLM-5** | BaiduBCE | 备选 LLM | 可配置 |
| **ERNIE** | BaiduBCE | 备选 LLM | 可配置 |
| **Qwen 2.5 7B** | Local (Ollama) | 演进引擎分析 | evolution-engine `LLM_MODEL=qwen2.5:7b` |

**LLM 配置** (skill-router `app/config.py`):
```python
llm_endpoint: str = "http://localhost:8000/v1"  # LLM API 端点
llm_api_key: str = "sk-xxx"                      # LLM API 密钥
llm_model: str = "deepseek-v4-flash-free"        # 默认模型
llm_timeout: int = 30                            # 超时(秒)
```

### 嵌入模型

| 模型 | 提供商 | 维度 | 用途 | 配置位置 |
|------|--------|------|------|---------|
| **BGE-M3** | SiliconFlow | 1024 | 代码/文档向量化 | skill-router `embedding_dim=1024` |
| **text-embedding-3-small** | OpenAI | 可配置 | 备选嵌入 | skill-router `embedding_model=text-embedding-3-small` |
| **sentence-transformers** | Local | - | 本地向量化 | knowledge-tool |

**Embedding 配置** (skill-router `app/config.py`):
```python
embedding_endpoint: str = "http://localhost:8000/v1"  # Embedding API 端点
embedding_api_key: str = "sk-xxx"                      # API 密钥
embedding_model: str = "text-embedding-3-small"        # 默认模型
embedding_dim: int = 1024                              # 维度(1-1536)
embedding_timeout: int = 15                            # 超时(秒)
```

### 生产安全检查

skill-router 配置在生产环境部署前会进行安全检查 (`app/config.py:74-93`):
- 检测默认密码 (`db_password == "change_me"`)
- 检测默认管理员密码 (`admin_password == "admin123"`)
- 检测占位 API Key (`llm_api_key == "sk-xxx"`)
- 检测占位 Embedding API Key (`embedding_api_key == "sk-xxx"`)

## 依赖汇总

### Python 公共依赖

所有服务共用的核心库:

| 库 | 最低版本 | 几乎所有服务使用 |
|----|---------|----------------|
| fastapi | >=0.100.0 | Controller, 所有工具 |
| uvicorn | >=0.24.0 | Controller, 所有工具 |
| pydantic | >=2.0 | Controller, 所有工具 |
| pydantic-settings | >=2.0 | Controller, 所有工具 |
| sqlalchemy | >=2.0 | Controller, 所有工具 |
| httpx | >=0.27.0 | Controller, 部分工具 |
| jinja2 | >=3.0.0 | Controller, 大部分工具 |
| python-multipart | >=0.0.6 | Controller, 大部分工具 |

### 独有依赖

| 服务 | 独有依赖 |
|------|---------|
| Controller | fastmcp >=3.0.0, prometheus-client, redis, PyJWT, itsdangerous, bcrypt, beautifulsoup4, lxml |
| Skill Router | fastmcp >=0.3.0, pgvector, redis[hiredis], bcrypt, alembic, greenlet |
| Knowledge Tool | sentence-transformers, beautifulsoup4, aiofiles |
| Memory Tool | pgvector |
| Code Index | aiosqlite, aiofiles |
| Doc Index | markdown, beautifulsoup4, lxml |
| Context Optimizer | aiosqlite (SQLite only) |
| Evolution Engine | aiosqlite (SQLite only) |
| File Watcher | aiosqlite (SQLite only) |
| Project Importer | httpx (纯 HTTP 客户端) |

## 版本说明

所有服务版本号统一为 `0.1.0`:
- `apps/controller/app/_config.py:6`: `APP_VERSION = "0.1.0"`
- `tools/skill-router/app/main.py:38`: `version="0.1.0"`
- `tools/code-index/app/config.py:6`: `APP_VERSION = "0.1.0"`
- `tools/knowledge-tool/app/config.py:6`: `APP_VERSION = "0.1.0"`
- `tools/memory-tool/app/config.py:6`: `APP_VERSION = "0.1.0"`
- `tools/doc-index/app/config.py:6`: `APP_VERSION = "0.1.0"`
- `tools/sandbox-tool/app/config.py:6`: `APP_VERSION = "0.1.0"`
- `tools/quality-tool/app/config.py:6`: `APP_VERSION = "0.1.0"`
- `docker-compose.yml:27`: `image: aidp/controller:0.1.0`
- `docker-compose.yml:37`: `image: aidp/sandbox-tool:0.1.0`
- `docker-compose.yml:45`: `image: aidp/quality-tool:0.1.0`
