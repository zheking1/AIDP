# Rules Module — 规则模块

## 1. 模块概述

规则模块（Rules Module）定义了 AI 必须遵守的约束和边界。采用**三级作用域**架构（global/personal/project），支持 6 大分类、5 级严重程度、分组管理和规则检查。

**模块注册** (`apps/controller/app/modules/rules/__init__.py`):

```python
@register_module(name='rules', enabled=True)
class RulesModule(BaseModule):
    name = "rules"
    description = "规则管理，三层架构：全局/个人/项目"
    version = "1.0.0"
    enabled = True
    dependencies = []

    def register_routes(self, app):
        from .routes import router as rules_router
        app.include_router(rules_router, prefix="/api/rules")
```

---

## 2. 数据模型

全部定义在 `apps/controller/app/modules/rules/models.py`。

### Rule（规则）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `String(36)` | 主键，UUID |
| `name` | `String(200)` | 规则名称，NOT NULL |
| `description` | `Text` | 规则描述 |
| `content` | `Text` | 规则内容（规则正文），NOT NULL |
| `category` | `String(50)` | 分类：`security` / `code_style` / `architecture` / `testing` / `deployment` / `business` |
| `severity` | `String(20)` | 严重级别：`critical` / `high` / `medium` / `low` / `info` |
| `scope` | `String(20)` | 作用域：`global` / `personal` / `project` |
| `pattern` | `Text` | 检测正则表达式（用于自动化检查） |
| `auto_fix` | `Text` | 自动修复方案 |
| `allowed_roles` | `Text` | JSON 数组，允许的角色 |
| `tags` | `Text` | JSON 数组，标签 |
| `embedding` | `Text` | 向量嵌入 |
| `embedding_model` | `String(128)` | 嵌入模型名 |
| `group_id` | `String(36)` | FK -> `aidp_rule_groups.id` |
| `user_id` | `String(100)` | 所有者 |
| `project_id` | `Integer` | FK -> `aidp_projects.id` |
| `is_active` | `Boolean` | 是否启用，默认 True |
| `access_count` | `Integer` | 访问计数 |
| `extra_data` | `Text` | JSON 扩展数据 |
| `created_at` | `DateTime` | 创建时间 |
| `updated_at` | `DateTime` | 更新时间 |
| `deleted_at` | `DateTime` | 软删除时间 |

`to_dict(include_content=False)` 方法仅在 `include_content=True` 时返回 `content` 字段。

### RuleGroup（规则分组）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `String(36)` | 主键 |
| `name` | `String(100)` | 分组名称，NOT NULL |
| `description` | `Text` | 描述 |
| `scope` | `String(20)` | 作用域 |
| `parent_id` | `String(36)` | FK 自引用（树形结构） |
| `user_id` | `String(100)` | 所有者 |
| `project_id` | `Integer` | 项目 ID |
| `sort_order` | `Integer` | 排序序号 |
| `created_at` | `DateTime` | 创建时间 |
| `updated_at` | `DateTime` | 更新时间 |

**关联**：
- `children` -> `RuleGroup`（自引用，级联删除）
- `parent` -> `RuleGroup`
- `rules` -> `Rule`（一对多，级联删除）

---

## 3. API 端点

全部定义在 `apps/controller/app/modules/rules/routes.py`，前缀 `/api/rules`。

### 静态路由

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/rules/list` | 规则列表，支持 category/severity/scope/group_id/search 过滤 |
| `POST` | `/api/rules/create` | 创建规则 |
| `POST` | `/api/rules/search` | 全文搜索规则 |
| `GET` | `/api/rules/groups/list` | 分组列表 |
| `POST` | `/api/rules/groups/create` | 创建分组 |
| `DELETE` | `/api/rules/groups/{group_id}` | 删除分组 |
| `GET` | `/api/rules/stats` | 统计信息（总数 + 按分类/级别分布） |

### 参数化路由

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/rules/{rule_id}` | 获取详情（增加访问计数） |
| `PUT` | `/api/rules/{rule_id}` | 更新规则 |
| `DELETE` | `/api/rules/{rule_id}` | 软删除规则 |

**列表接口过滤参数**：`scope`、`category`、`severity`、`project_id`、`group_id`、`search`、`skip`、`limit`。

**路由注册注意**：静态路由（`/list`、`/stats`、`/groups/list` 等）必须定义在参数化路由（`/{rule_id}`）之前，否则 FastAPI 会将静态路径错误地匹配为参数。

---

## 4. 前端

### 全局规则界面 (`global_content.html`，87 行)

```html
<div x-data="globalRulesPage()" x-init="init()">
```

**Alpine.js 函数**：`window.globalRulesPage()` (81-87 行)

```javascript
window.globalRulesPage = function globalRulesPage() {
    return {
        rules: [], filterCategory: '', filterSeverity: '',
        loading: false, showDetailModal: false, detail: null,
        async init() { this.loadRules() },
        async loadRules() {
            this.loading = true;
            try {
                const p = new URLSearchParams({ scope: 'global', limit: '100' });
                if (this.filterCategory) p.set('category', this.filterCategory);
                if (this.filterSeverity) p.set('severity', this.filterSeverity);
                const r = await fetch(`/api/rules/list?${p}`);
                if (r.ok) this.rules = (await r.json()).items || [];
            } finally { this.loading = false }
        },
        async viewRule(r) {
            const res = await fetch(`/api/rules/${r.id}`);
            if (res.ok) { this.detail = await res.json(); this.showDetailModal = true }
        }
    };
}
```

**UI 元素**：
- 分类下拉框（全部/安全/代码风格/架构/测试/部署/业务）
- 严重级别下拉框（全部/严重/高危/中等/低）
- 规则卡片网格 — 每个卡片显示分类图标（颜色区分）：
  - `security` → 红色盾牌 `fa-shield-alt`
  - `code_style` → 黄色代码 `fa-code`
  - `architecture` → 蓝色拓扑 `fa-sitemap`
  - `testing` → 绿色试管 `fa-vial`
  - `deployment` → 紫色火箭 `fa-rocket`
  - `business` → 灰色公文包 `fa-briefcase`
- 严重级别彩色徽章（红色/橙色/黄色/灰色）
- 详情模态框：规则内容、分类、级别、检测正则、自动修复

### 个人规则界面 (`personal_content.html`，127 行)

```html
<div x-data="personalRulesPage()" x-init="init()">
```

**Alpine.js 函数**：`window.personalRulesPage()` (115-127 行)

**额外功能**：
- 创建规则模态框（名称、规则内容、描述、分类、严重级别、检测正则、标签）
- 分组管理模态框（创建/删除分组）
- 删除规则（确认对话框）

---

## 5. 规则分类与严重级别

### 分类枚举（`category`）

定义在 `Rule.category` 字段（`models.py:57`），注释中列出全部可选值：

```python
category = Column(String(50), nullable=False, index=True, default="code_style")
# security / code_style / architecture / testing / deployment / business
```

| 值 | 中文名 | 图标 | 颜色 |
|------|--------|------|------|
| `security` | 安全 | `fa-shield-alt` | 红色 |
| `code_style` | 代码风格 | `fa-code` | 黄色 |
| `architecture` | 架构 | `fa-sitemap` | 蓝色 |
| `testing` | 测试 | `fa-vial` | 绿色 |
| `deployment` | 部署 | `fa-rocket` | 紫色 |
| `business` | 业务 | `fa-briefcase` | 灰色 |

前端分类选择器：

```html
<select x-model="filterCategory">
    <option value="">全部分类</option>
    <option value="security">安全</option>
    <option value="code_style">代码风格</option>
    <option value="architecture">架构</option>
    <option value="testing">测试</option>
    <option value="deployment">部署</option>
    <option value="business">业务</option>
</select>
```

### 严重级别枚举（`severity`）

定义在 `Rule.severity` 字段（`models.py:61`）：

```python
severity = Column(String(20), nullable=False, default="medium")
# critical / high / medium / low / info
```

| 值 | 中文名 | 徽章颜色 |
|------|--------|---------|
| `critical` | 严重 | 红色 `bg-red-900/50 text-red-300` |
| `high` | 高危 | 橙色 `bg-orange-900/50 text-orange-300` |
| `medium` | 中等 | 黄色 `bg-yellow-900/50 text-yellow-300` |
| `low` | 低 | 灰色 `bg-gray-700 text-gray-300` |
| `info` | 信息 | （未单独配色，默认灰色） |

---

## 6. 规则检查

规则模块支持通过 `pattern` 字段定义检测正则表达式，实现自动化的规则检查。

### `pattern` 字段

每条规则可以配置一个正则检测模式：

```python
pattern = Column(Text, nullable=True)
```

前端创建规则时提供输入：

```html
<input type="text" x-model="form.pattern"
    class="w-full bg-gray-700 border border-gray-600 rounded-lg ... font-mono"
    placeholder="eval\s*\(|exec\s*\(">
```

### 自动修复（`auto_fix`）

```python
auto_fix = Column(Text, nullable=True)
```

当规则被违反时，`auto_fix` 字段保存自动修复方案，例如：

```json
{
    "pattern": "console\\.log\\(",
    "auto_fix": "替换 console.log() 为 logger.info()",
    "content": "禁止使用 console.log 调试输出"
}
```

### 统计接口的检查支持

`GET /api/rules/stats` 返回按分类和按严重级别分布的数据：

```python
@router.get("/stats")
async def get_rules_stats(...):
    by_cat = await db.execute(
        select(Rule.category, func.count(Rule.id))
        .where(and_(Rule.deleted_at.is_(None), scope_c))
        .group_by(Rule.category)
    )
    by_sev = await db.execute(
        select(Rule.severity, func.count(Rule.id))
        .where(and_(Rule.deleted_at.is_(None), scope_c))
        .group_by(Rule.severity)
    )
    return {
        "total": total.scalar() or 0,
        "by_category": {row[0]: row[1] for row in by_cat.all()},
        "by_severity": {row[0]: row[1] for row in by_sev.all()}
    }
```

这使得前端可以展示规则的健康仪表盘，快速了解哪些分类的规则最多、哪些严重级别需要优先处理。

### 搜索检查

`POST /api/rules/search` 支持按关键字、分类、严重级别、作用域组合搜索，返回匹配规则的完整内容，供自动化流程使用：

```python
conditions = [
    Rule.deleted_at.is_(None), Rule.is_active == True,
    or_(Rule.name.ilike(p), Rule.description.ilike(p), Rule.content.ilike(p))
]
if query.category: conditions.append(Rule.category == query.category)
if query.severity: conditions.append(Rule.severity == query.severity)
if query.scope: conditions.append(_scope_filter(Rule, query.scope, ...))
```