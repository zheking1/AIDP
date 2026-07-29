# 编码规范

## 项目概述

AIDP 是一个 Python 为主的多服务项目，前端使用纯 JavaScript。以下规范从源码分析得出。

## Python 规范

### 框架与库

所有后端服务遵循统一模式:

| 组件 | 规范 | 示例 |
|------|------|------|
| Web 框架 | FastAPI (async) | `from fastapi import FastAPI` |
| ORM | SQLAlchemy 2.0 (async) | `from sqlalchemy.ext.asyncio import create_async_engine` |
| 配置管理 | Pydantic Settings | `from pydantic_settings import BaseSettings` |
| Web 服务器 | Uvicorn | - |
| 数据校验 | Pydantic (BaseModel) | `class XxxRequest(BaseModel)` |
| 异步 HTTP | httpx | `from httpx import AsyncClient` |

### 项目结构模式

```
tools/{tool_name}/app/
├── __init__.py
├── main.py              # FastAPI 应用 (lifespan, 路由注册)
├── config.py            # Settings(BaseSettings)
├── api/                 # API 路由
│   ├── __init__.py
│   ├── health.py        # /health 端点
│   └── tool.py          # /tool/manifest, /tool/capabilities, /tool/invoke
├── services/            # 业务逻辑
│   └── ...
├── db/                  # 数据库
│   ├── __init__.py
│   ├── models.py        # ORM 模型
│   └── init_db.py
├── analyzers/           # (可选) 分析模块
│   └── ...
└── web/                 # (可选) Web UI 路由
    ├── __init__.py
    └── routes.py
```

### 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 类名 | PascalCase | `Settings`, `Execution`, `ToolService` |
| 函数 | snake_case | `execute_code()`, `run_check()` |
| 模块/文件 | snake_case | `execution_service.py` |
| 常量 | UPPER_SNAKE | `EXECUTION_TIMEOUT`, `SUPPORTED_LANGUAGES` |
| 路由前缀 | `/api/{名词复数}` | `/api/tools`, `/api/execute` |

### FastAPI 应用入口模式

所有服务遵循相同的入口结构 (`main.py`):

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db.init_db import init_database

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_database()
    yield

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

app.include_router(health_router)
app.include_router(tool_router)
app.include_router(execute_router)    # 业务路由
app.include_router(web_router)        # (可选) Web UI 路由
```

### 配置管理模式

标准 `Settings` 类:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "tool-name"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 18xxx
    DATABASE_URL: str = ""
    DATABASE_ECHO: bool = False
    SECRET_KEY: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

settings = Settings()
```

### 数据库模式

统一的 SQLAlchemy async 模式:

```python
# models.py
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class MyModel(Base):
    __tablename__ = "table_name"
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DATABASE_ECHO)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_session():
    async with async_session() as session:
        yield session
```

**注意**: 所有服务使用独立的 `async_session` 定义，不共享数据库连接池。

### API 响应模式

| 场景 | 响应模式 |
|------|---------|
| 查询成功 | 直接返回 dict 或 list |
| 创建成功 | 返回实体 dict |
| 错误 | `{"error": "message"}` 或 `{"success": false, "error": {...}}` |
| MCP 调用 | `ToolInvokeResponse(trace_id, tool, capability, success, output, error, elapsed_ms)` |

### Controller 特有模式 (routes.py)

- 所有页面路由使用 `render_template()` 辅助函数
- `partial=1` 查询参数控制只返回内容片段
- `embed=True` 跳过布局包装
- 认证通过 `get_current_user_from_request()` 从 cookie 提取用户

## JavaScript 规范

### 框架

| 组件 | 技术 |
|------|------|
| 无前端框架 | 纯 JavaScript + Alpine.js 3.x |
| 无 TypeScript | 所有 JS 使用普通 JavaScript |
| 无构建工具 | CDN 引入 + 内联脚本 |
| 无 npm/package.json | 零依赖本地开发 |

### 模块模式

所有 JS 文件使用 **IIFE (立即执行函数表达式)**:

```javascript
(function(global) {
    'use strict';

    // 模块代码...

    global.AIDP = global.AIDP || {};
    global.AIDP.MyModule = MyClass;

})(window);
```

### 命名空间

所有公共 API 注册到 `window.AIDP`:

```
AIDP
├── config              # 全局配置
├── log                 # 日志工具
├── init()              # 初始化入口
├── API                 # APIClient 实例
├── store               # Store 实例
├── events              # EventBus 实例
├── Events              # 事件常量
├── toolService         # ToolService 实例
├── proxyService        # ProxyService 实例
├── registerComponents() # 组件注册函数
├── components
│   ├── ToolCard
│   ├── StatusBadge
│   ├── StatusDot
│   ├── DataTable
│   └── ...Templates
└── PageData
    ├── layoutData()
    ├── dashboardData()
    ├── toolsPageData()
    └── toolDetailData()
```

### 类命名

所有业务逻辑类使用 `PascalCase`:

| 类 | 文件 | 功能 |
|----|------|------|
| `APIClient` | `core/api.js` | HTTP 客户端 |
| `APIError` | `core/api.js` | API 错误类 |
| `Store` | `core/store.js` | 状态管理 |
| `EventBus` | `core/events.js` | 事件总线 |
| `ToolService` | `services/toolService.js` | 工具管理 |
| `ProxyService` | `services/proxyService.js` | 工具代理 |

### 数据获取模式

```javascript
// 通过 Service 层 (推荐)
const tools = await AIDP.toolService.getTools();

// 直接 API 调用
const data = await AIDP.API.get('/api/endpoint');
const result = await AIDP.API.post('/api/endpoint', { key: 'value' });
```

### 状态管理模式

```javascript
// 读取
const tools = AIDP.store.get('tools.list');

// 写入 (自动通知订阅者)
AIDP.store.set('tools.list', newTools);

// 订阅
const unsubscribe = AIDP.store.subscribe('tools.list', (newVal, oldVal) => {
    console.log('Changed:', newVal);
});
```

### Alpine.js 页面数据规范

```javascript
window.myPageData = function() {
    return {
        // Reactive state
        data: [],
        loading: false,

        // Lifecycle
        async init() {
            // 页面初始化
        },

        // Methods
        async loadData() {
            // fetch + state update
        }
    };
};
```

## HTML/Jinja2 模板规范

### 布局继承

页面通常不使用 `extends`，而是由 Controller 的 `render_template()` 渲染完整页面。布局通过路由映射到对应模板。

### 模板目录结构

```
templates/
├── layouts/         # 4 个布局 (base, unified_base, workspace, embed)
├── pages/           # 独立页面
├── modules/         # 功能模块 (按工具/领域)
│   ├── knowledge/
│   ├── memory/
│   ├── skills/
│   ├── rules/
│   ├── agents/
│   ├── assets/
│   ├── sandbox/
│   ├── quality/
│   └── workflows/
├── admin/           # 管理后台
├── auth/            # 认证
└── components/      # (保留，当前为空)
```

### 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 布局 | `{type}.html` | `base.html`, `workspace.html` |
| 页面 | `{name}.html` | `dashboard.html`, `tools.html` |
| 模块 | `{domain}/{page}.html` | `knowledge/bases.html` |
| Frame | `{name}-frame.html` | `users-frame.html` |
| Content | `{name}_content.html` | `dashboard_content.html` |
| 管理 | `admin/{name}.html` | `admin/users.html` |

### 页面内联脚本规范

模块页面将 Alpine 数据函数内联在模板底部:

```html
<script>
window.sandboxPage = function() {
    return {
        // Reactive data
        code: '',
        async execute() {
            var r = await fetch('/api/sandbox/execute', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({code: this.code, language: this.language})
            });
            if (r.ok) this.result = await r.json();
        }
    }
};
</script>
```

## CSS 样式规范

| 特性 | 规范 |
|------|------|
| CSS 框架 | Tailwind CSS 4 (CDN) |
| 主题 | 暗色主题 (bg-gray-900/800/700) |
| 强调色 | 靛蓝 (indigo-600/500/400) |
| 字体 | Inter (Google Fonts) |
| 响应式 | Tailwind 响应式断点 |
| 图标 | Font Awesome 6.4 (fas 风格) |

### 常用颜色映射

| 用途 | Tailwind class |
|------|---------------|
| 页面背景 | `bg-gray-900` |
| 卡片/面板 | `bg-gray-800` |
| 输入框 | `bg-gray-700 border-gray-600` |
| 主文字 | `text-white` |
| 次文字 | `text-gray-400` |
| 暗文字 | `text-gray-500` |
| 成功 | `text-green-400` |
| 错误 | `text-red-400` |
| 警告 | `text-yellow-400` |
| 链接/强调 | `text-indigo-400` |
| 边框 | `border-gray-700` |

## 项目配置规范

### 无统一 linter/formatter 配置

项目中**未找到**以下配置文件:
- ❌ `.editorconfig`
- ❌ `.flake8`
- ❌ `.pre-commit-config.yaml`
- ❌ `pyproject.toml`
- ❌ `setup.cfg`
- ❌ `eslint.config.*`
- ❌ `.prettierrc`

### 环境变量规范

所有服务使用 `.env` 文件管理配置:
- 配置文件位置: `tools/{name}/.env`
- 使用 `pydantic_settings.BaseSettings` 加载
- `model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}`
- 密钥从不硬编码，必须用环境变量

### 部署规范

- 所有服务支持 Docker 部署
- Dockerfile 位于各工具根目录
- `docker-compose.yml` 位于项目根目录
- NAS 部署通过 `deploy/deploy-nas.ps1` 脚本
- SSH 密钥: `~/.ssh/nas_temp`
- NAS IP: `192.168.0.100`