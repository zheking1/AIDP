# API 层设计

## 概述

AIDP Web UI 的 API 层由自定义 `APIClient` 类实现，存储在 `apps/controller/app/web/static/js/core/api.js`。使用原生 `fetch` API，不依赖 Axios。

## APIClient 核心类

**源文件**: `apps/controller/app/web/static/js/core/api.js`

### 配置 (`api.js:9-14`)

```javascript
const API_CONFIG = {
    baseUrl: '',            // 空字符串 = 同源请求
    timeout: 30000,         // 30 秒超时
    retries: 3,             // 最多重试 3 次
    retryDelay: 1000        // 初始重试延迟 1 秒 (指数递增)
};
```

### HTTP 方法封装 (`api.js:149-167`)

```javascript
api.get(endpoint, options)
api.post(endpoint, data, options)
api.put(endpoint, data, options)
api.patch(endpoint, data, options)
api.delete(endpoint, options)
```

所有方法调用内部 `request()` 函数。

### 请求流程 (`api.js:73-139`)

```
1. 拼接 URL: baseUrl + endpoint
2. 设置默认 headers: Content-Type: application/json, Accept: application/json
3. JSON 序列化 body (POST/PUT/PATCH)
4. 执行请求拦截器 chain
5. 发送 fetch 请求 (带 AbortController 超时)
6. 处理 204 No Content → 返回 null
7. 执行响应拦截器 chain
8. 成功: 返回 response.json()
9. 失败:
   - 4xx 错误: 立即抛出，不重试
   - 5xx/网络错误: 最多重试 3 次，指数退避 (1s, 2s, 3s)
```

### 拦截器系统

#### 请求拦截器 (`api.js:37-39`)

```javascript
api.addRequestInterceptor(fn)   // 注册
api.applyRequestInterceptors()  // 内部执行
```

每个拦截器接收 `(url, options)` 并返回 `{url, options}`。

#### 响应拦截器 (`api.js:44-46`)

```javascript
api.addResponseInterceptor(fn)  // 注册
api.applyResponseInterceptors() // 内部执行
```

每个拦截器接收 `response` 对象并返回 `response`。

---

## 内置拦截器

### 1. CSRF Token 注入 (`api.js:174-181`)

```javascript
api.addRequestInterceptor((url, options) => {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
    if (csrfToken) {
        options.headers['X-CSRF-Token'] = csrfToken;
    }
    return { url, options };
});
```

CSRF token 来源: `base.html` 中的 `<meta name="csrf-token" content="{{ csrf_token }}">`。

### 2. 响应错误日志 (`api.js:184-190`)

```javascript
api.addResponseInterceptor(async (response) => {
    if (!response.ok) {
        console.error(`API Error: ${response.status} ${response.statusText}`);
    }
    return response;
});
```

---

## 全局实例

`api.js:171` 创建全局单例 `AIDP.API`:

```javascript
const api = new APIClient();
global.AIDP.API = api;
```

所有前端代码使用 `AIDP.API.get()`, `AIDP.API.post()` 等方法。

### 单次请求示例

```javascript
// 获取工具列表
const tools = await AIDP.API.get('/api/tools');

// 获取单个工具
const tool = await AIDP.API.get('/api/tools/sandbox-tool');

// 健康检查
const result = await AIDP.API.post('/api/tools/sandbox-tool/health');

// 调用工具
const output = await AIDP.API.post('/api/tools/sandbox-tool/invoke', {
    capability: 'sandbox.execute',
    arguments: { code: 'print(1)', language: 'python' }
});
```

---

## 认证处理

### Session Cookie 机制

AIDP Web UI 使用传统的 **server-side session cookie** 认证，而非 JWT/Token-based:

1. **登录**: POST `/api/auth/login/form` 设置 `aidp_session` cookie
2. **请求验证**: Controller 从 cookie 中提取 session token (`routes.py:50-55`)
3. **重定向**: 无有效 session 时返回 302 到 `/login`
4. **Admin 权限**: Controller 检查 `user.role` 是否为 `admin` 或 `super_admin`

### 前端认证流程

由于使用 cookie，前端 **不需要** 手动添加 Authorization header：
- `fetch` 请求自动携带同源 cookie
- `Content-Type: application/json` 是唯一需要的手动 header
- 无 `Authorization` header 或 Bearer token
- 登录页面 POST 表单到 `/api/auth/login/form`

### 认证错误处理

`APIClient` 不拦截 401/403 做自动跳转。页面级路由通过 Controller 端的 `get_current_user_from_request()` 在渲染模板前即验证，未登录直接 302 到 `/login`。

---

## 代理 API

### 架构位置

前端不直接调用各工具 (sandbox-tool, quality-tool, etc.) 的内部 API，而是通过 Controller 的代理路由转发。

### 代理路由

| 路由模式 | 目标 | 源码位置 |
|---------|------|---------|
| `/api/proxy/{tool_name}/{path}` | 代理 API 请求到工具 | `routes.py:416-479` |
| `/tools/{tool_name}/web/{path}` | 代理 Web UI 请求到工具 | `routes.py:515-576` |

### 代理请求头注入 (`routes.py:442-445`)

Controller 在代理时添加以下 header:
```python
headers["X-Forwarded-By"] = "AIDP-Controller"
headers["X-Forwarded-For"] = request.client.host
headers["X-User-ID"] = str(user.id)
headers["X-User-Role"] = user.role
```

### 代理与前端调用流

```
前端 JS 代码
    ↓
AIDP.API.post('/api/tools/sandbox-tool/invoke', args)
    ↓
Controller 路由 → get_tool('sandbox-tool') → 获取 endpoint URL
    ↓
httpx.AsyncClient → POST http://127.0.0.1:18083/tool/invoke
    ↓
sandbox-tool 响应 → Controller 原样返回给前端
```

### 沙箱/质量页面的直接调用

在 `modules/sandbox/index.html:98` 中，沙箱页面**直接**调用快捷路径:
```javascript
fetch('/api/sandbox/execute', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({code, language, stdin})
})
```

这里的 `/api/sandbox/execute` 也是通过 Controller 转发到 sandbox-tool 的 `/api/execute` 端点 (在 Controller 的 API routers 中注册)。

---

## 错误处理

### APIError 类 (`api.js:16-23`)

```javascript
class APIError extends Error {
    constructor(message, status, data) {
        super(message);
        this.name = 'APIError';
        this.status = status;     // HTTP 状态码
        this.data = data;         // 服务器返回的错误体
    }
}
```

### 重试策略 (`api.js:123-136`)

```
- 4xx 错误: 客户端错误，立即抛出，不重试
- 5xx 错误 / 网络错误 / 超时: 自动重试，最多 3 次
- 重试延迟: retryDelay * (attempt + 1) → 1s, 2s, 3s
```

### AbortController 超时 (`api.js:95-96`)

```javascript
const controller = new AbortController();
const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);
// ... fetch ...
clearTimeout(timeoutId);
```

---

## Service 层的 API 使用模式

### ToolService (`services/toolService.js`)

`ToolService` 封装所有工具管理的 API 调用：

| 方法 | API 端点 | 方法 |
|------|---------|------|
| `getTools()` | `GET /api/tools` | GET |
| `getTool(name)` | `GET /api/tools/{name}` | GET |
| `registerTool(data)` | `POST /api/tools` | POST |
| `updateTool(name, data)` | `PUT /api/tools/{name}` | PUT |
| `deleteTool(name)` | `DELETE /api/tools/{name}` | DELETE |
| `checkHealth(name)` | `POST /api/tools/{name}/health` | POST |
| `checkAllHealth()` | `GET /api/tools/health/all` | GET |
| `syncCapabilities(name)` | `POST /api/tools/{name}/sync` | POST |
| `enableTool(name)` | `POST /api/tools/{name}/enable` | POST |
| `disableTool(name)` | `POST /api/tools/{name}/disable` | POST |
| `getInvocationHistory(opts)` | `GET /api/tools/invocations/history` | GET |
| `invoke(toolName, cap, args)` | `POST /api/tools/{name}/invoke` | POST |

### 缓存机制 (`toolService.js:12-14`)

```javascript
this.cache = new Map();
this.cacheTTL = 30000;  // 30 秒
```

`getTools()` 默认使用缓存，`forceRefresh: true` 时绕过缓存。每次修改操作后自动清除缓存。

### 自动刷新 (`toolService.js:379-383`)

```javascript
setInterval(() => {
    if (document.visibilityState === 'visible') {
        toolService.checkAllHealth().catch(() => {});
    }
}, 60000);
```

每 60 秒自动检查所有工具健康状态，仅在标签页可见时执行。

### ProxyService (`services/proxyService.js`)

封装工具 Web UI 的代理请求和 HTML 重写：

| 方法 | 功能 |
|------|------|
| `getToolUrl(name)` | 从 Store 中获取工具 endpoint |
| `hasWebUI(name)` | 检查工具是否有 Web UI |
| `fetchToolPage(name, path)` | 通过 `/api/proxy/{name}{path}` 获取 HTML |
| `rewriteHTML(html, name, basePath)` | DOM 解析 + 链接重写 + 样式注入 |
| `loadToolInIframe(name, container)` | 创建 iframe 指向代理 URL |
| `loadToolWithRewrite(name, container)` | 获取 HTML → 重写 → 注入容器 |
| `getToolInfo(name)` | 从 Store 获取工具完整信息 |
| `refreshAll()` | 刷新所有活跃代理 iframe |
| `cleanup(name?)` | 清理代理资源 |

### 工具间通信 (`proxyService.js:407-418`)

嵌入的工具页面通过 `postMessage` 与父窗口通信:
```javascript
window.addEventListener('message', (event) => {
    if (data?.type?.startsWith('aidp:')) {
        events.emit(data.type, data);  // 桥接到 AIDP 事件总线
        if (data.type === 'aidp:tool:navigate') {
            window.location.href = data.href;
        }
    }
});
```

### HTML 重写 (`proxyService.js:94-160`)

`rewriteHTML` 方法使用 DOM API 操作 HTML:
1. 移除导航栏 (`nav`, `header`, `.navbar`, `[role="navigation"]`)
2. 重写 `<a href>` → 转换为代理路径
3. 重写 `<form action>` → 转换为代理路径
4. 重写资源 URL (CSS/JS/图片) → 转换为代理路径
5. 注入统一样式 (暗色背景、隐藏工具导航)
6. 注入桥接脚本 (标记 `aidp-embedded` 类、发送 ready 消息)

---

## API 端点索引 (Web UI 使用)

### 公开端点

| 端点 | 方法 | 说明 | 源码 |
|------|------|------|------|
| `/login` | GET | 登录页面 | `routes.py:62` |
| `/api/auth/login/form` | POST | 表单登录 | `routes.py` (外部 Auth router) |

### 认证端点

| 端点 | 方法 | 说明 | 源码 |
|------|------|------|------|
| `/logout` | GET | 登出 | `routes.py:77` |

### 核心 API (页面级)

| 端点 | 方法 | 说明 | 源码 |
|------|------|------|------|
| `/api/menu` | GET | 获取用户菜单配置 | `routes.py:618` |
| `/api/config/menu.yaml` | GET | 获取原始菜单 YAML (Admin) | `routes.py:636` |
| `/api/config/reload` | POST | 热重载配置 (Admin) | `routes.py:652` |

### 工具 API (通过 Service 层)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/tools` | GET | 获取工具列表 |
| `/api/tools` | POST | 注册工具 |
| `/api/tools/{name}` | GET | 获取工具详情 |
| `/api/tools/{name}` | PUT | 更新工具 |
| `/api/tools/{name}` | DELETE | 删除工具 |
| `/api/tools/{name}/health` | POST | 健康检查 |
| `/api/tools/health/all` | GET | 批量健康检查 |
| `/api/tools/{name}/enable` | POST | 启用工具 |
| `/api/tools/{name}/disable` | POST | 禁用工具 |
| `/api/tools/{name}/sync` | POST | 同步能力 |
| `/api/tools/{name}/invoke` | POST | 调用工具 |
| `/api/tools/invocations/history` | GET | 调用历史 |

### 快捷代理端点 (直接路径)

| 端点 | 说明 | 目标工具 |
|------|------|---------|
| `/api/sandbox/execute` | 执行代码 | sandbox-tool |
| `/api/sandbox/history` | 执行历史 | sandbox-tool |
| `/api/quality/check` | 质量检查 | quality-tool |
| `/api/quality/history` | 检查历史 | quality-tool |

### 通用代理端点

| 端点 | 方法 | 说明 | 源码 |
|------|------|------|------|
| `/api/proxy/{tool_name}/{path}` | ALL | 通用工具 API 代理 | `routes.py:416` |
| `/tools/{tool_name}/web/{path}` | ALL | 通用工具 Web UI 代理 | `routes.py:515` |

---

## 关键文件索引

| 文件 | 行数 | 职责 |
|------|------|------|
| `core/api.js` | 198 | APIClient 类定义, 拦截器, 重试逻辑 |
| `services/toolService.js` | 390 | 工具管理 API 封装, 缓存, 自动刷新 |
| `services/proxyService.js` | 425 | 工具 Web UI 代理, HTML 重写, iframe 管理 |
| `web/routes.py` | ~1238 | 全部 Controller 路由定义 |
| `web/auth.py` | 33 | 认证装饰器 |