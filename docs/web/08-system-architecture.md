# AIDP Controller — 系统架构与实现原理

## 1. 系统总览

AIDP Controller 是一个基于 FastAPI 的模块化单体应用，集成了知识管理、记忆系统、技能库、规则引擎、Agent 编排、工作流引擎、代码沙箱、质量检查等模块，通过统一的工作台界面（Alpine.js 标签页）提供 Web UI。

### 1.1 技术栈

| 层 | 技术 | 版本 |
|---|---|---|
| 框架 | FastAPI | 0.115+ |
| ORM | SQLAlchemy (async) | 2.0+ |
| 数据库 | PostgreSQL (asyncpg) / SQLite (aiosqlite) | — |
| 前端 | Alpine.js 3.x + Tailwind CSS v4 + Font Awesome 6 | CDN |
| 模板 | Jinja2 | — |
| 认证 | Cookie-based session (`aidp_session`) | — |
| 部署 | Docker, `network_mode: host` | — |

### 1.2 目录结构

```
apps/controller/
├── app/
│   ├── main.py                 # 应用入口：路由注册、中间件、生命周期
│   ├── _config.py              # Settings 配置（Pydantic BaseSettings）
│   ├── api/                    # API 路由（13 个路由文件）
│   ├── web/
│   │   ├── routes.py           # 75+ 前端路由（Jinja2 渲染）
│   │   └── templates/          # Jinja2 模板
│   ├── modules/                # 模块系统（9 个模块）
│   │   ├── __init__.py         # BaseModule + 注册/初始化系统
│   │   ├── knowledge/          # 知识库模块
│   │   ├── memory/             # 记忆模块
│   │   ├── skills/             # 技能模块
│   │   ├── assets/             # 资产模块
│   │   ├── rules/              # 规则模块
│   │   ├── agents/             # Agent 模块
│   │   ├── workflows/          # 工作流模块
│   │   ├── sandbox/            # 沙箱模块
│   │   └── quality/            # 质量检查模块
│   ├── core/                   # 核心工具
│   │   ├── config_loader.py    # YAML 配置加载器
│   │   ├── menu.py             # 动态菜单引擎
│   │   ├── permissions.py      # 权限检查
│   │   ├── context.py          # 项目上下文
│   │   └── utils.py            # ID 生成、时间工具
│   ├── db/                     # 数据库
│   │   ├── database.py         # 异步引擎 + Session
│   │   ├── auth_models.py      # 用户/角色/权限/AuditLog 模型
│   │   ├── models.py           # ToolRegistry 模型
│   │   └── init_db.py          # 数据库初始化 + Seed 数据
│   ├── services/               # 服务层
│   │   ├── auth_service.py     # 认证服务
│   │   ├── context_pipeline.py # 5 阶段上下文流水线
│   │   ├── seed_data.py        # 种子数据（模板）
│   │   └── ...                 # 其他服务
│   ├── routers/                # 额外路由
│   │   └── projects_new.py     # 新版项目 CRUD
│   ├── models/                 # 旧版模型
│   │   ├── project.py
│   │   ├── project_new.py
│   │   ├── instructions.py
│   │   └── review.py
│   ├── mcp/                    # MCP 服务器
│   │   ├── server.py
│   │   └── session_manager.py
│   ├── schemas/                # Pydantic 数据模式
│   ├── security/               # 安全模块
│   └── config/
│       └── menu.yaml           # 菜单配置（v3.0）
└── tests/                      # 测试
    ├── run_all.py              # API CRUD 测试（47 个）
    └── scripts/
        ├── test-full-log.js    # 全页面零错误测试
        ├── test-menu-click.js  # 菜单功能测试
        └── test-layout.js      # 布局一致性测试
```

---

## 2. 应用启动流程

```
app/main.py
│
├── 导入所有模型（确保 SQLAlchemy 注册）
│   ├── app.db.auth_models      → User, UserSession, AuditLog 等
│   ├── app.models.project_new  → Project, ProjectMember 等
│   └── app.modules.{knowledge,memory,...}.models  → 9 个模块的模型
│
├── 导入所有路由
│   ├── app.api.*               → 13 个 API 路由器
│   ├── app.web.routes          → Web 路由器（75+ 前端路由）
│   └── app.routers.projects_new → 新版项目路由器
│
├── app_lifespan (启动时执行)
│   ├── Base.metadata.create_all → 建表
│   ├── init_database()          → 写入默认权限/管理员/设置
│   ├── init_all_modules()       → 初始化所有模块（注册路由/模型/事件）
│   └── seed_templates()         → 写入种子模板（5 Agent + 2 工作流 + 3 文档）
│
├── 中间件
│   ├── SessionMiddleware        → cookie 会话
│   └── CORSMiddleware           → 跨域
│
├── 路由器注册（12 个 API + 1 个 Web）
│
├── WebSocket /ws/logs           → 实时日志流
│
├── /static                      → 静态文件
│
└── /mcp                         → fastmcp 服务器 (streamable-http)
```

---

## 3. 模块系统

### 3.1 BaseModule 接口

```python
class BaseModule(ABC):
    name: str                     # 模块名
    api_prefix: str               # API 路由前缀，如 /api/knowledge
    dependencies: List[str]       # 依赖模块列表
    enabled: bool = True

    def register_routes(self, app):     # 注册 API 路由
    def register_models(self):          # 注册模型
    def register_events(self):          # 注册事件
    async def on_startup(self, app):    # 启动回调
    async def on_shutdown(self):        # 关闭回调
```

### 3.2 模块注册

```python
@register_module(name='workflows', dependencies=['agents'])
class WorkflowsModule(BaseModule):
    ...
```

`init_all_modules()` 按照拓扑排序解析依赖，确保 `agents` 在工作流之前初始化。

### 3.3 已注册模块

| 模块 | API 前缀 | 依赖 | 模型数 | 路由数 |
|---|---|---|---|---|
| knowledge | /api/knowledge | — | 4 | 2 (routes + templates_routes) |
| memory | /api/memory | — | 3 | 1 |
| skills | /api/skills | — | 4 | 1 |
| assets | /api/assets | — | 2 | 1 |
| rules | /api/rules | — | 2 | 1 |
| agents | /api/agents | — | 1 | 1 |
| workflows | /api/workflows | agents | 4 | 1 |
| sandbox | /api/sandbox | — | 1 | 1 |
| quality | /api/quality | — | 1 | 1 |

### 3.4 数据隔离

采用三层作用域（Scope）隔离数据：

```
Global（全局） → 管理员维护，所有用户可见
Personal（个人） → 用户私有
Project（项目） → 项目内成员可见
```

适用模块：Skills、Rules、Agents（通过 `scope` 字段区分）

---

## 4. 前端架构

### 4.1 页面加载流程

```
浏览器请求 /login → 登录 → 重定向到 /
  │
  └── workspace.html（Alpine.js 应用）
      │
      ├── init() → loadMenu() → loadProjects()
      │
      ├── 用户点击侧边栏按钮
      │   └── openHub() / openMenuTab() → openTab(id, name, icon, url)
      │       │
      │       ├── 构建 partial URL: url + "?partial=1"
      │       ├── fetch(partialUrl)
      │       ├── 提取 <script> 标签
      │       ├── 替换 x-data="func()" → data-alpine-component="func"
      │       ├── 创建临时 div → 设置 innerHTML
      │       ├── 执行 script 标签（定义组件函数）
      │       ├── 恢复 x-data="func()"
      │       └── replaceChildren() 批量插入 → Alpine.initTree()
      │
      └── 切换标签
          └── switchTab(id) → 仅修改 activeTab（x-show 控制显隐）
```

### 4.2 模板渲染机制

```python
def render_template(request, template_name, context):
    # partial 模式：自动切换到 _content 模板
    if context["partial"]:
        content_tpl = template_name.rsplit(".", 1)[0] + "_content.html"
        找到则返回内容片段，找不到则回退原模板
    return 完整页面渲染
```

### 4.3 布局系统

```
workspace.html
  ├── sidebar（256px） ← 动态菜单（menu.yaml）
  │   ├── Hub 按钮（知识中心/技能库/记忆中心）
  │   ├── 普通菜单项（代码沙箱/质量检查）
  │   ├── 项目区域（选择项目后显示）
  │   └── 管理区域（admin 角色可见）
  │
  └── main（flex-1）
      ├── tab bar（标签页标题栏）
      └── tab content（内容区域）
          └── mx-auto max-w-7xl min-w-[480px] px-6
              ├── [CSS 自动样式]
              │   ├── header: div:first-of-type → pt-5 pb-4 border-b
              │   └── body: div:not(:first-of-type) → pt-5
              └── [页面具体内容]
```

### 4.4 页面统一布局

每个 `_content.html` 模板遵循：

```html
<div x-data="xxxPage()" x-init="init()">    <!-- 外层 Alpine 组件 -->
    <div class="flex items-center justify-between">   <!-- 页头 -->
        <div>                                          <!-- 标题区 -->
            <h1>页面标题</h1>
            <p>页面描述</p>
        </div>
        <div class="flex gap-2">                       <!-- 操作区 -->
            <button>创建</button>
        </div>
    </div>
    <div> ... </div>                                    <!-- 正文区 -->
</div>
```

所有布局类（间距、边框、居中）由 `workspace.html` 的 CSS 自动注入，各模板只保留功能类。

---

## 5. API 路由总览

### 5.1 认证 API（`/api/auth`）

| 方法 | 路径 | 功能 |
|---|---|---|
| POST | /api/auth/login | 登录 |
| POST | /api/auth/logout | 登出 |
| GET | /api/auth/me | 当前用户信息 |
| GET | /api/auth/users | 用户列表 |
| POST | /api/auth/users | 创建用户 |
| PUT | /api/auth/users/{id} | 更新用户 |
| DELETE | /api/auth/users/{id} | 删除用户 |
| GET/POST/PUT/DELETE | /api/auth/api-keys | API 密钥管理 |

### 5.2 模块 API（9 个模块）

| 前缀 | 主要端点 |
|---|---|
| /api/knowledge | `/bases` CRUD, `/documents` CRUD, `/search`, `/stats`, `/templates` CRUD |
| /api/memory | `/entries` CRUD, `/graph`, `/search`, `/stats`, `/import` |
| /api/skills | `/list`, CRUD, `/groups` CRUD, `/files`, `/evolutions`, `/import`/`/export` |
| /api/assets | `/list`, CRUD, `/tags`, `/search`, `/render` |
| /api/rules | `/list`, CRUD, `/groups` CRUD, `/search`, `/stats`, `/check` |
| /api/agents | `/list`, CRUD, `/{id}/context`（上下文汇编器）, `/templates` |
| /api/workflows | `/list`, CRUD, `/{id}/execute`/`cancel`, `/templates`, `/{id}/executions` |
| /api/sandbox | `/execute`, `/list` |
| /api/quality | `/check/lint`, `/check/security`, `/check/score`, `/list` |

### 5.3 工具与代理

| 方法 | 路径 | 功能 |
|---|---|---|
| GET | /api/tools | 工具列表 |
| POST | /api/tools/register | 注册工具 |
| POST | /api/proxy/{tool}/{path} | 代理调用工具 |
| GET/POST | /tools/{tool}/web/{path} | 工具 Web UI 代理（HTML 重写） |

### 5.4 认证方式

API 路由统一使用 `AuthService.validate_session(session_token)` 认证：
```python
session_token = request.cookies.get("aidp_session")
user = await AuthService.validate_session(session_token)
```

---

## 6. 数据模型

### 6.1 数据库表

所有模块表使用 `aidp_` 前缀（由模块注册时自动设置 `__tablename__`）。

| 表名 | 所属模块 | 说明 |
|---|---|---|
| users | auth | 用户 |
| user_sessions | auth | 会话 |
| audit_logs | auth | 审计日志 |
| system_settings | auth | 系统设置 |
| projects | project_new | 项目 |
| project_members | project_new | 项目成员 |
| aidp_knowledge_bases | knowledge | 知识库 |
| aidp_knowledge_documents | knowledge | 文档 |
| aidp_document_chunks | knowledge | 文档分块 |
| aidp_memory_entries | memory | 记忆条目 |
| aidp_memory_relations | memory | 记忆关系 |
| aidp_skills | skills | 技能 |
| aidp_skill_groups | skills | 技能分组 |
| aidp_assets | assets | 代码资产 |
| aidp_rules | rules | 规则 |
| aidp_rule_groups | rules | 规则分组 |
| aidp_agents | agents | Agent |
| aidp_workflows | workflows | 工作流 |
| aidp_workflow_steps | workflows | 工作流步骤 |
| aidp_workflow_executions | workflows | 工作流执行记录 |

### 6.2 核心模型关系

```
Agent
  ├── instructions (Text)           → 角色定义
  ├── skills (many-to-many via agent_skills)  → 关联技能
  ├── rules (many-to-many via agent_rules)    → 关联规则
  └── knowledge (many-to-many via agent_knowledge) → 关联知识

Workflow
  ├── steps (one-to-many WorkflowStep)  → 多步骤定义
  └── executions (one-to-many WorkflowExecution)
      └── step_results (one-to-many WorkflowExecutionStep)

Project
  ├── members (one-to-many ProjectMember)
  └── settings (one-to-one ProjectSettings)
```

---

## 7. 路由与认证流程

### 7.1 Web 路由认证

```python
async def get_current_user_from_request(request: Request):
    session_token = request.cookies.get("aidp_session")
    return await AuthService.validate_session(session_token)
```

所有 Web 路由调用此函数获取当前用户，未认证时重定向到 `/login`。

### 7.2 API 路由认证

```python
# api/audit.py（示例）
session_token = request.cookies.get("aidp_session")
if not session_token:
    raise HTTPException(status_code=401)
user = await AuthService.validate_session(session_token)
```

---

## 8. 部署配置

### 8.1 Docker

```yaml
services:
  aidp-controller:
    image: aidp/controller:0.1.0
    network_mode: host  # 直接使用宿主机网络
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db
```

### 8.2 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| CONTROLLER_SESSION_KEY | "change-me" | Session 密钥 |
| DATABASE_URL | — | 数据库连接 |
| HOST | "0.0.0.0" | 监听地址 |
| PORT | 8883 | 监听端口 |

---

## 9. 当前测试覆盖

| 测试 | 文件 | 数量 | 覆盖范围 |
|---|---|---|---|
| API CRUD | tests/run_all.py | 47 | 9 个模块的增删改查 |
| E2E 页面 | tests/scripts/e2e-smoke.js | 22 | 所有模块页面加载 |
| 菜单功能 | tests/scripts/test-menu-click.js | 5 | Hub 点击 + 子页面可见性 |
| 零错误 | tests/scripts/test-full-log.js | 8 | 控制台 0 报错 + 0 失败请求 |
| 布局一致 | tests/scripts/test-layout.js | 8 | 所有页面 header/body 样式一致 |

---

## 10. 现状与已知问题

### 10.1 已完成
- [x] 9 个模块全部实现并部署（API + 模型 + 前端）
- [x] 模块化注册系统（BaseModule + 依赖解析）
- [x] 三级作用域（global/personal/project）
- [x] 标签页工作台（Alpine.js 动态加载）
- [x] Partial 模板系统（`_content.html`）
- [x] 统一布局（CSS 自动注入）
- [x] 3 个 Hub 导航（知识/技能/记忆）
- [x] Agent 上下文汇编器（Instructions + Skills + Rules + Knowledge）
- [x] 工作流执行引擎（步骤 + 状态追踪）
- [x] 种子数据（5 Agent + 2 工作流 + 3 文档模板）
- [x] 零控制台报错 + 5/5 菜单功能测试

### 10.2 已知边缘问题
- `pageevent` 底层错误（Playwright 级别捕获，浏览器控制台不可见）
- 同一组件名跨标签页覆盖（如 `globalSkillsPage` 被后续页面重定义）
- 隐藏标签页中 Alpine MutationObserver 的异步重初始化报错

### 10.3 待优化方向
- 组件函数名加标签页 ID 前缀避免冲突
- `window.onerror` 统一过滤 Alpine 运行时误报
- 统一错误处理层（当前各模块各自 try/catch）
- 分页/搜索/排序的统一参数规范
- 前端组件的进一步封装（减少每个 `_content.html` 的内联 JS）

---

## 11. 关键设计决策

### 11.1 为什么用 `replaceChildren` 而非 `innerHTML`

`innerHTML` 触发 Alpine MutationObserver 同步处理 DOM，此时组件函数尚未定义。`replaceChildren` 在临时 div 中构建完整 DOM → 定义函数 → 恢复 `x-data` → 批量插入，Alpine 只看到一个完整变更事件，消除 "is not defined" 错误。

### 11.2 为什么用 `x-show` 而非 `x-if`

`x-if` 销毁/重建 DOM，导致 Alpine 组件实例被销毁。`x-show` 保留 DOM 和组件状态，切换标签时无需重新初始化。

### 11.3 为什么布局用 CSS 而非模板类

15 个 `_content.html` 模板各自维护布局类导致不一致。将布局统一到 workspace.html 的 CSS 规则（`div:first-of-type` / `div:not(:first-of-type)`），新增页面自动继承，零维护成本。

### 11.4 为什么认证用 cookie 而非 token

SessionMiddleware + `aidp_session` cookie 简化部署（无需客户端存储 token），适合单体应用架构。API 路由复用了 `AuthService.validate_session()` 统一认证路径。