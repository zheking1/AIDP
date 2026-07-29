# AIDP Backend — API 设计文档

> 本文档详尽描述 AIDP Controller 后端 API 的整体架构、路由注册机制、完整路由清单、认证模式、权限体系、请求处理管道、错误处理、WebSocket 及 MCP 服务器设计。

---

## 1. API 架构总览

AIDP Controller 采用 **FastAPI async framework** 构建，运行于端口 **8883**，作为 AI DevOps Platform 的单一 API 网关。

### 核心架构特性

| 特性 | 说明 |
|---|---|
| 框架 | FastAPI async (Starlette 底层) |
| 端口 | 8883 |
| ORM | Async SQLAlchemy 2.0 (async_session_factory) |
| 认证 | Cookie Session（`aidp_session`）+ API Key 双模式 |
| 模板 | Jinja2 Server-Side Rendering |
| 文档 | Swagger `/docs` + Redoc `/redoc` |
| 指标 | Prometheus Client (`/metrics`) |
| WebSocket | `/ws/logs` 实时日志推送 |
| MCP | fastmcp with streamable-http transport at `/mcp` |

### 代码配置 (`apps/controller/app/_config.py`)

```python
class Settings(BaseSettings):
    APP_NAME: str = "aidp-controller"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8883
    DATABASE_URL: str = ""
```

---

## 2. 路由注册机制

所有路由在 `apps/controller/app/main.py` 中通过 `app.include_router()` 集中注册。注册顺序如下：

```python
# ===== 系统核心 API（无前缀或短前缀） =====
app.include_router(health_router)        # /health
app.include_router(auth_router)          # /api/auth/*
app.include_router(metrics_router)       # /metrics
app.include_router(audit_router)         # /api/audit/*
app.include_router(tools_router)         # /api/tools/*
app.include_router(models_router)        # /api/models/*
app.include_router(settings_router)      # /api/settings

# ===== 遗留业务 API =====
# app.include_router(projects_router)       # 已废弃（dead code，未注册）
app.include_router(configs_router)        # /api/projects/{id}/configs
app.include_router(reviews_router)        # /api/reviews
app.include_router(nas_storage_router)    # /api/projects/{id}/code-path
app.include_router(instructions_router)   # /api/instructions

# ===== Web 路由（HTML 页面 + 代理）=====
app.include_router(web_router)           # /, /login, /tools, /knowledge/*, etc.

# ===== 新架构路由 =====
app.include_router(projects_new_router)   # /api/projects (new, AIDP Unified)
```

路由导入方式（以 `main.py` 为例）：

```python
from app.api.health import router as health_router
from app.api.tools import router as tools_router
from app.api.auth import router as auth_router
from app.api.metrics import router as metrics_router
from app.api.audit import router as audit_router
from app.api.projects import router as projects_router
from app.api.configs import router as configs_router
from app.api.reviews import router as reviews_router
from app.api.nas_storage import router as nas_storage_router
from app.api.instructions import router as instructions_router
from app.api.models import router as models_router
from app.api.settings import router as settings_router
from app.web.routes import router as web_router
from app.routers.projects_new import router as projects_new_router
```

### 模块化路由注册

9 个业务模块通过 `BaseModule` 抽象类在 `app/modules/__init__.py` 中定义统一的注册接口。模块启动时自动调用 `register_routes(self, app)`：

```python
class BaseModule(ABC):
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    enabled: bool = True
    dependencies: List[str] = []

    @abstractmethod
    def register_routes(self, app: FastAPI):
        pass

    def on_startup(self):
        logger.info(f"Module {self.name} started")

    def on_shutdown(self):
        logger.info(f"Module {self.name} stopped")
```

模块通过 `@register_module` 装饰器注册，然后在 `app_lifespan` 中统一初始化：

```python
@register_module(name='knowledge', enabled=True)
class KnowledgeModule(BaseModule):
    def register_routes(self, app):
        from .routes import router as knowledge_router
        app.include_router(knowledge_router, prefix="/api/knowledge")
        from .templates_routes import router as templates_router
        app.include_router(templates_router, prefix="/api/knowledge")
```

---

## 3. 完整 API 路由清单

### 3.1 系统核心 API

| 方法 | 路径 | 说明 | 认证 |
|---|---|---|---|
| GET | `/health` | 健康检查 | 无 |
| GET | `/metrics` | Prometheus 指标 | 无 |
| GET | `/api/menu` | 动态菜单配置 | Cookie |
| GET | `/api/config/menu.yaml` | 原始菜单 YAML | Admin |
| POST | `/api/config/reload` | 热重载配置 | Admin |
| GET | `/api/modules` | 已注册模块信息 | Cookie |
| GET/POST | `/api/audit/` | 审计日志列表/写入 | Admin |
| GET | `/api/audit/logs` | 审计日志查询 | Admin |
| GET/PUT | `/api/settings` | 系统设置读写 | Admin |
| GET/POST/PUT/DELETE | `/api/models` | LLM 模型配置 CRUD | Admin |
| POST | `/api/instructions` | Agent 指令 CRUD | Cookie |

### 3.2 认证 API (`/api/auth`)

| 方法 | 路径 | 说明 | 认证 |
|---|---|---|---|
| POST | `/api/auth/login` | JSON 登录 | 无 |
| POST | `/api/auth/login/form` | Form 登录（Web UI） | 无 |
| POST | `/api/auth/logout` | JSON 登出 | Cookie |
| POST | `/api/auth/logout/form` | Form 登出 | Cookie |
| GET | `/api/auth/me` | 当前用户信息 | Cookie |
| POST | `/api/auth/change-password` | 修改密码 | Cookie |
| PUT | `/api/auth/profile` | 更新个人资料 | Cookie |
| GET | `/api/auth/users` | 用户列表 | Admin |
| POST | `/api/auth/users` | 创建用户 | Admin |
| PUT | `/api/auth/users/{id}` | 更新用户 | Admin |
| POST | `/api/auth/users/{id}/toggle` | 启用/禁用用户 | Admin |
| DELETE | `/api/auth/users/{id}` | 删除用户 | Super Admin |
| GET | `/api/auth/api-keys` | API 密钥列表 | Cookie |
| POST | `/api/auth/api-keys` | 创建 API 密钥 | Cookie |
| DELETE | `/api/auth/api-keys/{id}` | 吊销 API 密钥 | Cookie |

### 3.3 工具 API (`/api/tools`)

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/tools` | 工具列表 |
| POST | `/api/tools` | 注册工具 |
| GET | `/api/tools/{name}` | 工具详情 |
| GET | `/api/tools/health/all` | 全量健康检查 |
| POST | `/api/tools/{name}/health` | 单工具健康检查 |
| POST | `/api/tools/{name}/sync` | 同步工具能力 |
| POST | `/api/tools/{name}/disable` | 禁用工具 |
| POST | `/api/tools/{name}/enable` | 启用工具 |
| DELETE | `/api/tools/{name}` | 删除工具 |
| POST | `/api/tools/{name}/invoke` | 调用工具能力 |
| GET | `/api/tools/invocations/history` | 调用历史 |
| GET | `/api/tools/dashboard/stats` | 仪表盘统计 |

### 3.4 代理路由

| 方法 | 路径 | 说明 |
|---|---|---|
| GET\|POST\|PUT\|DELETE\|... | `/api/proxy/{tool}/{path}` | 工具 API 代理（JSON） |
| GET\|POST\|PUT\|DELETE\|... | `/tools/{tool}/web/{path}` | 工具 Web UI 代理（HTML 重写） |

工具 Web UI 代理会自动重写 HTML 中的相对路径和静态资源引用，通过 `rewrite_tool_html()` 函数实现统一界面嵌入。

### 3.5 项目管理 API

#### 遗留项目 API

| 方法 | 路径 | 说明 | 认证 |
|---|---|---|---|
| POST | `/api/projects/` | 创建项目 | Cookie |
| GET | `/api/projects/{id}/configs` | 项目配置 | Cookie |
| GET | `/api/projects/{id}/code-path` | 代码路径 | Cookie |

#### 新架构项目 API (`/api/projects`)

| 方法 | 路径 | 说明 | 认证 |
|---|---|---|---|
| GET | `/api/projects` | 项目列表（分页搜索） | Cookie |
| POST | `/api/projects` | 创建项目 | Cookie |
| GET | `/api/projects/{id}` | 项目详情 | Cookie |
| PUT | `/api/projects/{id}` | 更新项目 | Admin |
| DELETE | `/api/projects/{id}` | 软删除项目 | Owner |
| GET | `/api/projects/{id}/members` | 成员列表 | Cookie |
| POST | `/api/projects/{id}/members` | 添加成员 | Admin |
| DELETE | `/api/projects/{id}/members/{uid}` | 移除成员 | Admin |

### 3.6 9 大模块 API 路由

#### 知识库模块 (`/api/knowledge`)

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/api/knowledge/bases` | 知识库列表 | read |
| POST | `/api/knowledge/bases` | 创建知识库 | write |
| GET | `/api/knowledge/bases/{id}` | 知识库详情 | read |
| DELETE | `/api/knowledge/bases/{id}` | 删除知识库 | delete |
| GET | `/api/knowledge/bases/{id}/documents` | 文档列表 | read |
| POST | `/api/knowledge/bases/{id}/documents` | 创建文档 | write |
| GET | `/api/knowledge/documents/{id}` | 文档详情 | read |
| DELETE | `/api/knowledge/documents/{id}` | 删除文档 | delete |
| POST | `/api/knowledge/search` | 语义搜索 | read |
| GET | `/api/knowledge/stats` | 统计信息 | read |
| GET | `/api/knowledge/templates` | 文档模板列表 | read |
| POST | `/api/knowledge/templates` | 创建模板 | write |
| GET | `/api/knowledge/templates/{id}` | 模板详情 | read |
| PUT | `/api/knowledge/templates/{id}` | 更新模板 | write |
| DELETE | `/api/knowledge/templates/{id}` | 删除模板 | delete |

#### 记忆模块 (`/api/memory`)

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/api/memory/memories` | 记忆列表（支持分类/层级搜索） | read |
| POST | `/api/memory/memories` | 创建记忆 | write |
| GET | `/api/memory/memories/{id}` | 记忆详情（含访问计数） | read |
| PUT | `/api/memory/memories/{id}` | 更新记忆 | write |
| DELETE | `/api/memory/memories/{id}` | 删除记忆 | delete |
| GET | `/api/memory/memories/{id}/relations` | 记忆关联图谱（出入边） | read |
| POST | `/api/memory/memories/{id}/relations` | 创建关联 | write |
| DELETE | `/api/memory/relations/{id}` | 删除关联 | write |
| POST | `/api/memory/search` | 语义检索 | read |
| GET | `/api/memory/graph` | 全量记忆图谱 | read |
| GET | `/api/memory/stats` | 统计（按分类/层级） | read |

#### 技能模块 (`/api/skills`)

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/api/skills/list` | 技能列表（三层作用域） | read |
| POST | `/api/skills/create` | 创建技能 | write |
| POST | `/api/skills/search` | 技能搜索 | read |
| GET | `/api/skills/stats` | 统计 | read |
| GET | `/api/skills/groups/list` | 技能分组列表 | read |
| POST | `/api/skills/groups/create` | 创建分组 | write |
| DELETE | `/api/skills/groups/{id}` | 删除分组 | write |
| GET | `/api/skills/{id}` | 技能详情 | read |
| PUT | `/api/skills/{id}` | 更新技能 | write |
| DELETE | `/api/skills/{id}` | 删除技能 | delete |
| GET | `/api/skills/{id}/files` | 技能文件列表 | read |
| POST | `/api/skills/{id}/files` | 保存技能文件 | write |
| POST | `/api/skills/{id}/move` | 移动技能（分组/作用域） | write |

#### 规则模块 (`/api/rules`)

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/api/rules/list` | 规则列表（三层作用域） | read |
| POST | `/api/rules/create` | 创建规则 | write |
| POST | `/api/rules/search` | 规则搜索 | read |
| GET | `/api/rules/stats` | 统计 | read |
| GET | `/api/rules/groups/list` | 规则分组列表 | read |
| POST | `/api/rules/groups/create` | 创建分组 | write |
| DELETE | `/api/rules/groups/{id}` | 删除分组 | write |
| GET | `/api/rules/{id}` | 规则详情 | read |
| PUT | `/api/rules/{id}` | 更新规则 | write |
| DELETE | `/api/rules/{id}` | 删除规则 | delete |

#### 代码资产模块 (`/api/assets`)

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/api/assets/list` | 资产列表 | read |
| POST | `/api/assets/create` | 创建资产 | write |
| POST | `/api/assets/search` | 资产搜索 | read |
| GET | `/api/assets/stats` | 统计 | read |
| GET | `/api/assets/{id}` | 资产详情 | read |
| PUT | `/api/assets/{id}` | 更新资产 | write |
| DELETE | `/api/assets/{id}` | 删除资产 | delete |
| POST | `/api/assets/{id}/render` | 模板渲染 | read |

#### 代码沙箱模块 (`/api/sandbox`)

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| POST | `/api/sandbox/execute` | 执行代码（Python/Bash/Sh） | execute |
| GET | `/api/sandbox/history` | 执行历史 | read |
| GET | `/api/sandbox/stats` | 统计 | read |

#### 质量检查模块 (`/api/quality`)

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| POST | `/api/quality/check` | 运行检查（lint/security/all） | check |
| GET | `/api/quality/history` | 检查历史 | read |
| GET | `/api/quality/stats` | 统计（平均分） | read |

#### Agent 管理模块 (`/api/agents`)

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/api/agents/list` | Agent 列表 | read |
| POST | `/api/agents/create` | 创建 Agent（含技能/规则/知识关联） | write |
| GET | `/api/agents/templates/list` | Agent 模板列表 | read |
| POST | `/api/agents/from-template/{id}` | 从模板创建 Agent | write |
| GET | `/api/agents/stats` | 统计 | read |
| GET | `/api/agents/{id}` | Agent 详情（含关联资源） | read |
| PUT | `/api/agents/{id}` | 更新 Agent | write |
| DELETE | `/api/agents/{id}` | 删除 Agent | delete |
| GET | `/api/agents/{id}/context` | Agent 完整上下文（含继承链） | read |
| POST | `/api/agents/{id}/link-skill` | 关联技能 | write |
| POST | `/api/agents/{id}/unlink-skill` | 取消关联技能 | write |
| POST | `/api/agents/{id}/link-rule` | 关联规则 | write |
| POST | `/api/agents/{id}/unlink-rule` | 取消关联规则 | write |
| POST | `/api/agents/{id}/link-knowledge` | 关联知识库 | write |
| POST | `/api/agents/{id}/unlink-knowledge` | 取消关联知识库 | write |

#### 工作流模块 (`/api/workflows`)

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/api/workflows/list` | 工作流列表 | read |
| POST | `/api/workflows/create` | 创建工作流（含步骤） | write |
| GET | `/api/workflows/templates/list` | 模板列表 | read |
| GET | `/api/workflows/stats` | 统计 | read |
| GET | `/api/workflows/executions/list` | 执行记录列表 | read |
| GET | `/api/workflows/executions/{id}` | 执行详情 | read |
| POST | `/api/workflows/executions/{id}/cancel` | 取消执行 | write |
| GET | `/api/workflows/{id}` | 工作流详情（含步骤） | read |
| PUT | `/api/workflows/{id}` | 更新工作流 | write |
| DELETE | `/api/workflows/{id}` | 删除工作流 | delete |
| POST | `/api/workflows/{id}/steps` | 添加步骤 | write |
| PUT | `/api/workflows/{id}/steps/{step}` | 更新步骤 | write |
| DELETE | `/api/workflows/{id}/steps/{step}` | 删除步骤 | write |
| POST | `/api/workflows/{id}/execute` | 执行工作流 | write |

### 3.7 Web 路由（HTML 页面）

| 方法 | 路径 | 模板 | 认证 |
|---|---|---|---|
| GET | `/` | `layouts/workspace.html` | Cookie |
| GET | `/login` | `auth/login.html` | 无 |
| GET | `/logout` | — | Cookie |
| GET | `/dashboard-frame` | `pages/dashboard-frame.html` | 可选 |
| GET | `/profile` | `auth/profile.html` | Cookie |
| GET | `/api-keys` | `auth/api_keys.html` | Cookie |
| GET | `/tools` | `pages/tools.html` | Cookie |
| GET | `/tools/{name}` | `pages/tool_detail.html` | Cookie |
| GET | `/tools-frame` | `pages/tools-frame.html` | Cookie |
| GET | `/projects` | `pages/projects_new.html` | Cookie |
| GET | `/logs` | `logs.html` | Cookie |
| GET | `/configs` | `configs.html` | Cookie |
| GET | `/onboarding` | `onboarding.html` | 无 |

#### 模块页面

| 方法 | 路径 | 模板 |
|---|---|---|
| GET | `/knowledge/bases` | `modules/knowledge/bases.html` |
| GET | `/knowledge/documents` | `modules/knowledge/documents.html` |
| GET | `/knowledge/search` | `modules/knowledge/search.html` |
| GET | `/knowledge/templates` | `modules/knowledge/templates.html` |
| GET | `/memory/memories` | `modules/memory/memories.html` |
| GET | `/memory/graph` | `modules/memory/graph.html` |
| GET | `/memory/search` | `modules/memory/memories.html` |
| GET | `/skills/global` | `modules/skills/global.html` |
| GET | `/skills/personal` | `modules/skills/personal.html` |
| GET | `/skills/project/{id}` | `modules/skills/personal.html` |
| GET | `/assets` | `modules/assets/list.html` |
| GET | `/assets/search` | `modules/assets/list.html` |
| GET | `/sandbox` | `modules/sandbox/index.html` |
| GET | `/quality` | `modules/quality/index.html` |
| GET | `/rules/global` | `modules/rules/global.html` |
| GET | `/rules/personal` | `modules/rules/personal.html` |
| GET | `/rules/project/{id}` | `modules/rules/personal.html` |
| GET | `/agents` | `modules/agents/list.html` |
| GET | `/workflows` | `modules/workflows/list.html` |

#### 项目详情页面

| 方法 | 路径 | 模板 |
|---|---|---|
| GET | `/project/{id}/dashboard` | `pages/project_dashboard.html` |
| GET | `/project/{id}/settings/general` | `pages/project_settings/general.html` |
| GET | `/project/{id}/settings/instructions` | `pages/project_settings/instructions.html` |
| GET | `/project/{id}/settings/knowledge/general` | `pages/project_settings/knowledge.html` |
| GET | `/project/{id}/settings/members` | `pages/project_settings/members.html` |
| GET | `/project/{id}/settings/integrations/git` | `pages/project_settings/integrations.html` |

#### 管理员页面

| 方法 | 路径 | 模板 | 权限 |
|---|---|---|---|
| GET | `/admin` | 重定向到 `/admin/users` | Admin |
| GET | `/admin/users` | `admin/users.html` | Admin |
| GET | `/admin/users/create` | `admin/user_form.html` | Admin |
| GET | `/admin/roles` | `admin/roles.html` | Admin |
| GET | `/admin/models` | `admin/models.html` | Admin |
| GET | `/admin/settings` | `admin/settings.html` | Admin |
| GET | `/admin/projects` | `admin/projects.html` | Admin |
| GET | `/admin/skills` | `admin/skills.html` | Admin |
| GET | `/admin/audit-logs` | `admin/audit_logs.html` | Admin |
| GET | `/admin/rules` | `modules/rules/global.html` | Admin |

#### Hub 页面

| 方法 | 路径 | 模板 |
|---|---|---|
| GET | `/hub/knowledge` | `pages/knowledge_hub.html` |
| GET | `/hub/skills` | `pages/skills_hub.html` |
| GET | `/hub/memory` | `pages/memory_hub.html` |

#### Frame 页面（iframe 嵌入）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/admin/users-frame` | 用户管理 frame |
| GET | `/admin/roles-frame` | 角色管理 frame |
| GET | `/admin/models-frame` | 模型管理 frame |
| GET | `/admin/settings-frame` | 设置 frame |
| GET | `/profile-frame` | 个人资料 frame |
| GET | `/api-keys-frame` | API 密钥 frame |
| GET | `/knowledge-frame` | 知识库 iframe（代理到知识服务） |
| GET | `/knowledge-frame/bindings` | 项目绑定 frame |
| GET | `/knowledge-frame/search` | 搜索 frame |

---

## 4. 认证模式详解

AIDP Controller 采用 **Cookie-based Session** 为主要认证方式，辅以 **API Key** 认证用于机器调用。

### 4.1 Session 认证流程

```python
# 登录：验证凭据 -> 创建 Session -> 设置 Cookie
@router.post("/api/auth/login")
async def api_login(request: Request, response: Response, data: LoginRequest):
    user = await AuthService.authenticate_user(
        username=data.username, password=data.password,
        ip_address=request.client.host, user_agent=request.headers.get("user-agent")
    )
    session = await AuthService.create_session(
        user_id=user.id, remember_me=data.remember_me
    )
    max_age = 60 * 60 * 24 * 7 if data.remember_me else 60 * 60 * 24  # 7天或1天
    response.set_cookie(
        key="aidp_session", value=session.session_token,
        httponly=True, secure=False, samesite="lax", max_age=max_age
    )
    return LoginResponse(success=True, user=user_info)
```

### 4.2 Session 验证

```python
# 每个受保护路由：从 Cookie 提取 token -> 验证 -> 返回 User
async def get_current_user(request: Request) -> Optional[User]:
    session_token = request.cookies.get("aidp_session")
    if not session_token:
        return None
    return await AuthService.validate_session(session_token)
```

`AuthService.validate_session()` 在 `auth_service.py` 中的实现：

```python
@classmethod
async def validate_session(cls, session_token: str) -> Optional[User]:
    if not session_token:
        return None
    async with async_session_factory() as session:
        result = await session.execute(
            select(UserSession).where(
                and_(
                    UserSession.session_token == session_token,
                    UserSession.expires_at > datetime.utcnow()
                )
            )
        )
        user_session = result.scalar_one_or_none()
        if user_session:
            user_session.last_activity_at = datetime.utcnow()
            await session.commit()
            result = await session.execute(
                select(User).where(User.id == user_session.user_id)
            )
            user = result.scalar_one_or_none()
            if user and user.status == UserStatus.ACTIVE:
                return user
        return None
```

### 4.3 密码验证

支持 bcrypt 和 pbkdf2_sha256 两种哈希格式：

```python
@staticmethod
def verify_password(password: str, password_hash: str) -> bool:
    if password_hash.startswith('$2'):
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    elif password_hash.startswith('pbkdf2_sha256$'):
        # 兼容 Django 格式
        ...
```

### 4.4 API Key 认证

```python
@classmethod
async def validate_api_key(cls, key: str) -> Optional[User]:
    if not key or not key.startswith("aidp_"):
        return None
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    async with async_session_factory() as session:
        result = await session.execute(
            select(ApiKey).where(
                and_(ApiKey.key_hash == key_hash, ApiKey.is_active == True,
                     or_(ApiKey.expires_at.is_(None), ApiKey.expires_at > datetime.utcnow()))
            )
        )
        api_key = result.scalar_one_or_none()
        if api_key:
            api_key.last_used_at = datetime.utcnow()
            await session.commit()
            ...
```

### 4.5 角色体系

角色层级定义在 `PermissionService` 中：

```python
ROLE_HIERARCHY = {
    UserRole.SUPER_ADMIN: 5,
    UserRole.ADMIN: 4,
    UserRole.DEVELOPER: 3,
    UserRole.USER: 2,
    UserRole.READONLY: 1,
}
```

---

## 5. 权限检查

### 5.1 `require_permissions` 依赖

```python
from app.core.permissions import require_permissions

@router.get("/api/projects")
async def list_projects(user=require_permissions("project:view")):
    return {"projects": []}
```

### 5.2 `PermissionChecker` 实现

```python
class PermissionChecker:
    async def __call__(self, request: Request) -> Any:
        user = await self._get_current_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        for permission in self.permissions:
            if not await self._check_permission(user, permission, request):
                raise HTTPException(status_code=403, detail=f"Permission denied: {permission}")
        return user

    async def _check_permission(self, user, permission, request) -> bool:
        # 管理员拥有所有权限
        if user.role in ['admin', 'super_admin']:
            return True
        # 按 resource:action[:scope] 解析
        ...
```

### 5.3 模块内权限检查

模块路由同时使用 `require_permissions` 和 `get_current_user`，根据端点需求灵活组合：

```python
# 只读端点：仅需认证
@router.get("/bases")
async def list_bases(user=Depends(get_current_user)):
    ...

# 写操作：需要特定权限
@router.post("/bases")
async def create_base(user=require_permissions("knowledge:write")):
    ...
```

### 5.4 Web 页面权限检查

Web 页面在 `web/routes.py` 中做手动权限检查：

```python
@router.get("/admin/users")
async def admin_users_page(request: Request):
    user = await get_current_user_from_request(request)
    if not user or not PermissionService.is_admin(user):
        return RedirectResponse(url="/login", status_code=302)
    return render_template(request, "admin/users.html", ...)
```

---

## 6. 请求处理管道

完整的 HTTP 请求生命周期如下：

```
HTTP Request
    │
    ▼
[SessionMiddleware]    — 解密/解析 session cookie
    │
    ▼
[CORSMiddleware]       — 跨域头处理（allow_origins=["*"]）
    │
    ▼
[Route Matching]       — FastAPI 路由匹配
    │
    ├── 无认证端点（/health, /metrics, /login）
    │
    ├── API 端点
    │   ├── [Auth validation]  — 从 Cookie 提取 session_token
    │   │                       → AuthService.validate_session()
    │   ├── [Permission Check] — require_permissions() 或手动检查
    │   └── [Handler]          — 业务逻辑 → Response
    │
    ├── Web 页面端点
    │   ├── [get_current_user_from_request]
    │   ├── [Redirect if not authenticated] → /login
    │   └── [render_template]  — Jinja2 SSR → HTMLResponse
    │
    └── WebSocket (/ws/logs)
        └── [ws_handler]      — 实时广播
```

### SessionMiddleware 配置

```python
app.add_middleware(SessionMiddleware, secret_key=os.environ.get("CONTROLLER_SESSION_KEY", "change-me"))
```

### CORSMiddleware 配置

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 7. 错误处理

### 标准 HTTP 错误响应

| 状态码 | 说明 | 典型场景 |
|---|---|---|
| 401 | Unauthorized | Session 无效/过期、未登录 |
| 403 | Forbidden | 角色权限不足 |
| 404 | Not Found | 资源不存在（项目/知识库/技能等） |
| 400 | Bad Request | 参数校验失败、重复用户名 |
| 500 | Internal Error | 服务端异常 |
| 502 | Bad Gateway | 工具代理连接失败 |

### 典型错误处理模式

```python
# 401 - 未认证
if not user:
    raise HTTPException(status_code=401, detail="Authentication required")

# 403 - 权限不足
if not PermissionService.is_admin(user):
    raise HTTPException(status_code=403, detail="Admin access required")

# 404 - 资源不存在
if not project:
    raise HTTPException(status_code=404, detail="Project not found")

# 400 - 参数错误
if data.scope == "project" and not project_id:
    raise HTTPException(status_code=400, detail="Project skill requires project_id")
```

### Web 页面错误处理

Web 页面在认证失败时返回 **重定向** 而非 JSON 错误：

```python
if not user:
    return RedirectResponse(url="/login?next=/knowledge/bases", status_code=302)
```

---

## 8. WebSocket

### 8.1 `/ws/logs` — 实时日志推送

用于实时推送工具调用状态到前端：

```python
from fastapi import WebSocket, WebSocketDisconnect

connected_clients: list[WebSocket] = []

async def ws_handler(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
```

广播消息格式：

```python
async def broadcast_invocation(tool_name, status, duration_ms, error=None):
    payload = json.dumps({
        "tool_name": tool_name,
        "status": status,
        "duration_ms": duration_ms,
        "error": error,
        "timestamp": datetime.utcnow().isoformat(),
    })
    for ws in connected_clients:
        try:
            await ws.send_text(payload)
        except Exception:
            disconnected.append(ws)
```

注册方式：

```python
app.add_api_websocket_route("/ws/logs", ws_handler)
```

### 8.2 WebSocket 认证

当前 WebSocket 实现未做显式认证（接受所有连接后通过消息协议鉴权）。生产环境中建议在 `websocket.accept()` 前验证 `request.cookies`。

---

## 9. MCP 服务器

### 9.1 挂载方式

MCP 服务器挂载在 `/mcp` 路径下，使用 fastmcp 的 streamable-http 传输协议：

```python
from fastmcp import FastMCP

mcp = FastMCP("aidp-controller", instructions="""AIDP (AI DevOps Platform) 工作流指引...""")

_mcp_app = mcp.http_app(path="/", transport="streamable-http")

# 在 main.py 中挂载
app.mount("/mcp", _mcp_app)
```

### 9.2 生命周期合并

MCP 的 lifespan 与主应用的 lifespan 合并：

```python
@asynccontextmanager
async def combined_lifespan(app: FastAPI):
    async with app_lifespan(app):
        async with _mcp_app.lifespan(app):
            yield

app = FastAPI(lifespan=combined_lifespan)
```

### 9.3 核心 MCP 工具

| 工具函数 | 说明 |
|---|---|
| `aidp_context(project_name, task)` | 5 阶段上下文引擎（必须第一步调用） |
| `invoke_tool_mcp(tool_name, capability, arguments)` | 通用工具调用器 |
| `list_registered_tools(status)` | 列出所有已注册工具 |
| `check_tool_health(tool_name)` | 检查工具健康状态 |
| `sync_tool_capabilities(tool_name)` | 同步工具能力定义 |
| `aidp_init(project_name, ...)` | 初始化新项目到 AIDP |
| `aidp_instructions(project_name, task, agent_type)` | 生成 subagent 专用指令 |

### 9.4 强制工作流顺序

MCP 服务器通过 `session_manager` 强制要求先调用 `aidp_context` 再调用 `invoke_tool_mcp`：

```python
session_id = ctx.session_id or "default"
allowed, reason = session_manager.can_call_tool(session_id, tool_name)
if not allowed:
    return json.dumps({
        "success": False,
        "error": {
            "code": "CONTEXT_REQUIRED",
            "message": reason,
            "hint": "请先调用 aidp_context(project_name='aidp', task='你的任务描述')",
        }
    }, indent=2)
```

---

## 10. 静态文件服务

```python
static_dir = Path(__file__).parent / "web" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
```

所有 `/static/*` 请求由 StaticFiles 直接处理，不经过路由匹配。

---

## 11. 应用生命周期

```python
@asynccontextmanager
async def app_lifespan(app: FastAPI):
    # 启动阶段
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)  # 自动建表
    await init_database()                              # 初始化默认数据
    initialized_modules = init_all_modules(app)        # 初始化 9 大业务模块
    await seed_templates()                              # 初始化种子数据
    yield
    # 关闭阶段
    shutdown_all_modules()                              # 关闭所有模块
```

模块初始化顺序依赖解析（`init_all_modules` 自动处理依赖拓扑排序），例如 Workflows 模块依赖 Agents 模块。

---

## 12. 总结

AIDP Controller 后端 API 设计遵循以下原则：

1. **统一网关** — 所有请求经过单一入口，统一认证和权限检查
2. **模块化可扩展** — 通过 `BaseModule` 抽象类和 `@register_module` 装饰器，新增模块只需实现 `register_routes()` 和定义路由文件
3. **双模式认证** — Cookie Session 用于 Web 界面，API Key 用于机器/工具调用
4. **权限分层** — 角色层级（super_admin > admin > developer > user > readonly）+ 资源级别权限（knowledge:write, project:view 等）
5. **异步全栈** — FastAPI async + Async SQLAlchemy + async httpx 代理，端到端非阻塞
6. **统一模板渲染** — Jinja2 SSR 通过 `render_template()` 工具函数统一处理，支持 partial/embed 模式
7. **MCP 集成** — fastmcp 提供 AI Agent 可直接调用的 MCP 工具接口

共计 **12 个 API Router + 1 个 Web Router + 9 个模块子 Router**，涵盖系统管理、用户认证、工具管理、项目管理、知识库、记忆、技能、规则、资产、沙箱、质量检查、Agent、工作流等完整功能域。端口 8883 作为唯一对外暴露的网关端口，所有内部工具服务通过 `api/proxy` 和 `tools/{name}/web` 代理透明访问。