# Skills Module — 技能模块

## 1. 模块概述

技能模块（Skills Module）是 AIDP 平台的核心能力单元，提供**三级作用域**技能管理系统。每个技能代表一个可复用的 AI 能力（如代码审查、自动部署、安全扫描等），支持分组管理、文件附件、版本演化、导入导出。

**模块注册** (`apps/controller/app/modules/skills/__init__.py`):

```python
@register_module(name='skills', enabled=True)
class SkillsModule(BaseModule):
    name = "skills"
    description = "三层技能管理，支持全局/个人/项目技能"
    version = "1.0.0"
    enabled = True
    dependencies = []

    def register_routes(self, app):
        from .routes import router as skills_router
        app.include_router(skills_router, prefix="/api/skills")
```

---

## 2. 数据模型

全部定义在 `apps/controller/app/modules/skills/models.py`，使用 SQLAlchemy ORM。

### Skill（技能）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `String(36)` | 主键，UUID |
| `name` | `String(200)` | 技能名称，NOT NULL |
| `description` | `Text` | 描述 |
| `scope` | `String(20)` | 作用域：`global` / `personal` / `project` |
| `instruction` | `Text` | AI 指令/提示词 |
| `content` | `Text` | 脚本/代码内容 |
| `tags` | `Text` | JSON 数组，如 `["python","deploy"]` |
| `version` | `Integer` | 版本号，默认 1 |
| `dependencies` | `Text` | JSON 数组，依赖列表 |
| `exec_config` | `Text` | JSON 对象，执行配置 |
| `embedding` | `Text` | 向量嵌入 |
| `embedding_model` | `String(128)` | 嵌入模型名 |
| `review_status` | `String(20)` | 审核状态：`approved` / `pending` |
| `allowed_roles` | `Text` | JSON 数组，允许的角色 |
| `sensitive` | `Boolean` | 是否敏感 |
| `weight_config` | `Text` | JSON 对象，权重配置 |
| `examples` | `Text` | JSON 数组，示例输入输出 |
| `source_url` | `String(500)` | 来源 URL |
| `source_type` | `String(50)` | 来源类型，默认 `manual` |
| `group_id` | `String(36)` | FK -> `aidp_skill_groups.id` |
| `user_id` | `String(100)` | 所有者用户 ID |
| `project_id` | `Integer` | FK -> `aidp_projects.id` |
| `extra_data` | `Text` | JSON 对象，扩展数据 |
| `access_count` | `Integer` | 访问计数 |
| `last_accessed_at` | `DateTime` | 最后访问时间 |
| `created_at` | `DateTime` | 创建时间 |
| `updated_at` | `DateTime` | 更新时间 |
| `deleted_at` | `DateTime` | 软删除时间 |

**关联**：
- `group` -> `SkillGroup`（多对一）
- `files` -> `SkillFile`（一对多，级联删除）
- `evolutions` -> `SkillEvolution`（一对多，级联删除）

`to_dict(include_content=False)` 方法控制是否返回 `instruction`、`content`、`exec_config` 等详细字段。

### SkillGroup（技能分组）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `String(36)` | 主键 |
| `name` | `String(100)` | 分组名称，NOT NULL |
| `description` | `Text` | 描述 |
| `scope` | `String(20)` | 作用域 |
| `parent_id` | `String(36)` | FK 自引用，支持树形结构 |
| `user_id` | `String(100)` | 所有者 |
| `project_id` | `Integer` | 项目 ID |
| `sort_order` | `Integer` | 排序序号 |
| `created_at` | `DateTime` | 创建时间 |
| `updated_at` | `DateTime` | 更新时间 |

**关联**：
- `children` -> `SkillGroup`（一对多，自引用，级联删除）
- `parent` -> `SkillGroup`
- `skills` -> `Skill`（一对多，级联删除）

### SkillFile（技能文件）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `String(36)` | 主键 |
| `skill_id` | `String(36)` | FK -> `aidp_skills.id`，CASCADE 删除 |
| `path` | `String(500)` | 文件路径 |
| `content` | `Text` | 文件内容 |
| `language` | `String(50)` | 编程语言 |
| `is_entry` | `Boolean` | 是否为入口文件 |
| `sort_order` | `Integer` | 排序 |
| `created_at` | `DateTime` | 创建时间 |
| `updated_at` | `DateTime` | 更新时间 |

**关联**：
- `skill` -> `Skill`

### SkillEvolution（技能版本演化）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `String(36)` | 主键 |
| `skill_id` | `String(36)` | FK -> `aidp_skills.id`，CASCADE 删除 |
| `old_version` | `Integer` | 旧版本号 |
| `old_content` | `Text` | 旧内容快照 |
| `new_content` | `Text` | 新内容，NOT NULL |
| `diff_summary` | `Text` | 变更摘要 |
| `trigger_reason` | `String(100)` | 触发原因，默认 `manual` |
| `status` | `String(20)` | 状态：`pending` 等 |
| `rollback_to` | `Integer` | 回滚目标版本 |
| `created_at` | `DateTime` | 创建时间 |

**关联**：
- `skill` -> `Skill`

---

## 3. API 端点

全部定义在 `apps/controller/app/modules/skills/routes.py`，前缀 `/api/skills`。

### 静态路由（必须定义在参数化路由之前）

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/skills/list` | 列表查询，支持 scope/group_id/search/tag 过滤 |
| `GET` | `/api/skills/stats` | 统计信息（总数、按 scope 分布） |
| `GET` | `/api/skills/groups/list` | 分组列表 |
| `POST` | `/api/skills/groups/create` | 创建分组 |
| `DELETE` | `/api/skills/groups/{group_id}` | 删除分组 |
| `POST` | `/api/skills/create` | 创建技能 |
| `POST` | `/api/skills/search` | 全文搜索（name + description） |

### 参数化路由

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/skills/{skill_id}` | 获取详情（增加访问计数） |
| `PUT` | `/api/skills/{skill_id}` | 更新技能 |
| `DELETE` | `/api/skills/{skill_id}` | 软删除技能 |
| `GET` | `/api/skills/{skill_id}/files` | 获取技能文件列表 |
| `POST` | `/api/skills/{skill_id}/files` | 保存文件（先删后插） |
| `POST` | `/api/skills/{skill_id}/move` | 移动技能到另一分组/作用域 |

### 作用域过滤器（`_scope_filter`）

```python
def _scope_filter(model, scope: str, user_id: str = None, project_id: int = None):
    if scope == "global":
        return model.scope == "global"
    elif scope == "personal":
        return and_(model.scope == "personal", model.user_id == user_id)
    elif scope == "project":
        return and_(model.scope == "project", model.project_id == project_id)
    return model.scope == scope
```

### 前端使用的额外路由（未在该 routes.py 中定义，可能在其他位置）

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/skills/import/preview` | 导入预览 |
| `POST` | `/api/skills/import` | 执行导入 |
| `GET` | `/api/skills/{skill_id}/package` | 下载技能包 |

---

## 4. 前端

### 全局技能界面 (`global_content.html`，251 行)

```html
<div x-data="globalSkillsPage()" x-init="init()">
```

**Alpine.js 函数**：`window.globalSkillsPage()` (217-251 行)

**数据**：
- `skills[]`, `groups[]`, `searchQuery`, `filterGroup`, `filterStatus`
- `stats`, `groupCount`, `detail`, `detailTab`

**方法**：
- `init()` — 并行加载 skills + groups + stats
- `loadSkills()` — `GET /api/skills/list?scope=global`
- `loadGroups()` — `GET /api/skills/groups/list?scope=global`
- `loadStats()` — `GET /api/skills/stats`
- `viewSkill(s)` — `GET /api/skills/{id}`

**UI 元素**：
- 统计卡片（总数、已审核、待审核、分组数）
- 左侧分组树（高亮当前选中、递归按钮）
- 搜索框（300ms debounce）+ 状态过滤
- 技能网格（3 列，显示图标、名称、状态徽章、版本、描述、标签、使用次数）
- 详情模态框（5 个标签页：基本信息 / 指令 / 脚本 / 文件 / 示例）

### 个人技能界面 (`personal_content.html`，274 行)

```html
<div x-data="personalSkillsPage()" x-init="init()">
```

**Alpine.js 函数**：`window.personalSkillsPage()` (186-273 行)

**额外功能**：
- 创建技能模态框（名称、描述、指令、脚本、标签、分组选择）
- 导入模态框（URL 输入、预览、确认导入）
- 分组管理模态框（列表展示、创建新分组、删除分组）
- 删除技能（确认对话框）

---

## 5. 三级作用域

`scope` 字段控制数据访问权限：

| 作用域 | scope 值 | 数据可见性 | 创建者 |
|--------|----------|-----------|--------|
| **全局** | `global` | 所有用户可见 | 管理员（user_id = None） |
| **个人** | `personal` | 仅创建者可见 | user_id = 当前用户 |
| **项目** | `project` | 项目成员可见 | 需要 project_id 参数 |

**权限检查示例**（`routes.py:80-87`）：

```python
def _scope_filter(model, scope, user_id=None, project_id=None):
    if scope == "global":
        return model.scope == "global"
    elif scope == "personal":
        return and_(model.scope == "personal", model.user_id == user_id)
    elif scope == "project":
        return and_(model.scope == "project", model.project_id == project_id)
```

创建技能时根据 scope 自动设置 user_id/project_id：

```python
user_id=user_id if data.scope != "global" else None,
project_id=project_id if data.scope == "project" else None
```

---

## 6. 导入导出

前端 `personal_content.html` 实现了完整的导入导出流程。

**导入流程**：
1. 用户在导入模态框输入 URL（支持 GitHub 仓库路径或 `.tar.gz` 包链接）
2. 点击「预览」调用 `POST /api/skills/import/preview`，返回技能名称/描述/标签
3. 确认后调用 `POST /api/skills/import`，传入 `url` + `scope`
4. 导入成功后刷新列表和统计

```javascript
async previewImport() {
    const r = await fetch('/api/skills/import/preview', {
        method: 'POST',
        body: JSON.stringify({ url: this.importUrl })
    })
    if (r.ok) this.importPreview = await r.json()
}

async doImport() {
    const r = await fetch('/api/skills/import', {
        method: 'POST',
        body: JSON.stringify({ url: this.importUrl, scope: 'personal' })
    })
}
```

**导出流程**：
- 详情模态框底部提供下载按钮：`<a :href="'/api/skills/'+detail?.id+'/package'" target="_blank">下载</a>`
- 将技能打包为可移植文件供分发

---

## 7. 演化追踪

SkillEvolution 模型记录技能的每一次变更历史：

```python
class SkillEvolution(Base):
    __tablename__ = "aidp_skill_evolutions"
    id = Column(String(36), primary_key=True)
    skill_id = Column(String(36), ForeignKey("aidp_skills.id", ondelete="CASCADE"))
    old_version = Column(Integer, nullable=True)
    old_content = Column(Text, nullable=True)    # 旧内容快照
    new_content = Column(Text, nullable=False)     # 新内容
    diff_summary = Column(Text, nullable=True)     # 变更摘要
    trigger_reason = Column(String(100), default="manual")  # 触发原因
    status = Column(String(20), default="pending")           # 演化状态
    rollback_to = Column(Integer, nullable=True)             # 回滚目标
```

**能力**：
- `old_content` / `new_content` — 支持内容对比和回滚
- `diff_summary` — 自动生成或手动填写的变更摘要
- `rollback_to` — 指定回滚到哪个版本
- `trigger_reason` — 记录是手动编辑、导入更新还是自动触发

Skill 模型通过 `evolutions` 关系与 SkillEvolution 关联（级联删除），每次更新技能时可自动创建演化记录，实现变更溯源。