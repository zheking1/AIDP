# AIDP Frontend — 前端架构文档

## 1. 技术选型

| 技术 | 版本 | 用途 | 加载方式 |
|------|------|------|---------|
| Alpine.js | 3.x | 轻量响应式前端框架 | CDN (`cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js`) |
| Tailwind CSS | v4 | 工具类优先的 CSS 框架 | CDN (`@tailwindcss/browser@4`) |
| Font Awesome | 6.4.0 | 图标库 | CDN (`font-awesome/6.4.0/css/all.min.css`) |
| Jinja2 | — | 服务端模板引擎 | Python 包，FastAPI 集成 |
| Playwright | — | E2E 浏览器自动化测试 | npm 包 |

所有前端依赖均通过 CDN 加载，无需本地构建工具链。Tailwind CSS v4 使用 `@tailwindcss/browser` 运行时版本，在浏览器端动态解析 `class` 属性并生成对应样式。Alpine.js 使用 `defer` 属性延迟加载，确保 DOM 解析完成后才初始化。

## 2. 模板渲染机制

### Jinja2 环境配置

Jinja2 模板引擎在 `apps/controller/app/web/routes.py:13-17` 中初始化：

```python
from jinja2 import Environment, FileSystemLoader

templates_dir = Path(__file__).parent / "templates"
jinja_env = Environment(
    loader=FileSystemLoader(str(templates_dir)),
    auto_reload=True,
    cache_size=0  # 开发模式不缓存
)
```

关键配置说明：
- `auto_reload=True`：模板文件修改后自动重新加载，无需重启服务器
- `cache_size=0`：禁止模板缓存，确保每次请求都从磁盘读取最新模板（仅开发环境）

### render_template() 函数

`render_template()` 函数（`routes.py:27-47`）是服务端渲染的核心入口，支持三种渲染模式：

```python
def render_template(request: Request, template_name: str, context: dict = None):
    if context is None:
        context = {}
    context["request"] = request
    context["embed"] = request.query_params.get("embed", False)
    context["partial"] = request.query_params.get("partial", False)

    # partial 模式：自动切换到 _content 模板
    if context["partial"]:
        content_tpl = template_name.rsplit(".", 1)[0] + "_content.html"
        try:
            template = get_template(content_tpl)
            html = template.render(context)
            return HTMLResponse(content=html)
        except Exception:
            pass  # 没有 _content 模板时回退到原模板

    template = get_template(template_name)
    html = template.render(context)
    return HTMLResponse(content=html)
```

三种渲染模式：

| 模式 | 触发条件 | 行为 |
|------|---------|------|
| **默认（完整页面）** | 无 `partial` 或 `embed` 参数 | 渲染完整 HTML 模板，包含 `<html><head><body>` 等结构 |
| **Partial 模式** | `?partial=1` | 自动查找 `xxx_content.html`，只返回 Alpine 组件片段 |
| **Embed 模式** | `?embed=1` | 使用 `layouts/embed.html` 布局，主要用于 iframe 嵌入 |

Partial 模式的工作原理：
1. 从 `template_name` 推断 `_content` 模板路径（例如 `admin/users.html` → `admin/users_content.html`）
2. 尝试加载 `_content` 模板；如果文件不存在则静默回退到原模板
3. 返回的 HTML 不含完整页面结构，只有 Alpine.js 组件片段

## 3. Workspace 工作台架构

Workspace 工作台（`layouts/workspace.html`）是 AIDP 主界面的核心布局，采用标签页（Tab）架构将多个页面整合在一个 SPA-like 的界面中。

### 整体结构

```html
<body x-data="workspace()" x-init="init()">
    <!-- Sidebar: 256px 固定宽度 -->
    <aside class="w-64 bg-gray-800 border-r border-gray-700 ...">
        ...
    </aside>

    <!-- Main Content Area -->
    <main class="flex-1 flex flex-col min-w-0">
        <!-- Tab Bar: 40px 高度 -->
        <div class="h-10 bg-gray-800 border-b border-gray-700 ...">
            ...
        </div>
        <!-- Tab Content -->
        <div class="flex-1 ...">
            <template x-for="tab in tabs" :key="tab.id">
                <div :id="'tab-content-' + tab.id"
                     x-show="activeTab === tab.id"
                     class="mx-auto max-w-7xl min-w-[480px] w-full h-full overflow-auto px-6">
                </div>
            </template>
        </div>
    </main>
</body>
```

### Workspace 组件属性

`workspace()` 函数（`workspace.html:385-520`）定义在页面底部的 `<script>` 标签中，返回 Alpine.js 组件对象，包含以下属性：

#### Tab 管理
| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `tabs` | Array | `[]` | 已打开的标签页数组，每项含 `{id, name, icon, url, html}` |
| `activeTab` | String | `null` | 当前激活的标签页 ID |
| `loading` | Boolean | `false` | 加载中状态标识 |

#### 动态菜单
| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `menu` | Object | `{sidebar:[], header:[], user:[]}` | 从 API 获取的菜单数据 |
| `menuLoaded` | Boolean | `false` | 菜单是否已加载完成 |
| `menuError` | Boolean | `false` | 菜单加载是否失败 |

#### 项目切换器
| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `projects` | Array | `[]` | 当前用户可访问的项目列表 |
| `currentProjectId` | String | `''` | 当前选中的项目 ID |
| `currentProjectName` | String | `''` | 当前选中的项目名称 |
| `projectSwitcher` | Object | `{enabled: true, show_create: true, create_label: '创建新项目'}` | 项目切换器配置 |

## 4. 页面加载流程

`openTab()` 方法（`workspace.html:519-621`）是页面加载的核心函数，实现了完整的 Partial 内容获取与 Alpine 组件初始化流程：

### 完整流程图

```
openTab(id, name, icon, url)
  │
  ├─ 1. URL 处理：替换 {project_id} 占位符
  │
  ├─ 2. 追加 partial=1 参数：
  │      url + "?" + "partial=1"
  │
  ├─ 3. 检查 Tab 是否已存在：
  │      存在 → 切换到该 Tab，更新 url，直接返回
  │      不存在 → 创建新 Tab，push 到 tabs[]
  │
  ├─ 4. fetch(fetchUrl) 获取 HTML
  │
  ├─ 5. 提取 <script> 标签：
  │      html.replace(/<script>([\s\S]*?)<\/script>/g, fn)
  │      → 将脚本代码存入 scripts[] 数组
  │      → 从 HTML 中移除 <script> 标签
  │
  ├─ 6. 替换 x-data 属性：
  │      html.replace(/\sx-data="(\w+)\(\)"/g, ' data-alpine-component="$1"')
  │      → 防止 Alpine 在 DOM 插入时自动初始化
  │
  ├─ 7. 创建临时 div，设置 innerHTML = html
  │
  ├─ 8. 动态注入 <script> 标签：
  │      scripts.forEach(code => {
  │        var s = document.createElement('script');
  │        s.textContent = code;
  │        document.body.appendChild(s);
  │        document.body.removeChild(s);
  │      })
  │      → 执行组件函数定义（注册到 window）
  │
  ├─ 9. 恢复 x-data 属性：
  │      找到 [data-alpine-component]
  │      移除 data-alpine-component
  │      设置 x-data="funcName()"
  │
  ├─ 10. replaceChildren() 批量插入 DOM
  │
  └─ 11. Alpine.initTree(compEl) 初始化组件
```

### 核心代码

```javascript
async openTab(id, name, icon, url) {
    // 替换 project_id 占位符
    if (this.currentProjectId && url.includes('{project_id}')) {
        url = url.replace(/\{project_id\}/g, this.currentProjectId);
    }

    // 用 partial 模式获取纯内容
    const fetchUrl = url + (url.includes('?') ? '&' : '?') + 'partial=1';

    // 检查是否已存在（tab.html 缓存则直接切换）
    let tab = this.tabs.find(t => t.id === id);
    if (tab && tab.html) {
        tab.url = url;
        this.activeTab = id;
        return;
    }

    if (!tab) {
        tab = { id, name, icon, url, html: '' };
        this.tabs.push(tab);
    } else {
        tab.url = url;
        if (tab.html) return;
    }
    this.activeTab = id;
    this.loading = true;

    try {
        const resp = await fetch(fetchUrl);
        if (resp.ok) {
            let html = await resp.text();
            const scripts = [];
            // 提取 <script> 代码
            html = html.replace(/<script>([\s\S]*?)<\/script>/g,
                function(match, code) { scripts.push(code); return ''; });
            // 防止 Alpine 自动初始化
            html = html.replace(/\sx-data="(\w+)\(\)"/g,
                ' data-alpine-component="$1"');
            tab.html = html;
            var el = document.getElementById('tab-content-' + id);
            if (el) {
                var tmp = document.createElement('div');
                tmp.innerHTML = html;
                // 动态注入脚本：function 声明注册到 window，其余直接 eval
                scripts.forEach(function(code) {
                    var trimmed = code.trim();
                    if (trimmed.startsWith('function ')) {
                        var match = trimmed.match(/^function\s+(\w+)/);
                        if (match) {
                            try {
                                eval('window.' + match[1] + ' = ' + trimmed);
                            } catch(e) {
                                console.warn('Script eval failed:', e.message);
                            }
                            return;
                        }
                    }
                    try { eval(code); } catch(e) {
                        console.warn('Script eval2 failed:', e.message);
                    }
                });
                // 恢复 x-data 属性
                var compEl = tmp.querySelector('[data-alpine-component]');
                if (compEl && window.Alpine) {
                    var funcName = compEl.getAttribute('data-alpine-component');
                    compEl.removeAttribute('data-alpine-component');
                    compEl.setAttribute('x-data', funcName + '()');
                }
                // JS 布局注入：给第一个子 DIV 添加页头样式
                if (compEl) {
                    var children = compEl.children;
                    for (var ci = 0; ci < children.length; ci++) {
                        if (children[ci].tagName === 'DIV') {
                            children[ci].classList.add('flex', 'items-center', 'justify-between', 'pt-5', 'pb-4');
                            children[ci].style.borderBottom = '1px solid rgba(107, 114, 128, 0.5)';
                            break;
                        }
                    }
                }
                el.replaceChildren(...tmp.childNodes);
                if (compEl && window.Alpine) {
                    Alpine.initTree(compEl);
                }
            }
        } else {
            tab.html = '<div class="flex items-center justify-center h-full text-red-400 bg-gray-900"><p>加载失败: ' + resp.status + '</p></div>';
        }
    } catch(e) {
        tab.html = '<div class="flex items-center justify-center h-full text-red-400 bg-gray-900"><p>请求失败: ' + e.message + '</p></div>';
    }
    this.loading = false;
    this.saveState();
}
```

### 关键设计决策

1. **<script> 提取与 eval 注入**：直接 `innerHTML` 赋值时，`<script>` 标签不会自动执行。因此需要先提取所有 `<script>` 代码，用 `eval()` 手动执行。对于 `function` 声明，注册到 `window` 对象上（如 `window.knowledgeBasesPage = function() {...}`），确保后续 Alpine 组件初始化可以访问。

2. **tab.html 缓存**：首次加载后，`tab.html` 保存了渲染后的 HTML。再次切换到该 Tab 时，直接使用缓存内容，无需重新 fetch。`saveState()` 持久化到 localStorage。

3. **JS 布局注入**：`openTab()` 在 DOM 插入前，通过 JavaScript 给第一个子 DIV 添加 `flex items-center justify-between pt-5 pb-4` 类名和 `border-bottom` 样式，避免纯 CSS 选择器的闪烁问题。

4. **data-alpine-component 中转**：直接插入包含 `x-data="func()"` 的 HTML 会导致 Alpine 自动尝试初始化，而此时 `func` 尚未定义（脚本还没执行）。通过临时替换为 `data-alpine-component` 属性，待脚本执行完毕后再恢复，确保组件函数已可用。

3. **Alpine.initTree()**：`replaceChildren()` 替换 DOM 后，Alpine 不会自动感知新节点。需要手动调用 `Alpine.initTree()` 递归初始化新插入的组件树。注意：`initTree()` 必须在 `replaceChildren()` 之后调用，否则会操作旧 DOM。

4. **JS 布局注入**：在 `replaceChildren()` 之前，通过 JavaScript 给第一个子 DIV 添加 Tailwind 类名和内联样式，避免纯 CSS 选择器的闪烁问题。这比 CSS 选择器方式更可靠，因为 CSS 选择器无法添加 flex 布局类名。

## 5. Partial 内容加载

### _content.html 约定

Partial 模式是 AIDP 前端最核心的架构约定。每个功能页面由两个模板文件组成：

- `xxx.html`：完整页面（含 `<html><head><body>`），用于独立访问
- `xxx_content.html`：内容片段（只有 Alpine 组件），用于 Workspace 标签页加载

### _content.html 结构规范

`_content.html` 文件应遵循以下结构：

```html
<div x-data="xxxPage()" x-init="init()">
    <!-- 1. 页头区域（自动获得 pt-5 pb-4 border-b 样式） -->
    <div class="flex items-center justify-between">
        <div>
            <h1>页面标题</h1>
            <p>页面描述</p>
        </div>
        <div class="flex gap-2">
            <button @click="...">操作按钮</button>
        </div>
    </div>

    <!-- 2. 页面主体（自动获得 pt-5 样式） -->
    <div>
        <!-- 内容区域 -->
    </div>

    <!-- 3. 模态框等浮动元素 -->
    <div x-show="showModal" class="fixed inset-0 z-50 ...">
        ...
    </div>
</div>

<script>
window.xxxPage = function() {
    return {
        // 组件状态
        items: [],
        loading: false,
        showModal: false,

        async init() {
            await this.loadData();
        },

        async loadData() { ... },
        createItem() { ... },
        deleteItem(id) { ... }
    }
};
</script>
```

### 真实示例（`modules/knowledge/bases_content.html`）

```html
<div x-data="knowledgeBasesPage()" x-init="init()">
    <div class="flex items-center justify-between">
        <div class="flex items-center justify-between">
            <div>
                <h1 class="text-xl font-bold text-white tracking-tight">知识库</h1>
                <p class="text-sm text-gray-400 mt-0.5">管理文档和知识资源</p>
            </div>
            <button @click="showCreateModal = true"
                    class="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 ...">
                创建知识库
            </button>
        </div>
    </div>

    <!-- 统计卡片 -->
    <div class="pt-5 pb-3">
        <div class="grid grid-cols-4 gap-4">
            ...
        </div>
    </div>

    <!-- 列表 -->
    <div class="pb-6 flex-1">
        ...
    </div>
</div>

<script>
window.knowledgeBasesPage = function() {
    return {
        knowledgeBases: [],
        searchQuery: '',
        showCreateModal: false,
        loading: false,
        stats: {},
        newKB: { name: '', description: '', chunking_strategy: 'fixed', chunk_size: 500 },

        async init() {
            await Promise.all([this.loadKnowledgeBases(), this.loadStats()]);
        },

        async loadKnowledgeBases() {
            this.loading = true;
            try {
                var p = new URLSearchParams();
                if (this.searchQuery) p.set('search', this.searchQuery);
                var r = await fetch('/api/knowledge/bases?' + p);
                if (r.ok) {
                    var d = await r.json();
                    this.knowledgeBases = d.items || [];
                }
            } finally { this.loading = false; }
        },

        async createKnowledgeBase() {
            var r = await fetch('/api/knowledge/bases', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.newKB)
            });
            if (r.ok) {
                this.showCreateModal = false;
                this.newKB = { name: '', description: '', chunking_strategy: 'fixed', chunk_size: 500 };
                await this.loadKnowledgeBases();
                await this.loadStats();
            }
        }
    };
};
</script>
```

### 设计原则

- **页面只保留功能类**：`_content.html` 只包含业务逻辑和 UI 结构，所有布局相关的 CSS 由 Workspace 自动注入
- **无页面框架**：`_content.html` 不含 `<html><head><body>`，只包含 Alpine.js 组件及其定义脚本
- **组件函数注册到 window**：`window.knowledgeBasesPage = function() { ... }`，确保 openTab() 中可以访问

## 6. 布局系统

### CSS 自动注入机制

Workspace 通过两种方式为所有加载的 Tab 内容页面添加统一的间距和分隔线：

**方式一：JS 布局注入（`openTab()` 中，推荐）**

在 DOM 插入前，`openTab()` 通过 JavaScript 给第一个子 DIV 添加 Tailwind 类名和内联样式：

```javascript
// 给第一个子 DIV 添加页头样式
if (compEl) {
    var children = compEl.children;
    for (var ci = 0; ci < children.length; ci++) {
        if (children[ci].tagName === 'DIV') {
            children[ci].classList.add('flex', 'items-center', 'justify-between', 'pt-5', 'pb-4');
            children[ci].style.borderBottom = '1px solid rgba(107, 114, 128, 0.5)';
            break;
        }
    }
}
```

**方式二：CSS 选择器（`workspace.html:143-148`，兼容）**

```css
/* 第一个子元素：页头样式 */
[id^="tab-content-"] > * > div:first-of-type {
    padding-top: 1.25rem;      /* pt-5 */
    padding-bottom: 1rem;      /* pb-4 */
    border-bottom: 1px solid rgba(107, 114, 128, 0.5);
                                    /* border-b border-gray-500/50 */
}

/* 后续子元素：主体内容样式 */
[id^="tab-content-"] > * > div:not(:first-of-type) {
    padding-top: 1.25rem;      /* pt-5 */
}
```

### Tab 容器样式

Tab 容器使用 Tailwind 类名直接定义在 HTML 元素上（`workspace.html` 模板中）：

```html
<div :id="'tab-content-' + tab.id"
     x-show="activeTab === tab.id"
     class="flex-1 overflow-auto bg-gray-900 mx-auto max-w-7xl min-w-[480px] px-6">
</div>
```

| 类名 | 说明 |
|------|------|
| `flex-1` | 占满剩余高度 |
| `overflow-auto` | 内容溢出时滚动 |
| `bg-gray-900` | 深色背景 |
| `mx-auto` | 水平居中 |
| `max-w-7xl` | 最大宽度 80rem |
| `min-w-[480px]` | 最小宽度 480px |
| `px-6` | 左右内边距 1.5rem |

### 布局规则总结

| 元素 | 自动注入样式 | 注入方式 | 说明 |
|------|------------|---------|------|
| Tab 容器 | `mx-auto max-w-7xl min-w-[480px] px-6` | HTML 类名 | 居中、最小宽度、内边距 |
| 第一个 `div` | `flex items-center justify-between pt-5 pb-4` + `border-bottom` | JS 注入 | 页头：flex 布局 + 上边距 + 分隔线 |
| 后续 `div` | `pt-5` | CSS 选择器 | 主体：自动上边距 |
| 浮动元素（模态框） | 无影响 | — | 绝对/固定定位不受影响 |

### 新增页面的好处

开发者在创建新页面时完全不需要关注布局代码：
- 不需要写 `pt-5`、`border-b` 等重复性布局样式（`openTab()` 自动注入）
- 不需要设置容器宽度或居中（Tab 容器类名自动应用）
- 不需要写 `<html><head><body>` 框架（`_content.html` 只包含组件片段）
- 所有页面自动获得一致的视觉风格

## 7. Tab 管理

### Tab 切换机制

Workspace 使用 `x-show`（而非 `x-if`）来控制 Tab 内容的显示与隐藏：

```html
<template x-for="tab in tabs" :key="tab.id">
    <div :id="'tab-content-' + tab.id"
         x-show="activeTab === tab.id"
         class="...">
    </div>
</template>
```

使用 `x-show` 而非 `x-if` 的关键原因：
- **`x-show`**：只是 CSS `display: none`，DOM 节点保留，组件状态保持
- **`x-if`**：会销毁/重建 DOM，导致组件状态丢失（如输入框内容、滚动位置等）

### switchTab() 方法

```javascript
switchTab(id) {
    this.activeTab = id;
}
```

仅更改 `activeTab` 的值，通过 Alpine 的响应式系统自动切换显示。不会重新请求数据或重建组件。

### Tab 关闭

```javascript
closeTab(id) {
    const index = this.tabs.findIndex(t => t.id === id);
    if (index === -1) return;
    this.tabs.splice(index, 1);

    // 如果关闭的是当前活动标签，切换到其他标签
    if (this.activeTab === id && this.tabs.length > 0) {
        this.activeTab = this.tabs[Math.min(index, this.tabs.length - 1)].id;
    }
}
```

关闭行为：
- 从 `tabs` 数组中移除
- 如果关闭的是当前激活的 Tab，自动切换到相邻 Tab
- 当 `tabs.length === 1` 时，关闭按钮隐藏（至少保留一个 Tab）

## 8. 动态菜单

### MenuEngine 集成

Workspace 启动时通过 `loadMenu()` 方法从 API 获取动态菜单（`workspace.html:441-467`）：

```javascript
async loadMenu() {
    try {
        const params = this.currentProjectId ? `?project_id=${this.currentProjectId}` : '';
        const response = await fetch(`/api/menu${params}`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        this.menu.sidebar = data.sidebar || [];
        this.menu.header = data.header || [];
        this.menu.user = data.user || [];

        if (data.project_switcher) {
            this.projectSwitcher = { ...this.projectSwitcher, ...data.project_switcher };
        }

        this.menuLoaded = true;
        this.menuError = false;
    } catch (error) {
        console.error('Failed to load menu:', error);
        this.menuError = true;
        this.menuLoaded = false;
    }
}
```

### 菜单 API 返回结构

```json
{
    "sidebar": [
        {
            "group": "dashboard",
            "title": "总览",
            "icon": "fa-home",
            "is_hub": false,
            "items": [
                { "id": "dashboard", "label": "仪表盘", "icon": "fa-home", "route": "/dashboard-frame" }
            ]
        },
        {
            "group": "tools",
            "title": "工具",
            "icon": "fa-th-large",
            "is_hub": false,
            "items": [
                { "id": "tools", "label": "全部工具", "icon": "fa-th-large", "route": "/tools-frame" }
            ]
        },
        {
            "group": "knowledge",
            "title": "知识中心",
            "icon": "fa-book",
            "is_hub": true,
            "is_project_section": false,
            "description": "知识库、文档、搜索",
            "hub_route": "/hub/knowledge",
            "hub_items": [
                { "id": "knowledge-bases", "label": "知识库管理", "icon": "fa-book", "route": "/knowledge/bases" },
                { "id": "knowledge-documents", "label": "文档管理", "icon": "fa-file-alt", "route": "/knowledge/documents" },
                { "id": "knowledge-search", "label": "知识搜索", "icon": "fa-search", "route": "/knowledge/search" }
            ]
        }
    ],
    "header": [],
    "user": [],
    "project_switcher": {
        "enabled": true,
        "show_create": true,
        "create_label": "创建新项目"
    }
}
```

### 菜单类型

| 类型 | 说明 | 交互方式 |
|------|------|---------|
| **Hub** | 一级入口（`is_hub: true`），有子页面 | 点击后打开第一个 Hub 子页面 |
| **普通组** | 有 `items` 数组的菜单分组 | 点击 `item` 直接打开对应 Tab |
| **项目专区** | `is_project_section: true`，仅选中项目后显示 | 自动显示当前项目名称 |

### 菜单过滤

Menu Engine 在服务端根据用户角色进行过滤（`app/core/menu.py`）：
- `requires_role`：仅特定角色可见
- `requires_permission`：需要特定权限
- `is_project_section`：仅在已选择项目时显示

### 默认菜单（降级）

当 API 请求失败时（`menuError = true`），Workspace 使用硬编码的默认菜单（`workspace.html:281-330`），确保即使后端异常用户仍可正常导航。默认菜单包含：仪表盘、全部工具、知识库管理、知识搜索、用户管理（仅 admin 角色可见）。

## 9. 错误处理

### Console 警告过滤

Alpine.js 首次渲染时，如果模板中引用了尚未初始化的变量，会抛出 "is not defined" 警告。Workspace 通过以下代码过滤这些无害警告（`workspace.html:104-128`）：

```javascript
(function(){
    var ow = console.warn;
    console.warn = function(m) {
        if (typeof m === 'string' &&
            (m.includes('is not defined') || m.includes('Alpine Expression Error')))
            return;
        ow.apply(console, arguments);
    };

    var oe = window.onerror;
    window.onerror = function(msg, url, line) {
        if (msg && (msg.includes('is not defined') ||
            msg.includes('Alpine') || msg.includes('sidebarOpen')))
            return true;
        return oe ? oe.apply(this, arguments) : false;
    };
})();
```

过滤规则：

| 错误类型 | 是否过滤 | 原因 |
|---------|---------|------|
| `xxx is not defined` | 是 | Alpine 首次渲染时变量未就绪 |
| `Alpine Expression Error` | 是 | 组件函数尚未定义 |
| `sidebarOpen is not defined` | 是 | 侧边栏状态变量未初始化 |
| 其他错误 | 否 | 真实错误需要暴露 |

### Tab 加载错误处理

```javascript
// 服务器返回错误状态码
if (!resp.ok) {
    tab.html = '<div class="flex items-center justify-center h-full text-red-400 ...">
                <p>加载失败: ' + resp.status + '</p></div>';
}

// 网络请求异常
} catch(e) {
    tab.html = '<div class="flex items-center justify-center h-full text-red-400 ...">
                <p>请求失败: ' + e.message + '</p></div>';
}
```

### iframe 嵌入错误处理

对于 Tool Proxy 路由（`routes.py:611-615`），当后端工具不可用时返回 502：

```python
except httpx.RequestError as e:
    return HTMLResponse(
        content=f"<html><body style='background:#1f2937;color:#fff;padding:20px;'>
                 <h1>Tool Unavailable</h1>
                 <p>{tool_name} is not responding: {str(e)}</p></body></html>",
        status_code=502
    )
```

## 10. 模板文件清单

```
templates/
│
├── layouts/                          # 布局模板
│   ├── workspace.html                # 主工作台（Tab 架构，SPA-like）
│   ├── embed.html                    # 嵌入布局（iframe 使用，暗色主题守卫）
│   ├── base.html                     # 基础布局（旧版全页式导航）
│   └── unified_base.html             # 统一布局基类
│
├── pages/                            # 独立页面
│   ├── dashboard.html                # 仪表盘（旧版全页）
│   ├── dashboard-frame.html          # 仪表盘片段（iframe 嵌入用）
│   ├── tools.html                    # 工具列表（全页）
│   ├── tools-frame.html              # 工具列表片段
│   ├── tool_detail.html              # 工具详情
│   ├── projects_new.html             # 项目列表
│   ├── project_dashboard.html        # 项目仪表盘
│   ├── knowledge_hub.html            # 知识中心 Hub
│   ├── skills_hub.html               # 技能库 Hub
│   ├── memory_hub.html               # 记忆中心 Hub
│   └── project_settings/             # 项目设置子页面
│       ├── base.html                 # 设置页基类
│       ├── general.html              # 基本信息
│       ├── instructions.html         # AI 配置
│       ├── knowledge.html            # 知识库配置
│       ├── members.html              # 成员管理
│       └── integrations.html         # 集成配置
│
├── auth/                             # 认证页面
│   ├── login.html                    # 登录页
│   ├── profile.html                  # 个人资料（全页）
│   ├── profile-frame.html            # 个人资料片段
│   ├── api_keys.html                 # API Key 管理（全页）
│   └── api-keys-frame.html           # API Key 管理片段
│
├── admin/                            # 管理后台
│   ├── users.html                    # 用户管理（全页）
│   ├── users_content.html            # 用户管理片段 ★
│   ├── users-frame.html              # 用户管理 iframe 页
│   ├── users-frame_content.html      # 用户管理 iframe 片段 ★
│   ├── user_form.html                # 创建/编辑用户表单
│   ├── roles.html                    # 角色管理
│   ├── roles-frame.html              # 角色管理 iframe 页
│   ├── models.html                   # 模型管理
│   ├── models-frame.html             # 模型管理 iframe 页
│   ├── settings.html                 # 系统设置（全页）
│   ├── settings_content.html         # 系统设置片段 ★
│   ├── settings-frame.html           # 系统设置 iframe 页
│   ├── settings-frame_content.html   # 系统设置 iframe 片段 ★
│   ├── projects.html                 # 项目管理
│   ├── skills.html                   # 技能管理
│   ├── audit_logs.html               # 审计日志（全页）
│   ├── audit_logs_content.html       # 审计日志片段 ★
│   └── frame.html                    # 通用 iframe 基类
│
├── modules/                          # 模块页面（按模块分组）
│   ├── knowledge/
│   │   ├── bases.html                # 知识库列表（全页）
│   │   ├── bases_content.html        # 知识库列表片段 ★
│   │   ├── documents.html            # 文档管理（全页）
│   │   ├── documents_content.html    # 文档管理片段 ★
│   │   ├── search.html               # 知识搜索（全页）
│   │   ├── search_content.html       # 知识搜索片段 ★
│   │   └── templates.html / _content.html  # 文档模板
│   │
│   ├── memory/
│   │   ├── memories.html             # 记忆管理（全页）
│   │   ├── memories_content.html     # 记忆管理片段 ★
│   │   ├── graph.html                # 记忆图谱（全页）
│   │   └── graph_content.html        # 记忆图谱片段 ★
│   │
│   ├── skills/
│   │   ├── global.html / _content.html    # 全局技能
│   │   ├── personal.html / _content.html  # 个人技能
│   │   ├── personal_content_raw.html      # 个人技能原始模板
│   │   └── list.html                     # 技能列表
│   │
│   ├── rules/
│   │   ├── global.html / _content.html    # 全局规则
│   │   └── personal.html / _content.html  # 个人规则
│   │
│   ├── assets/
│   │   ├── list.html                 # 资产列表（全页）
│   │   └── list_content.html         # 资产列表片段 ★
│   │
│   ├── agents/
│   │   ├── list.html                 # Agent 列表（全页）
│   │   └── list_content.html         # Agent 列表片段 ★
│   │
│   ├── workflows/
│   │   ├── list.html                 # 流程列表（全页）
│   │   └── list_content.html         # 流程列表片段 ★
│   │
│   ├── sandbox/
│   │   ├── index.html                # 代码沙箱（全页）
│   │   └── index_content.html        # 代码沙箱片段 ★
│   │
│   └── quality/
│       ├── index.html                # 质量检查（全页）
│       └── index_content.html        # 质量检查片段 ★
│
└── 其他（旧版/独立页面）
    ├── logs.html                     # 日志
    ├── configs.html                  # 配置
    ├── onboarding.html               # 新手引导
    ├── audits.html                   # 审计（旧版）
    ├── reviews.html                  # 评审
    ├── projects.html                 # 项目（旧版）
    └── project_detail.html           # 项目详情（旧版）
```

标记 ★ 的为 Partial 模式 `_content.html` 文件，共约 18 个。

## 11. 性能注意事项

### CDN 加载策略

所有前端依赖通过 CDN 加载，首次访问时浏览器会缓存这些资源：

```html
<script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
```

加载顺序：
1. Tailwind CSS（同步，阻塞渲染）
2. Font Awesome（异步，不阻塞）
3. Alpine.js（`defer`，等待 DOM 解析完成后加载）

### 避免多 Alpine 实例

```html
<!-- 正确：workspace.html 中只加载一次 -->
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>

<!-- 错误：_content.html 中不要重复加载 Alpine -->
<script src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script> <!-- 禁止 -->
```

Partial 内容中禁止包含 Alpine.js CDN 加载脚本，否则会导致：
- 加载多个 Alpine 实例，相互冲突
- 内存泄漏
- 组件初始化异常

### Partial 内容缓存

当前 `openTab()` 每次切换时都会重新 fetch 内容。未来可以考虑：
- **已加载缓存**：同一 Tab 切换回来时，如果内容未过期则复用已缓存的 HTML
- **Swr 策略**：先显示缓存内容，后台静默刷新
- **预加载**：用户 hover 菜单项时提前 fetch

### CSS 注入覆盖问题

Tailwind CSS v4 的运行时模式会动态生成样式，可能导致 Workspace 自动注入的 CSS 被覆盖。`embed.html` 使用 MutationObserver 每隔 500ms 重新注入样式（`embed.html:80-84`）：

```javascript
setInterval(function(){
    var el = document.getElementById('aidp-unified');
    if (el) { el.parentNode.removeChild(el); document.head.appendChild(el); }
    else inject();
}, 500);
```

Workspace 中不存在此问题，因为 Tab 内容是 Workspace 容器的子元素，CSS 选择器的优先级足够高。

### 脚本执行性能

`openTab()` 中的脚本执行（`document.body.appendChild(s); document.body.removeChild(s);`）每次会同步执行脚本代码。对于组件函数注册来说开销很小，但如果页面包含大量内联脚本，可以考虑异步执行策略。

## 12. 如何新增一个页面

### 步骤 1: 在 routes.py 添加路由

在 `apps/controller/app/web/routes.py` 中添加 FastAPI 路由：

```python
@router.get("/my-new-page", response_class=HTMLResponse)
async def my_new_page(request: Request):
    """新功能页面"""
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login?next=/my-new-page", status_code=302)

    return render_template(request, "pages/my_new_page.html", {
        "current_user": user.to_dict(),
        "active_page": "my-new-page",
        "title": "新功能 - AIDP"
    })
```

### 步骤 2: 创建 HTML 模板

如果只需要全页访问，创建完整模板：

```html
{% extends "layouts/base.html" %}
{% block title %}新功能 - AIDP{% endblock %}
{% block content %}
<div x-data="myNewPage()" x-init="init()" class="p-6">
    <h1 class="text-2xl font-bold text-white">新功能页面</h1>
</div>
{% endblock %}
{% block extra_js %}
<script>
function myNewPage() {
    return {
        init() { console.log('My new page loaded'); }
    };
}
</script>
{% endblock %}
```

### 步骤 3: 创建 _content.html（Partial 模式）

如果需要在 Workspace 中以 Tab 形式加载，创建 `_content.html`：

```html
<div x-data="myNewPageContent()" x-init="init()">
    <div>
        <h1 class="text-xl font-bold text-white">新功能</h1>
        <p class="text-sm text-gray-400 mt-0.5">新功能描述</p>
    </div>

    <div>
        <!-- 页面内容 -->
    </div>
</div>

<script>
window.myNewPageContent = function() {
    return {
        loading: false,
        data: [],

        async init() {
            await this.loadData();
        },

        async loadData() {
            this.loading = true;
            try {
                var r = await fetch('/api/my-new-feature');
                if (r.ok) this.data = await r.json();
            } finally { this.loading = false; }
        }
    };
};
</script>
```

### 步骤 4: 添加菜单配置

在菜单配置文件（YAML）中添加对应条目：

```yaml
sidebar:
  - group: my-features
    title: 我的功能
    icon: fa-star
    is_hub: false
    requires_role: user
    items:
      - id: my-new-page
        label: 新功能页面
        icon: fa-star
        route: /my-new-page
```

### 步骤 5: 测试

1. 访问 `http://localhost:8000/my-new-page` → 全页模式
2. 访问 `http://localhost:8000/my-new-page?partial=1` → Partial 模式，应只返回片段
3. 在 Workspace 中通过菜单打开 → 应正确加载到 Tab 中
4. 检查控制台无 "is not defined" 等错误
5. Tab 切换、关闭行为正常
6. 如果设置了角色过滤，测试不同角色用户的可见性

### 完整 Checklist

| 检查项 | 说明 |
|--------|------|
| 路由注册 | `@router.get` 正确，`render_template` 调用正确 |
| 全页模板 | 继承 `layouts/base.html`，含完整页面结构 |
| Content 模板 | 仅含 `x-data` 组件 + `<script>`，无 `<html><head><body>` |
| Partial 模式 | `?partial=1` 返回纯片段，服务器自动找 `_content.html` |
| Alpine 组件函数 | 注册到 `window`，函数名与 `x-data` 一致 |
| 无 CDN 重复加载 | `_content.html` 中不含 Alpine/Tailwind CDN 脚本 |
| 布局正确 | 第一个 `div` 自动获得 `pt-5 pb-4 border-b` |
| 菜单配置 | YAML 菜单文件中添加了对应条目 |
| 错误处理 | Tab 加载失败时有友好的错误提示 |
| 角色/权限 | 如需角色过滤，路由和菜单都已正确配置 |

通过遵循以上步骤，开发人员可以在 10 分钟内完成一个新功能页面的创建，并且自动获得 Workspace 标签页、动态菜单、布局系统、错误处理等全部基础设施支持。