# 公共组件

AIDP Web UI 的可复用组件分为两个层面：**Alpine.js 组件函数**（定义在 JS 文件中）和 **HTML 模板片段**（存在于 Jinja2 模板中）。

## 1. JS 组件系统

### 组件注册机制 (`components/index.js`)

**源文件**: `apps/controller/app/web/static/js/components/index.js:14-26`

所有 JS 组件通过 Alpine.js 的 `Alpine.data()` API 注册：

```javascript
Alpine.data('toolCard', (options) => components.ToolCard(options));
Alpine.data('statusBadge', (options) => components.StatusBadge(options));
Alpine.data('statusDot', (options) => components.StatusDot(options));
Alpine.data('dataTable', (options) => components.DataTable(options));
```

组件在 `alpine:init` 事件触发时自动注册，或等 Alpine 加载后立即注册。

### 组件目录

| 组件 | 文件 | 导出 | Alpine 名 |
|------|------|------|-----------|
| ToolCard | `components/ToolCard.js` | `ToolCard`, `ToolCardTemplate` | `toolCard` |
| StatusBadge | `components/StatusBadge.js` | `StatusBadge`, `StatusBadgeTemplate`, `StatusDot`, `StatusDotTemplate` | `statusBadge`, `statusDot` |
| DataTable | `components/DataTable.js` | `DataTable`, `DataTableTemplate` | `dataTable` |

---

## 2. ToolCard 组件

**源文件**: `apps/controller/app/web/static/js/components/ToolCard.js`

### 配置参数

```javascript
AIDP.components.ToolCard({
    tool: {},               // 工具对象 {name, displayName, status, description, capabilities, version}
    size: 'md',             // 'sm' | 'md' | 'lg'
    showActions: true,      // 是否显示操作按钮
    selectable: false,      // 是否可选模式
})
```

### 工具图标映射 (`ToolCard.js:29-43`)

| 工具名 | 图标 | Font Awesome |
|--------|------|-------------|
| `skill-router` | 路由 | `fa-route` |
| `knowledge-tool` | 书籍 | `fa-book` |
| `asset-tool` | 档案 | `fa-box-archive` |
| `sandbox-tool` | 烧瓶 | `fa-flask` |
| `quality-tool` | 盾牌 | `fa-shield-check` |
| `memory-tool` | 大脑 | `fa-brain` |
| `code-index` | 代码 | `fa-code` |
| `doc-index` | 文件行 | `fa-file-lines` |
| `context-optimizer` | 压缩 | `fa-compress` |
| `evolution-engine` | DNA | `fa-dna` |
| `project-importer` | 上传 | `fa-upload` |
| `controller` | 手柄 | `fa-gamepad` |
| 其他 | 立方体 | `fa-cube` (默认) |

### 状态颜色/文字 (`ToolCard.js:49-72`)

| 状态 | 颜色 | 中文 |
|------|------|------|
| `healthy` | green | 健康 |
| `registered` | yellow | 已注册 |
| `unhealthy` | red | 异常 |
| `unreachable` | gray | 不可达 |
| `disabled` | gray | 已禁用 |

### 三种尺寸 (`ToolCard.js:77-96`)

| 尺寸 | 内边距 | 图标容器 | 图标文字 |
|------|--------|---------|---------|
| sm | `p-3` | `w-8 h-8` | `text-sm` |
| md | `p-4` | `w-10 h-10` | `text-base` |
| lg | `p-5` | `w-12 h-12` | `text-lg` |

### 事件触发

| 事件 | Alpine dispatch | 说明 |
|------|----------------|------|
| 点击卡片 | `tool-selected` (可选), 或导航 | selectable 模式下触发选择事件 |
| 操作按钮 | `tool-open`, `tool-health`, `tool-settings` | 三个操作按钮 |

### 卡片结构 (`ToolCardTemplate`, `ToolCard.js:123-182`)

```
┌─────────────────────────────────────────┐
│ [图标] [工具名]              [状态徽章]  │
│       [内部名]                          │
│                                         │
│ [描述文本 - 2行截断]                     │
│ ─────────────────────────────────────── │
│ [N 能力] [版本号]    [打开][心跳][设置]  │
└─────────────────────────────────────────┘
```

---

## 3. StatusBadge 组件

**源文件**: `apps/controller/app/web/static/js/components/StatusBadge.js`

### StatusBadge 参数

```javascript
AIDP.components.StatusBadge({
    status: 'healthy',      // 'healthy'|'registered'|'unhealthy'|'unreachable'|'disabled'|'loading'|'unknown'
    size: 'md',             // 'sm' | 'md' | 'lg'
    showDot: true,          // 显示圆点
    showText: true,         // 显示文字
    text: null,             // 自定义文字（覆盖默认）
})
```

### 状态配置表 (`StatusBadge.js:27-78`)

| 状态 | 颜色 | 背景 | 文字色 | 圆点色 | 标签 | 动画 |
|------|------|------|--------|--------|------|------|
| `healthy` | green | `bg-green-500/20` | `text-green-400` | `bg-green-500` | 健康 | - |
| `registered` | yellow | `bg-yellow-500/20` | `text-yellow-400` | `bg-yellow-500` | 已注册 | - |
| `unhealthy` | red | `bg-red-500/20` | `text-red-400` | `bg-red-500` | 异常 | - |
| `unreachable` | gray | `bg-gray-500/20` | `text-gray-400` | `bg-gray-500` | 不可达 | - |
| `disabled` | gray | `bg-gray-600/20` | `text-gray-500` | `bg-gray-600` | 已禁用 | - |
| `loading` | blue | `bg-blue-500/20` | `text-blue-400` | `bg-blue-500` | 加载中 | `animate-pulse` |
| `unknown` | gray | `bg-gray-500/20` | `text-gray-400` | `bg-gray-500` | 未知 | - |

### 尺寸映射

| 尺寸 | 内边距 | 字号 | 圆点大小 |
|------|--------|------|---------|
| sm | `px-1.5 py-0.5` | `text-xs` | `w-1.5 h-1.5` |
| md | `px-2 py-1` | `text-sm` | `w-2 h-2` |
| lg | `px-3 py-1.5` | `text-base` | `w-2.5 h-2.5` |

### StatusDot 简化版 (`StatusBadge.js:137-160`)

只渲染圆点，不显示文字标签。额外支持 `pulse` 参数。

### 模板结构 (`StatusBadgeTemplate`, `StatusBadge.js:125-132`)

```
[可选的圆点] [文字标签]
```

---

## 4. DataTable 组件

**源文件**: `apps/controller/app/web/static/js/components/DataTable.js`

### 配置参数

```javascript
AIDP.components.DataTable({
    data: [],               // 行数据数组
    columns: [],            // 列定义 [{key, title, sortable, formatter, template, cellClass}]
    
    // 排序
    sortColumn: null,       // 初始排序列
    sortDirection: 'asc',   // 'asc' | 'desc'
    
    // 分页
    pagination: true,       // 是否分页
    page: 1,                // 当前页
    pageSize: 10,           // 每页条数
    total: 0,               // 总条目数
    
    // 选择
    selectable: false,      // 是否可选
    selectedIds: Set,       // 内部使用
    
    // 搜索
    searchable: true,       // 是否显示搜索栏
    searchQuery: '',        // 搜索关键词
    
    // 行操作
    rowActions: [],         // [{name, icon, title, class}]
    
    // 回调
    onInit: fn,             // 初始化回调
    onRefresh: fn,          // 刷新回调
})
```

### 列定义字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `key` | string | 数据字段路径 (支持点号: `'user.name'`) |
| `title` | string | 列表头文字 |
| `sortable` | boolean | 是否可排序 |
| `formatter` | function | 值格式化函数 |
| `template` | function | 自定义模板渲染函数 (返回 HTML) |
| `cellClass` | string | 单元格 CSS class |

### 排序逻辑 (`DataTable.js:138-148`)

- 点击已排序的列切换方向 (asc ↔ desc)
- 点击新列重置为 asc
- 派发 `sort` 事件: `{column, direction}`

### 分页逻辑 (`DataTable.js:92-106`)

```javascript
// 计算属性
get paginatedData()   // 当前页数据: (page-1)*pageSize ~ page*pageSize
get totalPages()      // 总页数: Math.ceil(processedData.length / pageSize)
```

分页控件显示 "显示 1 - 10 条，共 N 条" + 首末页按钮 + 页码按钮。

### 事件派发

| 事件 | 数据 | 触发时机 |
|------|------|---------|
| `sort` | `{column, direction}` | 点击列头排序 |
| `page-change` | `{page}` | 切换页面 |
| `selection-change` | `{selected, row}` | 勾选/取消行 |
| `action` | `{action, row}` | 点击行操作按钮 |
| `row-click` | `{row}` | 点击行 |

### 表格状态

组件内置三种状态渲染：

1. **加载中**: 转圈动画 + "加载中..."
2. **错误**: 感叹号图标 + 错误消息
3. **空**: 收件箱图标 + "暂无数据"

### 模板结构 (`DataTableTemplate`, `DataTable.js:268-417`)

```
┌──────────────────────────────────────────┐
│ [搜索栏 (可选)]    [自定义工具栏 (插槽)]   │
├──────────────────────────────────────────┤
│ ┌ [全选] ┬ [列1 ▲] ┬ [列2] ┬ [操作] ─┐  │
│ ├ [选]   ┤ [值1]   ┤ [值2] ┤ [⚙️ ✏️] ┤ │
│ ├ [选]   ┤ [值1]   ┤ [值2] ┤ [⚙️ ✏️] ┤ │
│ └────────┴─────────┴───────┴──────────┘  │
├──────────────────────────────────────────┤
│ 显示 1-10 条，共 N 条    [<] [1] [2] [>] │
└──────────────────────────────────────────┘
```

---

## 5. 模板中的内联组件

AIDP Web UI 大量使用**内联 Alpine.js 函数**，直接在模板文件末尾以 `<script>` 标签定义：

### 示例：沙箱页面 (`modules/sandbox/index.html:88-115`)

```javascript
window.sandboxPage = function() {
    return {
        code: 'print("Hello, World!")',
        language: 'python',
        stdin: '',
        running: false,
        showStdin: false,
        result: {},
        showHistory: false,
        history: [],
        showDetail: false,
        detailItem: {},
        async init() {},
        async execute() { /* fetch /api/sandbox/execute */ },
        async viewDetail(item) { /* fetch /api/sandbox/history */ },
        formatDate(d) { /* locale format */ }
    }
};
```

### 示例：质量检查页面 (`modules/quality/index.html:69-94`)

```javascript
window.qualityPage = function() {
    return {
        code: '',
        filename: '',
        checking: false,
        result: {},
        showHistory: false,
        history: [],
        async init() {},
        async runCheck() { /* fetch /api/quality/check */ },
        async viewDetail(item) {},
        formatDate(d) { /* locale format */ }
    }
};
```

### 公共 UI 组件 (模板内定义)

在 `workspace.html` 的 Alpine 初始化中预定义了全局组件状态变量 (`workspace.html:13-100`):

| 类别 | 全局变量 | 默认值 |
|------|---------|--------|
| 模态框 | `showDetailModal`, `showCreateModal`, `showEditModal`, `showUploadModal`, `showDeleteModal`, `showImportModal`, `showTemplateModal`, `showGroupModal`, `showPreview` | `false` |
| 表单 | `showCreate`, `showDetail`, `showRegister`, `showWebImport`, `showStdin`, `showHistory` | `false` |
| 状态 | `loading`, `running`, `creating`, `searching`, `checking`, `importing`, `analyzing` | `false` |
| 数据对象 | `detail`, `form`, `groupForm`, `deleteTarget`, `result`, `importPreview`, `importAnalysis` | `{}` |
| 字符串 | `detailTab`, `searchQuery`, `filterCategory`, etc. | `''` |
| 数组 | `groups`, `toasts`, `knowledgeBases`, `documents`, `memories`, `skills`, `rules`, `agents`, `workflows`, `assets`, `projects`, `templates`, `executions`, etc. | `[]` |
| 数值 | `skip=0`, `limit=20` | - |
| 其他 | `stats`, `execConfigStr` | `{}` |

### 通知/Toast 系统 (`aidp.js:136-168`)

由 `AIDP.layoutData()` 函数管理:

```javascript
showNotification(data) {
    const notification = {
        id: Date.now(),
        message: data.message,
        type: data.type || 'info',    // 'info' | 'success' | 'warning' | 'error'
        duration: data.duration || 3000
    };
    this.notifications.push(notification);
    setTimeout(() => this.removeNotification(id), notification.duration);
}
```

通知类型对应颜色:
- `info` → `bg-blue-500`
- `success` → `bg-green-500`
- `warning` → `bg-yellow-500`
- `error` → `bg-red-500`

---

## 6. 组件使用规范

### JS 组件 (注册为 Alpine data)

```html
<!-- ToolCard -->
<div x-data="toolCard({ tool: myTool, size: 'md' })"
     x-html="AIDP.components.ToolCardTemplate">
</div>

<!-- StatusBadge -->
<div x-data="statusBadge({ status: 'healthy', size: 'sm' })"
     x-html="AIDP.components.StatusBadgeTemplate">
</div>

<!-- DataTable -->
<div x-data="dataTable({ 
    columns: myCols, 
    data: myData, 
    onRefresh: async () => await fetchData() 
})"
     x-html="AIDP.components.DataTableTemplate">
</div>
```

### 内联模板组件

```html
<!-- 在 Jinja2 模板中 -->
<div x-data="sandboxPage()" x-init="init()">
    <textarea x-model="code" ...></textarea>
    <button @click="execute()" :disabled="running">
        <span x-show="!running">▶ 执行</span>
        <span x-show="running">执行中...</span>
    </button>
    <pre x-show="result?.stdout" x-text="result?.stdout"></pre>
</div>
```

### 通知调用

```javascript
// 从 Service 层
events.notify('Tool registered successfully', 'success');

// 从 Alpine 组件
this.$dispatch('notification:show', { 
    message: '操作成功', 
    type: 'success', 
    duration: 3000 
});

// 错误通知 (自动设为 error + 5s)
events.error('Failed to load tools', error);
```