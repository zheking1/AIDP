# Web UI 概述

## 技术栈纠正

系统索引文档(`00-INDEX.md`)将前端标记为 "Vue 3 + Element Plus + Pinia"，但**实际实现**完全是不同的技术栈:

| 文档声明 | 实际实现 |
|---------|---------|
| Vue 3 | **Jinja2 模板** (服务端渲染) |
| Element Plus | **Tailwind CSS** (CDN 引入) |
| Pinia | **自定义 Store** (`store.js`) |

## 实际技术栈

| 层级 | 技术 |
|------|------|
| 模板引擎 | Jinja2 (`apps/controller/app/web/routes.py:13-17`) |
| CSS 框架 | Tailwind CSS 4 (CDN: `@tailwindcss/browser@4`) |
| 响应式逻辑 | Alpine.js 3.x (CDN) |
| 图标库 | Font Awesome 6.4.0 (CDN) |
| 状态管理 | 自研 Store (`static/js/core/store.js`) |
| HTTP 客户端 | 自研 APIClient (Fetch API 封装, `static/js/core/api.js`) |
| 事件总线 | 自研 EventBus (`static/js/core/events.js`) |
| 路由 | 服务端路由 (FastAPI routers, `web/routes.py`) |

## 前端代码位置

所有前端代码位于 `apps/controller/app/web/`:

```
apps/controller/app/web/
├── __init__.py
├── auth.py                 # 认证装饰器
├── routes.py               # FastAPI 路由 (页面 + API)
├── static/
│   └── js/
│       ├── aidp.js          # 主入口：AIDP 命名空间 + 页面数据
│       ├── core/
│       │   ├── api.js       # API 客户端
│       │   ├── store.js     # 全局状态管理
│       │   └── events.js    # 事件总线
│       ├── services/
│       │   ├── toolService.js   # 工具管理业务逻辑
│       │   └── proxyService.js  # 工具 Web UI 代理
│       └── components/
│           ├── ToolCard.js      # 工具卡片组件
│           ├── StatusBadge.js   # 状态徽章组件
│           ├── DataTable.js     # 数据表格组件
│           └── index.js         # 组件注册入口
└── templates/                   # Jinja2 模板
    ├── layouts/                 # 布局模板
    │   ├── base.html            # 基础布局 (带侧栏)
    │   ├── unified_base.html    # 新统一布局
    │   ├── workspace.html       # 工作区 (标签页式)
    │   └── embed.html           # 嵌入式布局
    ├── pages/                   # 独立页面
    │   ├── dashboard.html       # 仪表盘
    │   ├── tools.html           # 工具列表
    │   ├── tool_detail.html     # 工具详情
    │   ├── projects_new.html    # 项目列表
    │   ├── knowledge_hub.html   # 知识中心
    │   ├── skills_hub.html      # 技能库
    │   ├── memory_hub.html      # 记忆中心
    │   ├── project_dashboard.html # 项目仪表盘
    │   └── project_settings/    # 项目设置子页面
    ├── modules/                  # 功能模块页面
    │   ├── knowledge/           # 知识库 (bases, documents, search, templates)
    │   ├── memory/              # 记忆 (memories, graph)
    │   ├── skills/              # 技能 (global, personal)
    │   ├── rules/               # 规则 (global, personal)
    │   ├── agents/              # Agent 管理
    │   ├── assets/              # 代码资产
    │   ├── workflows/           # 流程管理
    │   ├── sandbox/             # 代码沙箱
    │   └── quality/             # 质量检查
    ├── admin/                    # 管理后台
    │   ├── users.html           # 用户管理
    │   ├── roles.html           # 角色管理
    │   ├── models.html          # 模型管理
    │   ├── settings.html        # 系统设置
    │   ├── projects.html        # 项目管理
    │   ├── skills.html          # 技能管理
    │   ├── audit_logs.html      # 审计日志
    │   └── tools.html           # 工具注册管理
    ├── auth/                     # 认证页面
    │   ├── login.html           # 登录
    │   ├── profile.html         # 个人资料
    │   └── api_keys.html        # API Keys
    └── onboarding.html          # 入门引导

```

## 页面架构概览

AIDP Web UI 是一个**多布局、服务端路由**的应用。Controller 通过 `web/routes.py` 定义所有页面路由，使用 Jinja2 渲染 HTML。前端通过 Alpine.js 提供页面级响应式交互。

### 三种渲染模式

1. **全量渲染**: 完整 HTML 页面，继承 `layouts/base.html` 或 `layouts/unified_base.html`
2. **内容渲染 (`?partial=1`)**: 仅返回 `_content.html` 内部内容片段，用于 SPA 式页面切换 (`routes.py:36-43`)
3. **iframe 嵌入**: 通过 Proxy 加载工具自带的 Web UI，HTML 重写后嵌入

### 认证机制

- 用户登录后设置 `aidp_session` cookie (`routes.py:52-55`)
- 每个页面路由检查 session cookie 验证登录状态
- 未登录用户自动重定向到 `/login`
- 管理页面额外检查 `is_admin()` 权限
- 装饰器方式也在 `auth.py` 中提供: `require_login`, `require_admin`

### 页面清单 (完整路由)

| 路由 | 页面 | 模板文件 | 访问控制 |
|------|------|---------|---------|
| `/login` | 登录页 | `auth/login.html` | 公开 |
| `/` | 工作区 (标签页) | `layouts/workspace.html` | 需登录 |
| `/dashboard` | 仪表盘 | `pages/dashboard.html` | 需登录 |
| `/tools` | 工具列表 | `pages/tools.html` | 需登录 |
| `/tools/{name}` | 工具详情 | `pages/tool_detail.html` | 需登录 |
| `/projects` | 项目列表 | `pages/projects_new.html` | 需登录 |
| `/profile` | 个人资料 | `auth/profile.html` | 需登录 |
| `/api-keys` | API Keys | `auth/api_keys.html` | 需登录 |
| `/admin/users` | 用户管理 | `admin/users.html` | Admin |
| `/admin/roles` | 角色管理 | `admin/roles.html` | Admin |
| `/admin/models` | 模型管理 | `admin/models.html` | Admin |
| `/admin/settings` | 系统设置 | `admin/settings.html` | Admin |
| `/admin/projects` | 项目管理 | `admin/projects.html` | Admin |
| `/admin/skills` | 技能管理 | `admin/skills.html` | Admin |
| `/admin/audit-logs` | 审计日志 | `admin/audit_logs.html` | Admin |
| `/admin/tools` | 工具注册管理 | `admin/tools.html` | Admin |
| `/admin/instructions` | 指令管理 | `admin/instructions_content.html` | Admin |
| `/hub/knowledge` | 知识中心 | `pages/knowledge_hub.html` | 需登录 |
| `/hub/skills` | 技能库 | `pages/skills_hub.html` | 需登录 |
| `/hub/memory` | 记忆中心 | `pages/memory_hub.html` | 需登录 |
| `/knowledge/bases` | 知识库列表 | `modules/knowledge/bases.html` | 需登录 |
| `/knowledge/documents` | 文档管理 | `modules/knowledge/documents.html` | 需登录 |
| `/knowledge/search` | 知识搜索 | `modules/knowledge/search.html` | 需登录 |
| `/knowledge/templates` | 文档模板 | `modules/knowledge/templates.html` | 需登录 |
| `/memory/memories` | 记忆管理 | `modules/memory/memories.html` | 需登录 |
| `/memory/graph` | 记忆图谱 | `modules/memory/graph.html` | 需登录 |
| `/memory/search` | 记忆检索 | `modules/memory/memories.html` | 需登录 |
| `/skills/global` | 全局技能 | `modules/skills/global.html` | 需登录 |
| `/skills/personal` | 个人技能 | `modules/skills/personal.html` | 需登录 |
| `/assets` | 代码资产 | `modules/assets/list.html` | 需登录 |
| `/sandbox` | 代码沙箱 | `modules/sandbox/index.html` | 需登录 |
| `/quality` | 质量检查 | `modules/quality/index.html` | 需登录 |
| `/agents` | Agent 管理 | `modules/agents/list.html` | 需登录 |
| `/workflows` | 流程管理 | `modules/workflows/list.html` | 需登录 |
| `/rules/global` | 全局规则 | `modules/rules/global.html` | 需登录 |
| `/rules/personal` | 个人规则 | `modules/rules/personal.html` | 需登录 |
| `/project/{id}/...` | 项目级页面 | 对应模块模板 | 需登录 |

## 前端如何连接 Controller

前端 JS 通过以下方式与后端通信:

1. **REST API 调用**: `AIDP.API.get/post/put/delete()` → Controller 的 `/api/*` 端点
2. **工具代理**: `/api/proxy/{tool_name}/{path}` → Controller 转发到目标工具
3. **工具 Web UI 嵌入**: `/tools/{tool_name}/web/{path}` → 代理 + HTML 重写
4. **Session Cookie**: `aidp_session` cookie 自动随请求发送，Controller 验证
5. **API 认证**: `fetch` 请求自动携带 session cookie，无需手动添加 token
6. **动态菜单**: `GET /api/menu` 返回当前用户的完整菜单配置

## 与系统索引文档的差异说明

`docs/aidp/00-INDEX.md` 描述的前端技术栈 (Vue 3 + Element Plus + Pinia) 与实际代码不一致。系统索引文档中的 `03-pages/`, `06-state.md`, `07-styles.md` 等章节描述的是规划中的架构，实际代码采用的是 Jinja2 + Alpine.js + Tailwind CSS 方案。建议同步更新索引文档。