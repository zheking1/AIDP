# AIDP Menu System — 菜单导航系统

## 1. 设计目标

AIDP 的菜单系统采用动态生成策略，核心设计目标包括：

- **动态渲染**：菜单从后端 API 获取，根据当前用户角色和权限过滤菜单项
- **Hub 机制**：一级菜单（如知识中心、技能库、记忆中心）点击后在内容区展开二级 Tab 导航
- **项目上下文**：项目专区的菜单项依赖当前选中的项目，路由中的 `{project_id}` 占位符自动替换
- **多区域**：支持侧边栏菜单、顶部导航、用户菜单和项目切换器四个区域
- **权限控制**：admin/super_admin 自动绕过所有权限检查

## 2. 菜单配置（menu.yaml v3.0）

菜单配置位于 `app/config/menu.yaml`，采用 YAML 格式定义。顶层结构：

```yaml
version: "3.0"
schema_version: "1.0"

header:        # 顶部导航栏
sidebar:       # 侧边栏（核心区域）
user_menu:     # 用户下拉菜单
project_switcher:  # 项目切换器配置
```

### 侧边栏分区

侧边栏按 `order` 排序，包含 6 个分区：

**1. 知识中心 (order: 10)** — Hub 类型
- hub_items: 知识库管理、文档管理、高级搜索、文档模板、代码资产
- 权限要求：knowledge:read / asset:read

**2. 技能库 (order: 20)** — Hub 类型
- hub_items: 全局技能、我的技能、全局规则、我的规则、Agent 管理、流程引擎
- 权限要求：skills:read:global / skills:read:personal

**3. 记忆中心 (order: 30)** — Hub 类型
- hub_items: 记忆列表、记忆图谱、记忆检索
- 权限要求：memory:read

**4. 开发工具 (order: 40)** — 直接打开
- items: 代码沙箱、质量检查
- 权限要求：sandbox:execute / quality:check

**5. 项目专区 (order: 90)** — 项目上下文
- requires_project: true, is_project_section: true
- 路由包含 `{project_id}` 占位符
- items: 项目仪表盘、项目知识、项目技能、项目规则、项目 Agent、项目流程、项目记忆、项目设置

**6. 系统管理 (order: 100)** — admin only
- requires_role: admin
- items: 用户管理、项目管理、全局技能、全局规则、审计日志、系统设置

### header 菜单定义

```yaml
header:
  - id: "notifications"
    label: "通知"
    icon: "bell"
    badge:
      type: "api"
      endpoint: "/api/notifications/unread-count"
      refresh_interval: 60
    route: "/notifications"
  - id: "help"
    label: "帮助"
    icon: "help-circle"
    href: "https://docs.aidp.io"
    target: "_blank"
  - id: "theme"
    label: "主题"
    icon: "moon"
    action: "toggle_theme"
```

### project_switcher 配置

```yaml
project_switcher:
  enabled: true
  show_recent: true
  recent_count: 5
  show_create: true
  create_label: "创建新项目"
```

## 3. MenuEngine 实现

`MenuEngine` 类（`menu.py:13-225`）是菜单生成引擎，核心方法如下：

### get_sidebar_menu(user, project_id)

侧边栏菜单生成流程：

1. 遍历 `menu.yaml` 中 `sidebar` 下的所有 group
2. **项目专区过滤**：`is_project_section=True` 的 group，如果没有 `project_id` 则跳过
3. **角色检查**：调用 `_has_role(user, requires_role)`，admin/super_admin 自动通过
4. **权限检查**：调用 `_has_permissions(user, permissions)`，admin/super_admin 自动通过
5. **Hub 处理**：`is_hub=True` 的 group，遍历其 `hub_items`，过滤权限后生成 hub 结构
6. **普通菜单**：遍历 `items`，过滤权限和角色，替换 `{project_id}` 占位符
7. **排序**：按 `order` 字段升序排列

```python
def get_sidebar_menu(self, user=None, project_id=None):
    menu = []
    for group in self.config.get('sidebar', []):
        if group.get('is_project_section') and not project_id:
            continue
        if group.get('requires_role') and not self._has_role(user, group['requires_role']):
            continue
        if group.get('is_hub'):
            hub_items = []
            for item in group.get('hub_items', []):
                if item.get('permissions') and not self._has_permissions(user, item['permissions']):
                    continue
                hub_items.append({'id': item['id'], 'label': item['label'], ...})
            if hub_items:
                menu.append({'is_hub': True, 'hub_items': hub_items, ...})
            continue
        # 普通菜单项处理...
    menu.sort(key=lambda x: x['order'])
    return menu
```

### get_header_menu(user)

顶部导航菜单生成，同样支持权限过滤：

```python
def get_header_menu(self, user=None):
    menu = []
    for item in self.config.get('header', []):
        if item.get('permissions') and not self._has_permissions(user, item['permissions']):
            continue
        menu.append({
            'id': item['id'], 'label': item['label'],
            'icon': item['icon'], 'route': item.get('route'),
            'href': item.get('href'), 'action': item.get('action'),
            'badge': item.get('badge')
        })
    return menu
```

### get_user_menu(user)

用户下拉菜单，支持分隔符：不涉及权限过滤（所有登录用户可见）。

### get_project_switcher_config()

返回项目切换器的配置信息（是否启用、是否显示最近项目、显示数量等）。

## 4. 角色与权限过滤

### _has_role 角色检查

```python
def _has_role(self, user, required_role):
    if not user:
        return False
    user_role = getattr(user, 'role', None)
    if user_role in ['admin', 'super_admin']:
        return True  # 管理员拥有所有角色
    return user_role == required_role
```

### _has_permissions 权限检查

```python
def _has_permissions(self, user, permissions):
    # 注意：当前为桩函数，始终返回 True
    # 实际权限检查应在各模块的 route 层实现
    return True
```

> **注意**：`_has_permissions()` 是一个桩函数（stub），始终返回 `True`。菜单过滤不依赖此函数，而是通过 `requires_permission` 和 `requires_project` 字段在渲染时动态判断。