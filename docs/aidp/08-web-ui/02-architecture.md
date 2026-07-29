# Web UI 架构

## 架构分层 (4 层)

`apps/controller/WEB_UI_ARCHITECTURE.md:9-28` 定义了 4 层架构:

```
┌──────────────────────────────────────────────────────────┐
│  Layer 4: Presentation Layer (展示层)                     │
│  ├── Layouts: base.html, unified_base.html, workspace.html│
│  ├── Pages: dashboard, tools, tool_detail, knowledge_hub..│
│  └── Components: ToolCard, StatusBadge, DataTable         │
├──────────────────────────────────────────────────────────┤
│  Layer 3: Application Layer (应用层)                       │
│  ├── Services: ToolService, ProxyService                  │
│  ├── Store: 全局状态管理 (store.js)                        │
│  └── EventBus: 事件总线 (events.js)                       │
├──────────────────────────────────────────────────────────┤
│  Layer 2: API Layer (接口层)                               │
│  ├── REST API Client (api.js)                             │
│  └── Proxy API: /api/proxy/{tool_name}/{path}             │
├──────────────────────────────────────────────────────────┤
│  Layer 1: Infrastructure (基础设施)                        │
│  ├── HTTP Client: Fetch API 封装                          │
│  └── Auth: aidp_session cookie + CSRF token               │
└──────────────────────────────────────────────────────────┘
```

## 目录结构 (实际代码)

```
apps/controller/app/web/
├── __init__.py                  # 空白文件 (Python 包标记)
├── auth.py                      # 认证装饰器 (require_login, require_admin)
├── routes.py                    # FastAPI 路由 (1238+ 行，所有页面+API)
├── static/
│   └── js/
│       ├── aidp.js              # 主入口: AIDP 命名空间、页面数据函数
│       ├── core/
│       │   ├── api.js           # API 客户端: APIClient 类
│       │   ├── store.js         # 状态管理: Store 类
│       │   └── events.js        # 事件总线: EventBus 类
│       ├── services/
│       │   ├── toolService.js   # 工具业务逻辑: ToolService 类
│       │   └── proxyService.js  # 工具代理: ProxyService 类
│       └── components/
│           ├── index.js         # 组件注册入口
│           ├── ToolCard.js      # 工具卡片组件
│           ├── StatusBadge.js   # 状态徽章组件
│           └── DataTable.js     # 数据表格组件
└── templates/
    ├── layouts/                 # 4 个布局模板
    ├── pages/                   # 14 个页面模板
    ├── modules/                 # 9 个功能模块目录
    ├── admin/                   # 13 个管理后台模板
    ├── auth/                    # 5 个认证模板
    └── components/              # 空目录 (预留)
```

## 路由系统

### 路由架构

AIDP Web UI 使用**服务端路由**。所有路由在 `apps/controller/app/web/routes.py` 中以 FastAPI `APIRouter` 形式定义。

### 关键路由函数

| 函数 | 位置 | 功能 |
|------|------|------|
| `render_template()` | `routes.py:27-47` | 渲染 Jinja2 模板，注入 `request`, `embed`, `partial` 上下文 |
| `get_template()` | `routes.py:22-24` | 获取 Jinja2 模板对象 |
| `get_current_user_from_request()` | `routes.py:50-55` | 从 `aidp_session` cookie 提取当前用户 |
| `rewrite_tool_html()` | `routes.py:482-508` | 重写工具 HTML (链接/CSS/JS 代理) |

### 路由分类

1. **认证页面** (`routes.py:62-87`): `/login`, `/logout`
2. **主页/工作区** (`routes.py:93-111`): `/`, `/home`, `/dashboard`
3. **Frame 页面** (`routes.py:132-202`): 用于 iframe 嵌入的内容片段 (含 `-frame` 后缀)
4. **工具管理** (`routes.py:320-440`): `/tools`, `/tools/{name}`, `/tools-frame`
5. **项目管理** (`routes.py:350-410`): `/projects`, `/admin/projects`
6. **知识中心** (`routes.py:674-757`): `/hub/knowledge`, `/knowledge/*`
7. **记忆中心** (`routes.py:764-801`): `/memory/*`, `/hub/memory`
8. **技能管理** (`routes.py:808-840`): `/skills/*`, `/hub/skills`
9. **资产管理** (`routes.py:847-866`): `/assets`, `/assets/search`
10. **DevTools** (`routes.py:873-896`): `/sandbox`, `/quality`
11. **规则管理** (`routes.py:903-934`): `/rules/*`
12. **Agent/Workflow** (`routes.py:941-986`): `/agents`, `/workflows`
13. **管理后台** (`routes.py:241-314, 993-1034`): `/admin/{users,roles,models,settings,projects,skills,audit-logs,instructions,tools}`
14. **项目内部路由** (`routes.py:1041-1210`): `/project/{id}/{dashboard,settings,modules,...}`
15. **代理路由** (`routes.py:416-576`): `/api/proxy/{tool_name}/{path}`, `/tools/{tool_name}/web/{path}`
16. **API 端点** (`routes.py:618-668`): `/api/menu`, `/api/config/menu.yaml`, `/api/config/reload`

## 布局系统

### 4 种布局

| 布局文件 | 路径 | 用途 |
|---------|------|------|
| `base.html` | `templates/layouts/base.html` | 带侧栏的基础布局，含 CSRF meta 标签 |
| `unified_base.html` | `templates/layouts/unified_base.html` | 新统一布局，含顶部导航栏 + 侧栏 |
| `workspace.html` | `templates/layouts/workspace.html` | 工作区多标签页布局 |
| `embed.html` | `templates/layouts/embed.html` | 嵌入式布局 (无导航) |

### 公共依赖 (所有布局共享)

| 资源 | 来源 | 说明 |
|------|------|------|
| Tailwind CSS 4 | `cdn.jsdelivr.net/npm/@tailwindcss/browser@4` | CDN 引入，浏览器端编译 |
| Alpine.js 3.x | `cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js` | 轻量响应式框架 |
| Font Awesome 6.4.0 | `cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css` | 图标库 |

### base.html 公共样式 (`base.html:19-79`)

- 自定义滚动条样式 (暗色主题)
- 侧栏 hover/active 效果
- 工具卡片 hover 动效
- 状态点样式 (.status-healthy, .status-registered, .status-unhealthy, etc.)
- fadeIn 入场动画 (.animate-fade-in)
- `[x-cloak] { display: none !important }` 防闪烁

### unified_base.html 额外特性 (`unified_base.html:17-66`)

- Google Fonts: Inter 字体
- Toast 动画 (slideIn/slideOut)
- 顶部固定导航栏 (`h-14`)
- 响应式侧栏

### workspace.html 特殊性 (`workspace.html:11-100`)

- 为所有已知 Alpine 变量提供全局默认值 (防止 ReferenceError)
- 预定义了所有常见的布尔、字符串、数组、对象变量

## 组件树

### 模块加载顺序

模板中 JS 脚本加载顺序:
1. 布局模板中的 Alpine.js CDN (最早加载)
2. `aidp.js` - 主入口 (IIFE 包装，注册到 `window.AIDP`)
3. `core/store.js` - 创建 `window.AIDP.store` 全局 Store 实例
4. `core/api.js` - 创建 `window.AIDP.API` 全局 APIClient 实例
5. `core/events.js` - 创建 `window.AIDP.events` 全局 EventBus 实例
6. `services/toolService.js` - 创建 `window.AIDP.toolService` 实例
7. `services/proxyService.js` - 创建 `window.AIDP.proxyService` 实例
8. `components/ToolCard.js` - 注册到 `window.AIDP.components.ToolCard`
9. `components/StatusBadge.js` - 注册到 `window.AIDP.components.StatusBadge`
10. `components/DataTable.js` - 注册到 `window.AIDP.components.DataTable`
11. `components/index.js` - 调用 `Alpine.data()` 注册所有组件

### 页面组件实例化

每个页面的 Alpine.js 数据函数定义在 `aidp.js` 中:

| 函数 | 用途 |
|------|------|
| `AIDP.layoutData()` | 布局级：侧栏折叠、通知系统、偏好持久化 |
| `AIDP.dashboardData()` | 仪表盘：工具列表、调用历史、项目统计、自动刷新 |
| `AIDP.toolsPageData()` | 工具列表：搜索、筛选、排序、批量操作 |
| `AIDP.toolDetailData(toolName)` | 工具详情：Web UI 嵌入、健康检查、能力同步 |

模块页面的 Alpine 函数**内联定义在各自的模板中** (如 `sandbox/index.html:88-115` 的 `window.sandboxPage`)。

## 状态管理

### Store 核心类 (`core/store.js`)

**源文件**: `apps/controller/app/web/static/js/core/store.js`

`Store` 类提供：
- **嵌套路径访问**: `store.get('tools.list')`, `store.set('tools.list', value)`
- **订阅机制**: `store.subscribe(path, callback)` 返回取消订阅函数
- **穿透通知**: 修改 `tools.list` 时也通知 `tools` 和 `*` 的订阅者
- **深度合并**: `store.update(updates)` 递归合并状态
- **批量更新**: `store.batch(updateFn)` 合并通知
- **计算属性**: `store.computed(name, fn)` 缓存计算值
- **Alpine 适配**: `store.toAlpineData()` 转换为 Alpine 兼容对象

### 全局初始状态 (`store.js:208-246`)

```javascript
{
    tools: {
        list: [],           // 工具列表
        loading: false,
        error: null,
        selected: null,     // 当前选中的工具
        filter: { query: '', status: '' }
    },
    dashboard: {
        stats: {
            totalTools: 0,
            healthyTools: 0,
            totalProjects: 0,
            recentInvocations: []
        },
        loading: false
    },
    ui: {
        sidebarCollapsed: false,
        currentPage: 'dashboard',
        modal: null,
        notifications: []
    },
    user: {
        id: null,
        name: '',
        role: 'user'
    }
}
```

## 事件总线

### EventBus 核心类 (`core/events.js`)

**源文件**: `apps/controller/app/web/static/js/core/events.js`

提供方法：
- `on(event, callback)` - 订阅事件，返回取消函数
- `once(event, callback)` - 一次性订阅
- `off(event, callback)` - 取消订阅
- `emit(event, data)` - 同步触发
- `emitAsync(event, data)` - 异步并行触发
- `removeAll(event)` - 清除监听器
- `listenerCount(event)` - 获取监听器数量

### 预定义事件 (`events.js:137-166`)

| 事件名 | 常量 | 触发时机 |
|--------|------|---------|
| `tools:loaded` | `Events.TOOLS_LOADED` | 工具列表加载完成 |
| `tool:selected` | `Events.TOOL_SELECTED` | 选中工具 |
| `tool:status_changed` | `Events.TOOL_STATUS_CHANGED` | 工具状态变化 |
| `tool:health_check` | `Events.TOOL_HEALTH_CHECK` | 健康检查 |
| `dashboard:refresh` | `Events.DASHBOARD_REFRESH` | 仪表盘刷新 |
| `stats:updated` | `Events.STATS_UPDATED` | 统计数据更新 |
| `page:changed` | `Events.PAGE_CHANGED` | 页面切换 |
| `modal:open/close` | `Events.MODAL_OPEN/CLOSE` | 弹窗操作 |
| `notification:show/hide` | `Events.NOTIFICATION_SHOW/HIDE` | 通知显示/隐藏 |
| `sidebar:toggle` | `Events.SIDEBAR_TOGGLE` | 侧栏折叠 |
| `navigate` | `Events.NAVIGATE` | 页面跳转 |
| `error:occurred` | `Events.ERROR_OCCURRED` | 错误发生 |
| `loading:start/end` | `Events.LOADING_START/END` | 加载状态 |

### 事件总线辅助方法 (`events.js:172-193`)

```javascript
eventBus.notify(message, type, duration)   // 快捷通知
eventBus.error(message, error)             // 错误日志 + 通知
eventBus.loading(promise, message)         // 加载状态包装
```

## 应用初始化流程

`aidp.js:37-55` 定义 `AIDP.init()`:
1. 合并传入配置
2. 将 `options.user` 存入 Store
3. 调用 `loadInitialData()` 预加载工具列表
4. 注册全局事件监听器 (导航、错误、标签页可见性)
5. `DOMContentLoaded` 自动触发 `AIDP.init()`

`loadInitialData()` (`aidp.js:60-68`) 只做一件事：调用 `AIDP.toolService.getTools()` 预加载工具列表。

## 数据流总结

```
用户操作 → Alpine.js (x-on:click, x-model)
    ↓
Alpine 数据函数 (dashboardData, toolsPageData, etc.)
    ↓
Service 层 (toolService, proxyService)
    ↓
API 层 (AIDP.API.get/post/etc.)
    ↓
fetch() → Controller /api/* 端点
    ↓
响应 → Store.set() → 订阅者通知 → Alpine 自动重渲染
         ↓
      事件总线 → 其他组件监听响应
```

## 关键文件索引

| 文件 | 行数 | 职责 |
|------|------|------|
| `routes.py` | ~1238 | 全部页面路由 + API 路由 + 代理路由 |
| `auth.py` | 33 | `require_login`, `require_admin` 装饰器 |
| `aidp.js` | 432 | 主入口、页面数据函数、自动初始化 |
| `core/api.js` | 198 | APIClient 类, CSRF 拦截器, 自动重试 |
| `core/store.js` | 253 | Store 类, 全局初始状态 |
| `core/events.js` | 201 | EventBus 类, 预定义事件, 辅助方法 |
| `services/toolService.js` | 390 | 工具 CRUD, 健康检查, 统计, 自动刷新 |
| `services/proxyService.js` | 425 | 工具 Web UI 代理, HTML 重写, iframe 模态 |
| `components/ToolCard.js` | 184 | 工具卡片: 图标/状态/操作按钮 |
| `components/StatusBadge.js` | 162 | 状态徽章: 圆点+文字/ISO尺寸 |
| `components/DataTable.js` | 420 | 数据表格: 排序/搜索/分页/行选择 |
| `components/index.js` | 39 | Alpine 组件注册 |