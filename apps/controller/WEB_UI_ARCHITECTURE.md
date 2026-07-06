# AIDP Web UI 架构文档

## 概述

AIDP 统一 Web UI 采用模块化、分层架构设计，支持集中管理所有工具，同时每个工具可以独立查看和管理。

## 架构分层

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 4: Presentation Layer (展示层)                           │
│  ├── Layouts: 统一布局系统                                       │
│  ├── Pages: 页面模块 (Dashboard, Tools, ToolDetail)              │
│  └── Components: 可复用组件                                       │
├─────────────────────────────────────────────────────────────────┤
│  Layer 3: Application Layer (应用层)                            │
│  ├── Services: ToolService, ProxyService                         │
│  ├── Store: 全局状态管理                                          │
│  └── EventBus: 事件总线                                          │
├─────────────────────────────────────────────────────────────────┤
│  Layer 2: API Layer (接口层)                                    │
│  ├── REST API Client                                             │
│  └── Proxy API: 工具代理转发                                      │
├─────────────────────────────────────────────────────────────────┤
│  Layer 1: Infrastructure (基础设施)                             │
│  ├── HTTP Client (Fetch API)                                     │
│  └── Auth Middleware                                             │
└─────────────────────────────────────────────────────────────────┘
```

## 目录结构

```
apps/controller/app/web/
├── static/                          # 静态资源
│   ├── js/
│   │   ├── core/                   # 核心模块
│   │   │   ├── api.js              # API 客户端
│   │   │   ├── store.js            # 状态管理
│   │   │   └── events.js           # 事件总线
│   │   ├── services/               # 业务服务
│   │   │   ├── toolService.js      # 工具服务
│   │   │   └── proxyService.js     # 代理服务
│   │   ├── components/             # 可复用组件
│   │   │   ├── ToolCard.js         # 工具卡片
│   │   │   ├── StatusBadge.js      # 状态徽章
│   │   │   ├── DataTable.js        # 数据表格
│   │   │   └── index.js            # 组件注册
│   │   └── aidp.js                 # 主入口
│   └── css/                        # 样式文件
├── templates/                       # HTML 模板
│   ├── layouts/                    # 布局模板
│   │   └── base.html               # 基础布局
│   ├── pages/                      # 页面模板
│   │   ├── dashboard.html          # 总览页
│   │   ├── tools.html              # 工具列表页
│   │   └── tool_detail.html        # 工具详情页
│   └── components/                 # 组件模板
└── routes.py                       # 路由定义
```

## 核心模块

### 1. API Client (`core/api.js`)

标准化的 HTTP 客户端：

```javascript
// 使用示例
const tools = await AIDP.API.get('/api/tools');
const result = await AIDP.API.post('/api/tools/sandbox/invoke', {
    capability: 'sandbox.execute',
    arguments: { code: 'print("Hello")' }
});
```

特性：
- 统一的错误处理
- 自动重试机制
- 请求/响应拦截器
- 超时控制

### 2. State Management (`core/store.js`)

简单的中心化状态管理：

```javascript
// 读取状态
const tools = AIDP.store.get('tools.list');

// 更新状态
AIDP.store.set('tools.list', newTools);

// 订阅变化
AIDP.store.subscribe('tools.list', (newVal, oldVal) => {
    console.log('Tools updated:', newVal);
});
```

### 3. Event Bus (`core/events.js`)

组件间通信：

```javascript
// 订阅事件
AIDP.events.on(AIDP.Events.TOOL_STATUS_CHANGED, (data) => {
    console.log('Tool status changed:', data);
});

// 触发事件
AIDP.events.emit(AIDP.Events.TOOLS_LOADED, tools);

// 快速通知
AIDP.events.notify('Tool registered successfully', 'success');
```

## 服务层

### ToolService (`services/toolService.js`)

工具管理业务逻辑：

```javascript
// 获取所有工具
const tools = await AIDP.toolService.getTools();

// 健康检查
await AIDP.toolService.checkHealth('sandbox-tool');

// 启用/禁用工具
await AIDP.toolService.enableTool('sandbox-tool');
await AIDP.toolService.disableTool('sandbox-tool');

// 获取统计
const stats = AIDP.toolService.getStats();
```

### ProxyService (`services/proxyService.js`)

工具 Web UI 代理：

```javascript
// 加载工具 Web UI 到 iframe
await AIDP.proxyService.loadToolInIframe('knowledge-tool', container, {
    path: '/documents',
    onLoad: (iframe) => console.log('Loaded!')
});

// 获取工具信息
const info = AIDP.proxyService.getToolInfo('memory-tool');
```

## 组件系统

### ToolCard

```html
<div x-data="AIDP.components.ToolCard({ tool: toolData, size: 'md' })">
    <!-- 渲染 ToolCard 模板 -->
</div>
```

### StatusBadge

```html
<div x-data="AIDP.components.StatusBadge({ status: 'healthy', size: 'md' })">
    <span x-html="AIDP.components.StatusBadgeTemplate"></span>
</div>
```

### DataTable

```html
<div x-data="AIDP.components.DataTable({
    columns: [
        { key: 'name', title: '名称', sortable: true },
        { key: 'status', title: '状态' }
    ],
    data: tools,
    onRefresh: async () => await loadData()
})">
    <div x-html="AIDP.components.DataTableTemplate"></div>
</div>
```

## 路由

### 页面路由

| 路由 | 页面 | 说明 |
|------|------|------|
| `/` | Dashboard | 总览页 |
| `/tools` | 工具列表 | 所有工具管理 |
| `/tools/{name}` | 工具详情 | 嵌入工具 Web UI |
| `/tools/manage` | 工具注册 | 注册新工具 |

### 代理路由

| 路由 | 说明 |
|------|------|
| `/api/proxy/{tool_name}/{path}` | 代理请求到工具 |

示例：
- `/api/proxy/knowledge-tool/documents` → 代理到知识库工具的文档页面
- `/api/proxy/memory-tool/api/memory` → 代理到记忆工具的 API

## 工具 Web UI 集成

### 方式 1: Iframe 嵌入

```html
<iframe :src="tool.endpoint" class="w-full h-full"></iframe>
```

### 方式 2: 代理 + HTML 重写

Controller 代理工具请求并重写 HTML：

1. 转发请求到工具端点
2. 重写相对链接（CSS, JS, 图片）
3. 注入桥接脚本
4. 返回重写后的 HTML

## 使用示例

### 在页面中使用

```html
{% extends "layouts/base.html" %}

{% block content %}
<div x-data="myPageData()" x-init="init()">
    <!-- 页面内容 -->
</div>

<script>
function myPageData() {
    return {
        async init() {
            // 使用服务层
            const tools = await AIDP.toolService.getTools();
            
            // 使用状态管理
            AIDP.store.set('myPage.data', tools);
            
            // 监听事件
            AIDP.events.on(AIDP.Events.TOOL_STATUS_CHANGED, (data) => {
                console.log('Status changed:', data);
            });
        }
    };
}
</script>
{% endblock %}
```

## 开发规范

### 命名规范

- **类名**: PascalCase (`ToolService`, `APIClient`)
- **函数/变量**: camelCase (`getTools`, `handleClick`)
- **常量**: UPPER_SNAKE_CASE (`API_CONFIG`, `MAX_RETRY`)
- **文件**: kebab-case (`tool-service.js`)

### 错误处理

```javascript
try {
    const result = await AIDP.toolService.getTools();
} catch (error) {
    // 全局错误处理
    AIDP.events.error('Failed to load tools', error);
    
    // 或者本地处理
    console.error('Error:', error.message);
}
```

### 性能优化

1. **缓存**: ToolService 自动缓存工具列表
2. **防抖**: 搜索输入使用防抖
3. **懒加载**: 组件按需加载
4. **WebSocket**: 实时数据推送（可选）

## 扩展指南

### 添加新页面

1. 在 `templates/pages/` 创建 HTML 文件
2. 在 `routes.py` 添加路由
3. 在 `aidp.js` 添加页面数据函数

### 添加新组件

1. 在 `static/js/components/` 创建 JS 文件
2. 导出组件数据函数和模板
3. 在 `components/index.js` 注册

### 添加新服务

1. 在 `static/js/services/` 创建 JS 文件
2. 实现业务逻辑
3. 导出为 `AIDP.serviceName`

## 技术栈

- **Backend**: Python 3.13 + FastAPI
- **Frontend**: Alpine.js 3.x + Tailwind CSS
- **Templates**: Jinja2
- **Icons**: Font Awesome 6
- **HTTP Client**: Fetch API (native)

## 部署

静态文件会自动挂载到 `/static` 路径：

```python
app.mount("/static", StaticFiles(directory="app/web/static"), name="static")
```

无需构建步骤，直接部署即可使用。
