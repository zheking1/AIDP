# AIDP Module System — 模块系统设计

## 1. 设计目标

AIDP 的模块系统是一个轻量级的可插拔架构，围绕以下四个核心目标设计：

- **可插拔**：每个模块可以独立启用/禁用，互不干扰。通过 `@register_module(name='xxx', enabled=True/False)` 装饰器控制。
- **依赖管理**：模块之间的依赖关系由框架自动解析。依赖声明在模块类的 `dependencies` 列表中，系统在初始化时通过拓扑排序保证依赖模块先初始化。
- **统一生命周期**：所有模块遵循相同的生命周期接口——`on_startup()` / `on_shutdown()`，由 `app_lifespan` 统一管理。
- **路由自动注册**：每个模块通过 `register_routes(app)` 将自己的 `APIRouter` 注册到 FastAPI 应用实例上，路由前缀统一为 `/api/{module_name}`。

## 2. BaseModule 抽象类

所有模块必须继承 `BaseModule` 并实现抽象方法。完整定义位于 `apps/controller/app/modules/__init__.py`：

```python
from typing import Dict, Type, List, Optional, Any
from fastapi import FastAPI, APIRouter
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class BaseModule(ABC):
    """
    模块基类 — 所有工具模块都需要继承此类
    """

    # 模块元数据
    name: str = ""            # 模块标识名，全局唯一
    description: str = ""     # 模块描述，用于 API 文档和界面展示
    version: str = "1.0.0"   # 模块版本号
    enabled: bool = True      # 是否启用（可在注册时指定）

    # 依赖的其他模块（模块名列表）
    dependencies: List[str] = []

    def __init__(self):
        self.router: Optional[APIRouter] = None
        self.app: Optional[FastAPI] = None

    @abstractmethod
    def register_routes(self, app: FastAPI):
        """
        注册 API 路由 — 必须实现
        子类应调用 app.include_router(router, prefix="/api/{name}")
        """
        pass

    def register_models(self):
        """注册数据库模型（可选）— 用于需要在运行时动态注册模型的场景"""
        pass

    def register_events(self):
        """注册事件处理器（可选）— 用于订阅/发布系统事件"""
        pass

    def on_startup(self):
        """模块启动时调用（可选）— 执行初始化逻辑，如连接池预热"""
        logger.info(f"Module {self.name} started")

    def on_shutdown(self):
        """模块关闭时调用（可选）— 执行清理逻辑，如关闭连接、释放资源"""
        logger.info(f"Module {self.name} stopped")

    def get_info(self) -> Dict[str, Any]:
        """获取模块元数据信息"""
        return {
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'enabled': self.enabled,
            'dependencies': self.dependencies
        }
```

### 各方法说明

| 方法 | 类型 | 说明 |
|------|------|------|
| `register_routes(app)` | **抽象必须实现** | 将模块的 `APIRouter` 注册到 FastAPI 主应用，指定路由前缀 |
| `register_models()` | 可选覆盖 | 注册 SQLAlchemy 模型（当前模块模型已在 `main.py` 中显式 import，此方法保留作为后备机制） |
| `register_events()` | 可选覆盖 | 注册事件监听器，用于模块间事件驱动通信 |
| `on_startup()` | 可选覆盖 | 预留接口，当前框架未调用（`init_all_modules()` 不调用此方法） |
| `on_shutdown()` | 可选覆盖 | 应用关闭时调用，用于释放资源、持久化状态等 |

## 3. 模块注册机制

模块通过 `@register_module` 装饰器注册到全局注册表 `_registered_modules`。

### 装饰器实现

```python
# 模块注册表（全局单例）
_registered_modules: Dict[str, Type[BaseModule]] = {}
_module_instances: Dict[str, BaseModule] = {}


def register_module(name: str, enabled: bool = True):
    """
    模块注册装饰器

    用法:
        @register_module(name='knowledge')
        class KnowledgeModule(BaseModule):
            ...

    Args:
        name: 模块名称（全局唯一标识）
        enabled: 是否默认启用
    """
    def decorator(cls: Type[BaseModule]):
        if not issubclass(cls, BaseModule):
            raise TypeError(f"Module {name} must inherit from BaseModule")

        cls.name = name
        cls.enabled = enabled
        _registered_modules[name] = cls
        logger.debug(f"Registered module: {name}")
        return cls
    return decorator
```

### 使用示例

```python
@register_module(name='knowledge', enabled=True)
class KnowledgeModule(BaseModule):
    name = "knowledge"
    description = "文档知识库管理，支持语义搜索和智能分块"
    version = "1.0.0"
    enabled = True
    dependencies = []  # 无依赖

    def register_routes(self, app):
        from .routes import router as knowledge_router
        app.include_router(knowledge_router, prefix="/api/knowledge")
```

### 注册时机

模块注册发生在 `main.py` 的 import 阶段。每个模块的 `__init__.py` 在导入时自动执行 `@register_module` 装饰器，将模块类写入 `_registered_modules`：

```python
# main.py 顶部 — 通过 import 触发模块注册
import app.modules.knowledge   # 触发 @register_module(name='knowledge')
import app.modules.agents      # 触发 @register_module(name='agents')
import app.modules.workflows   # 触发 @register_module(name='workflows')
```

## 4. 依赖解析

模块间可能存在依赖关系（如 `workflows` 依赖 `agents`），系统通过拓扑排序算法自动解析。

### 拓扑排序算法

```python
def init_all_modules(app: FastAPI, include: Optional[List[str]] = None) -> List[str]:
    """
    初始化所有模块 — 按依赖顺序拓扑排序
    """
    initialized = []
    modules_to_init = include if include else list(_registered_modules.keys())

    pending = set(modules_to_init)
    while pending:
        # 找出所有依赖已满足的模块
        ready = set()
        for name in pending:
            module_class = _registered_modules.get(name)
            if not module_class:
                continue

            # 检查依赖是否都已初始化
            deps_satisfied = all(
                dep in _module_instances or dep not in modules_to_init
                for dep in module_class.dependencies
            )

            if deps_satisfied:
                ready.add(name)

        if not ready:
            # 存在循环依赖 — 中断并报错
            logger.error(f"Circular dependency detected: {pending}")
            break

        # 初始化所有"就绪"的模块
        for name in ready:
            instance = init_module(name, app)
            if instance:
                initialized.append(name)
            pending.remove(name)

    logger.info(f"Initialized {len(initialized)} modules: {initialized}")
    return initialized
```

### 解析步骤

1. **收集候选模块** — 从注册表中获取待初始化的模块列表（默认全部）
2. **查找就绪模块** — 遍历 `pending` 集合，找到所有依赖已经初始化的模块
3. **初始化就绪模块** — 调用 `init_module()` 完成初始化
4. **循环检测** — 如果找不到就绪模块且 `pending` 非空，说明存在循环依赖或缺失依赖，报错退出
5. **重复 2-4** — 直到所有模块初始化完成

### 当前模块依赖关系

```
knowledge (无依赖)
memory (无依赖)
skills (无依赖)
assets (无依赖)
sandbox (无依赖)
quality (无依赖)
rules (无依赖)
agents (无依赖)
workflows → agents（依赖 agents 模块）
```

初始化顺序：knowledge, memory, skills, assets, sandbox, quality, rules, agents → workflows

## 5. 模块路由注册流程

每个模块通过 `register_routes()` 方法将自己的 API 路由注册到 FastAPI 主应用。

### 代码流程

```python
def init_module(name: str, app: FastAPI) -> Optional[BaseModule]:
    module_class = _registered_modules.get(name)
    if not module_class or not module_class.enabled:
        return None

    # 检查依赖是否就绪
    for dep in module_class.dependencies:
        if dep not in _module_instances:
            logger.error(f"Module {name} depends on {dep} which is not initialized")
            return None

    # 创建实例
    instance = module_class()
    instance.app = app
    _module_instances[name] = instance

    # 1. 注册路由
    try:
        instance.register_routes(app)
        logger.info(f"Registered routes for module: {name}")
    except Exception as e:
        logger.error(f"Failed to register routes for module {name}: {e}")
        return None

    # 2. 注册模型
    try:
        instance.register_models()
    except Exception as e:
        logger.error(f"Failed to register models for module {name}: {e}")

    # 3. 注册事件
    try:
        instance.register_events()
    except Exception as e:
        logger.error(f"Failed to register events for module {name}: {e}")

    return instance
```

### 路由前缀规范

每个模块的路由使用 `/api/{module_name}` 作为统一前缀：

| 模块 | 路由文件 | 前缀 |
|------|---------|------|
| knowledge | `knowledge/routes.py` | `/api/knowledge` |
| memory | `memory/routes.py` | `/api/memory` |
| skills | `skills/routes.py` | `/api/skills` |
| assets | `assets/routes.py` | `/api/assets` |
| sandbox | `sandbox/routes.py` | `/api/sandbox` |
| quality | `quality/routes.py` | `/api/quality` |
| rules | `rules/routes.py` | `/api/rules` |
| agents | `agents/routes.py` | `/api/agents` |
| workflows | `workflows/routes.py` | `/api/workflows` |

## 6. 模块生命周期

完整的生命周期由 `app_lifespan` 管理，定义在 `apps/controller/app/main.py`：

```python
@asynccontextmanager
async def app_lifespan(app: FastAPI):
    # ==== 启动阶段 ====

    # 创建数据库表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 初始化默认数据（管理员用户、权限等）
    await init_database()

    # --- 模块初始化（核心阶段）---
    from app.modules import init_all_modules
    initialized_modules = init_all_modules(app)
    print(f"[AIDP] Initialized modules: {initialized_modules}")

    # --- 种子数据 ---
    try:
        from app.services.seed_data import seed_templates
        await seed_templates()
        print(f"[AIDP] Seed data initialized")
    except Exception as e:
        print(f"[AIDP] Seed data skipped: {e}")

    yield   # 应用开始处理请求

    # ==== 关闭阶段 ====
    from app.modules import shutdown_all_modules
    shutdown_all_modules()
```

### 完整流程图

```
FastAPI app_lifespan start
  │
  ├─ 1. 创建数据库表 (Base.metadata.create_all)
  │
  ├─ 2. 初始化数据库默认数据 (init_database)
  │
  ├─ 3. init_all_modules(app)
  │     │
  │     ├─ 拓扑排序解析依赖
  │     │
  │     ├─ 对每个模块调用 init_module(name, app)
  │     │     │
  │     │     ├─ 创建模块实例 (module_class())
  │     │     ├─ register_routes(app)    — 注册 API 路由
  │     │     ├─ register_models()        — 注册模型（可选）
  │     │     └─ register_events()        — 注册事件（可选）
  │     │
  │     └─ 所有模块初始化完成后调用各模块
  │          └─ on_startup()             — 模块启动回调
  │
  ├─ 4. seed_templates()                — 初始化种子模板数据
  │
  │     [应用运行中...]
  │
  └─ shutdown_all_modules()
        │
        └─ 对每个已初始化的模块
             └─ on_shutdown()           — 模块关闭回调/清理资源
```

## 7. 9 个注册模块详解

### 7.1 knowledge — 知识库模块

| 属性 | 值 |
|------|----|
| 模块名 | `knowledge` |
| API 前缀 | `/api/knowledge` |
| 依赖 | 无 |
| 模型数量 | 5（KnowledgeBase, KnowledgeDocument, DocumentChunk, KnowledgeSearchLog, DocumentTemplate） |
| 路由文件 | `knowledge/routes.py`、`knowledge/templates_routes.py` |
| **功能** | 文档知识库全生命周期管理：知识库 CRUD、文档上传/分块/解析、语义向量搜索、搜索日志记录、文档模板管理 |

### 7.2 memory — 记忆模块

| 属性 | 值 |
|------|----|
| 模块名 | `memory` |
| API 前缀 | `/api/memory` |
| 依赖 | 无 |
| 模型数量 | 3（MemoryEntry, MemoryRelation, MemoryAccessLog） |
| 路由文件 | `memory/routes.py` |
| **功能** | 项目记忆存储与检索：记忆条目管理、语义向量搜索、记忆关系图谱、访问日志追踪 |

### 7.3 skills — 技能模块

| 属性 | 值 |
|------|----|
| 模块名 | `skills` |
| API 前缀 | `/api/skills` |
| 依赖 | 无 |
| 模型数量 | 4（SkillGroup, Skill, SkillFile, SkillEvolution） |
| 路由文件 | `skills/routes.py` |
| **功能** | 三层技能管理（全局/个人/项目）：技能分组、技能定义、技能文件关联、技能演化历史、导入导出 |

### 7.4 assets — 资产模块

| 属性 | 值 |
|------|----|
| 模块名 | `assets` |
| API 前缀 | `/api/assets` |
| 依赖 | 无 |
| 模型数量 | 2（Asset, AssetTag） |
| 路由文件 | `assets/routes.py` |
| **功能** | 代码资产管理：代码片段/模板/配置的存储、标签分类、搜索、模板渲染 |

### 7.5 sandbox — 沙箱模块

| 属性 | 值 |
|------|----|
| 模块名 | `sandbox` |
| API 前缀 | `/api/sandbox` |
| 依赖 | 无 |
| 模型数量 | 1（Execution） |
| 路由文件 | `sandbox/routes.py` |
| **功能** | 安全代码执行：支持 Python/Bash/Shell 代码沙箱运行，执行记录持久化，独立容器安全隔离 |

### 7.6 quality — 质量检查模块

| 属性 | 值 |
|------|----|
| 模块名 | `quality` |
| API 前缀 | `/api/quality` |
| 依赖 | 无 |
| 模型数量 | 1（CheckResult） |
| 路由文件 | `quality/routes.py` |
| **功能** | 代码质量检查：Lint 检查、安全扫描、检查结果记录与展示 |

### 7.7 rules — 规则模块

| 属性 | 值 |
|------|----|
| 模块名 | `rules` |
| API 前缀 | `/api/rules` |
| 依赖 | 无 |
| 模型数量 | 2（RuleGroup, Rule） |
| 路由文件 | `rules/routes.py` |
| **功能** | 三层规则管理（全局/个人/项目）：规则分组、规则定义、AI 必须遵守的约束和边界 |

### 7.8 agents — Agent 模块

| 属性 | 值 |
|------|----|
| 模块名 | `agents` |
| API 前缀 | `/api/agents` |
| 依赖 | 无 |
| 模型数量 | 1（Agent） |
| 路由文件 | `agents/routes.py` |
| **功能** | Agent 全生命周期管理：Agent = Instructions + Skills + Rules + Knowledge，三层作用域（global/personal/project）组合 |

### 7.9 workflows — 流程引擎模块

| 属性 | 值 |
|------|----|
| 模块名 | `workflows` |
| API 前缀 | `/api/workflows` |
| 依赖 | `agents`（依赖 Agent 模块） |
| 模型数量 | 4（Workflow, WorkflowStep, WorkflowExecution, WorkflowExecutionStep） |
| 路由文件 | `workflows/routes.py` |
| **功能** | 多步骤多 Agent 协作流程：流程定义、步骤编排、流程执行与状态追踪、执行历史记录 |

### 汇总表

| 模块 | 依赖 | 模型数 | 路由文件数 | 核心定位 |
|------|------|--------|-----------|---------|
| knowledge | — | 5 | 2 | 知识库与语义搜索 |
| memory | — | 3 | 1 | 记忆存储与向量检索 |
| skills | — | 4 | 1 | 三层技能管理 |
| assets | — | 2 | 1 | 代码资产管理 |
| sandbox | — | 1 | 1 | 安全代码执行 |
| quality | — | 1 | 1 | 代码质量检查 |
| rules | — | 2 | 1 | 约束规则管理 |
| agents | — | 1 | 1 | Agent 组合管理 |
| workflows | agents | 4 | 1 | 流程引擎编排 |
| **合计** | — | **23** | **10** | — |

## 8. 模块信息查询

系统提供 `get_module_info()` 函数，返回所有注册模块的状态信息：

```python
def get_module_info() -> List[Dict[str, Any]]:
    """
    获取所有模块信息 — 包括注册状态和运行时状态
    """
    info = []
    for name, module_class in _registered_modules.items():
        instance = _module_instances.get(name)
        info.append({
            'name': name,
            'description': module_class.description,
            'version': module_class.version,
            'enabled': module_class.enabled,
            'initialized': instance is not None,   # 是否已成功初始化
            'dependencies': module_class.dependencies
        })
    return info
```

### 返回示例

```json
[
  {
    "name": "knowledge",
    "description": "文档知识库管理，支持语义搜索和智能分块",
    "version": "1.0.0",
    "enabled": true,
    "initialized": true,
    "dependencies": []
  },
  {
    "name": "workflows",
    "description": "流程引擎，多步骤多 Agent 协作",
    "version": "1.0.0",
    "enabled": true,
    "initialized": true,
    "dependencies": ["agents"]
  }
]
```

该信息可以通过 `/api/modules` 端点暴露给前端，用于系统状态监控面板。

### 辅助函数

```python
def get_module_instance(name: str) -> Optional[BaseModule]:
    """获取已初始化的模块实例，用于跨模块调用"""
    return _module_instances.get(name)

def require_module(name: str):
    """确保模块已初始化，否则抛出 RuntimeError"""
    if name not in _module_instances:
        raise RuntimeError(f"Module {name} is not initialized")
```

## 9. 如何新增一个模块

以下是新增一个模块的完整步骤，以新增 `notifications` 模块为例：

### 步骤 1：创建模块目录

```
apps/controller/app/modules/notifications/
├── __init__.py    # 模块注册 + 模块类
├── models.py      # 数据模型
└── routes.py      # API 路由
```

### 步骤 2：创建 `__init__.py`

```python
"""
Notifications Module
通知模块 - 提供系统通知和消息推送功能
"""

from app.modules import BaseModule, register_module


@register_module(name='notifications', enabled=True)
class NotificationsModule(BaseModule):
    name = "notifications"
    description = "系统通知管理，支持消息推送和通知订阅"
    version = "1.0.0"
    enabled = True
    dependencies = []  # 如果依赖其他模块，在这里声明

    def register_routes(self, app):
        from .routes import router as notifications_router
        app.include_router(notifications_router, prefix="/api/notifications")

    def register_models(self):
        pass  # 模型在 models.py 中定义，由 main.py import 注册

    def on_startup(self):
        print(f"[NotificationsModule] 通知模块已启动")

    def on_shutdown(self):
        print(f"[NotificationsModule] 通知模块已停止")
```

### 步骤 3：创建 `models.py`

```python
from app.db.database import Base
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime


class Notification(Base):
    __tablename__ = "aidp_notifications"
    __table_args__ = {"comment": "系统通知"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False, comment="通知标题")
    content = Column(Text, nullable=True, comment="通知内容")
    # ... 其他字段
```

> **注意**：表名使用 `aidp_` 前缀，避免与其他业务表冲突。

### 步骤 4：创建 `routes.py`

```python
from fastapi import APIRouter, Depends
from typing import List

router = APIRouter()


@router.get("/")
async def list_notifications():
    """获取通知列表"""
    return {"notifications": []}


@router.post("/")
async def create_notification():
    """创建通知"""
    return {"message": "Notification created"}
```

### 步骤 5：在 `main.py` 中导入模型并注册模块

```python
# 导入模型（确保 SQLAlchemy 能识别）
from app.modules.notifications.models import Notification

# 导入模块 __init__ 触发 @register_module 装饰器
import app.modules.notifications
```

`init_all_modules(app)` 会自动发现并初始化新增的 `notifications` 模块。

### 步骤 6：添加菜单配置（可选）

如果新模块需要在前端显示，在菜单配置文件 `app/config/menu.yaml` 中添加对应的菜单项：

```yaml
# app/config/menu.yaml
groups:
  - group: 通知管理
    icon: fas fa-bell
    order: 60
    items:
      - id: notifications
        label: 通知列表
        icon: fas fa-list
        route: /notifications
        requires_permission: notifications:view
```

## 10. 注意事项

### 10.1 表前缀

所有模块的数据库表必须使用 `aidp_` 前缀：

```python
class KnowledgeBase(Base):
    __tablename__ = "aidp_knowledge_bases"   # ✅ 正确
    # __tablename__ = "knowledge_bases"      # ❌ 错误，缺少前缀
```

前缀由模块自行在 `__tablename__` 中设置，框架不强制但应作为约定遵守。

### 10.2 依赖不能循环

模块依赖关系必须是有向无环图（DAG）。如果出现循环依赖（如 A → B → A），`init_all_modules()` 会在拓扑排序阶段检测并报错：

```
ERROR: Circular dependency detected: {'agents', 'fake_module'}
```

### 10.3 路由路径规范

- 每个模块的路由前缀统一为 `/api/{module_name}`
- 路径中不要重复模块名：`/api/knowledge/documents` ✅，`/api/knowledge/knowledge-documents` ❌
- 使用 RESTful 风格：GET `/api/knowledge/`（列表）、POST `/api/knowledge/`（创建）、GET `/api/knowledge/{id}`（详情）

### 10.4 作用域数据隔离

对于支持多层作用域的模块（如 `skills`、`rules`、`agents`），模型中应包含 `scope` 字段：

```python
class Skill(Base):
    __tablename__ = "aidp_skills"

    id = Column(Integer, primary_key=True)
    scope = Column(String(20), nullable=False, default="global")  # global / personal / project
    project_id = Column(Integer, ForeignKey("aidp_projects.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("aidp_users.id"), nullable=True)
```

作用域层级：`global`（全局模板）> `personal`（个人）> `project`（项目级）。

### 10.5 模块间通信

模块之间通过共享的 `_module_instances` 注册表通信：

```python
# 在 workflows 模块中获取 agents 模块实例
from app.modules import get_module_instance

agents_module = get_module_instance('agents')
if agents_module:
    # 调用 agents 模块的公开方法
    pass
```

避免模块间的直接循环 import，应始终通过 `get_module_instance()` 获取运行时实例。

### 10.6 禁用模块

注册时将 `enabled=False` 即可禁用模块，该模块在初始化阶段会被跳过：

```python
@register_module(name='experimental', enabled=False)  # 默认禁用
class ExperimentalModule(BaseModule):
    ...
```

### 10.7 测试模块

系统包含一个 `example` 模块（`modules/example/`），该模块不注册到生产环境，仅用于测试模块系统功能和菜单系统的正确性。开发新模块时可以参照其代码结构。