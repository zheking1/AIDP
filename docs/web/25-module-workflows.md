# Workflows Module — 工作流模块

## 1. 模块概述

Workflows（工作流）模块是 AIDP 平台的流程引擎，提供**多步骤、多 Agent 协作**的流程定义与执行能力。用户可以通过可视化界面定义由多个步骤组成的工作流，每个步骤可以关联不同的 Agent，实现复杂的自动化流水线。

模块定义文件位于 `apps/controller/app/modules/workflows/__init__.py`：

```python
@register_module(name='workflows', enabled=True)
class WorkflowsModule(BaseModule):
    name = "workflows"
    description = "流程引擎，多步骤多 Agent 协作"
    version = "1.0.0"
    enabled = True
    dependencies = ['agents']

    def register_routes(self, app):
        from .routes import router as workflows_router
        app.include_router(workflows_router, prefix="/api/workflows")
```

模块声明依赖 `agents` 模块，因为每个步骤可以关联一个 Agent 执行实际任务。

## 2. 数据模型（4 models）

模块包含 4 个 SQLAlchemy 数据模型，位于 `apps/controller/app/modules/workflows/models.py`：

### Workflow — 流程定义

```python
class Workflow(Base):
    __tablename__ = "aidp_workflows"

    id            = Column(String(36), primary_key=True, default=gen_uuid)
    name          = Column(String(200), nullable=False, index=True)
    description   = Column(Text, nullable=True)
    category      = Column(String(50), default="development", index=True)
    # development / testing / deployment / review
    trigger       = Column(String(50), default="manual", index=True)
    # manual / webhook / schedule / event
    trigger_config = Column(Text, default="{}")
    variables     = Column(Text, default="[]")
    extra_data    = Column(Text, default="{}")
    project_id    = Column(Integer, ForeignKey("aidp_projects.id"), nullable=True, index=True)
    user_id       = Column(String(100), nullable=True, index=True)
    is_active     = Column(Boolean, default=True, index=True)
    is_template   = Column(Boolean, default=False, index=True)
    version       = Column(Integer, default=1)
    created_at    = Column(DateTime(timezone=True), default=utcnow)
    updated_at    = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    deleted_at    = Column(DateTime(timezone=True), nullable=True)

    steps = relationship("WorkflowStep", back_populates="workflow",
                         cascade="all, delete-orphan", order_by="WorkflowStep.order")
```

### WorkflowStep — 流程步骤

```python
class WorkflowStep(Base):
    __tablename__ = "aidp_workflow_steps"

    id              = Column(String(36), primary_key=True, default=gen_uuid)
    workflow_id     = Column(String(36), ForeignKey("aidp_workflows.id", ondelete="CASCADE"), nullable=False)
    name            = Column(String(200), nullable=False)
    order           = Column(Integer, nullable=False)
    agent_id        = Column(String(36), ForeignKey("aidp_agents.id"), nullable=True)
    skill_ids       = Column(Text, default="[]")
    rule_ids        = Column(Text, default="[]")
    conditions      = Column(Text, default="{}")
    input_mapping   = Column(Text, default="{}")
    output_mapping  = Column(Text, default="{}")
    timeout         = Column(Integer, default=300)
    on_success      = Column(Text, default="{}")
    on_fail         = Column(Text, default="{}")
    extra_data      = Column(Text, default="{}")
    created_at      = Column(DateTime(timezone=True), default=utcnow)
    updated_at      = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
```

### WorkflowExecution — 流程执行记录

```python
class WorkflowExecution(Base):
    __tablename__ = "aidp_workflow_executions"

    id            = Column(String(36), primary_key=True, default=gen_uuid)
    workflow_id   = Column(String(36), ForeignKey("aidp_workflows.id"), nullable=False)
    status        = Column(String(20), default="running", index=True)
    # running / completed / failed / cancelled
    trigger_type  = Column(String(50), default="manual")
    trigger_data  = Column(Text, default="{}")
    current_step  = Column(Integer, default=0)
    variables     = Column(Text, default="{}")
    started_at    = Column(DateTime(timezone=True), default=utcnow)
    completed_at  = Column(DateTime(timezone=True), nullable=True)
    created_at    = Column(DateTime(timezone=True), default=utcnow)
```

### WorkflowExecutionStep — 步骤执行记录

```python
class WorkflowExecutionStep(Base):
    __tablename__ = "aidp_workflow_execution_steps"

    id            = Column(String(36), primary_key=True, default=gen_uuid)
    execution_id  = Column(String(36), ForeignKey("aidp_workflow_executions.id"), nullable=False)
    step_id       = Column(String(36), ForeignKey("aidp_workflow_steps.id"), nullable=True)
    step_name     = Column(String(200), nullable=True)
    step_order    = Column(Integer, nullable=True)
    status        = Column(String(20), default="pending")
    # pending / running / completed / failed / skipped
    started_at    = Column(DateTime(timezone=True), nullable=True)
    completed_at  = Column(DateTime(timezone=True), nullable=True)
    duration_ms   = Column(Integer, nullable=True)
    input_data    = Column(Text, default="{}")
    output_data   = Column(Text, default="{}")
    error         = Column(Text, nullable=True)
    retry_count   = Column(Integer, default=0)
    created_at    = Column(DateTime(timezone=True), default=utcnow)
```

**模型关系总结：**

```
Workflow 1 ── N WorkflowStep        (通过 workflow_id 关联，按 order 排序)
Workflow 1 ── N WorkflowExecution   (每次执行创建一条记录)
WorkflowExecution 1 ── N WorkflowExecutionStep  (每个步骤的执行快照)
WorkflowStep 1 ── N WorkflowExecutionStep       (通过 step_id 关联)
```

## 3. API 端点

所有路由定义在 `apps/controller/app/modules/workflows/routes.py` 中，通过 `APIRouter` 注册，前缀为 `/api/workflows`。

### 工作流 CRUD

| 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|
| GET | `/api/workflows/list` | 列出工作流（支持 category/project_id/search/is_template 筛选） | 登录用户 |
| POST | `/api/workflows/create` | 创建工作流（含步骤） | skills:write:personal |
| GET | `/api/workflows/{workflow_id}` | 获取单个工作流详情（含步骤） | 登录用户 |
| PUT | `/api/workflows/{workflow_id}` | 更新工作流 | skills:write:personal |
| DELETE | `/api/workflows/{workflow_id}` | 软删除工作流 | skills:write:personal |

### 步骤管理

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/workflows/{workflow_id}/steps` | 添加步骤 |
| PUT | `/api/workflows/{workflow_id}/steps/{step_id}` | 更新步骤 |
| DELETE | `/api/workflows/{workflow_id}/steps/{step_id}` | 删除步骤 |

### 执行相关

| 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|
| POST | `/api/workflows/{workflow_id}/execute` | 启动执行 | 公开 |
| POST | `/api/workflows/executions/{execution_id}/cancel` | 取消执行 | skills:write:personal |
| GET | `/api/workflows/executions/list` | 执行历史列表 | 登录用户 |
| GET | `/api/workflows/executions/{execution_id}` | 获取执行详情 | 登录用户 |

### 模板

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/workflows/templates/list` | 模板列表（is_template=True 的工作流） |

### 统计

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/workflows/stats` | 工作流统计（总数、分类统计、活跃执行数） |

### 创建/更新接口的 Pydantic 模型

```python
class StepCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    order: int = 0
    agent_id: Optional[str] = None
    skill_ids: List[str] = Field(default_factory=list)
    rule_ids: List[str] = Field(default_factory=list)
    conditions: Optional[dict] = Field(default_factory=dict)
    input_mapping: Optional[dict] = Field(default_factory=dict)
    output_mapping: Optional[dict] = Field(default_factory=dict)
    timeout: int = 300
    on_success: Optional[dict] = Field(default_factory=dict)
    on_fail: Optional[dict] = Field(default_factory=dict)

class WorkflowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category: str = "development"
    trigger: str = "manual"
    trigger_config: Optional[dict] = Field(default_factory=dict)
    variables: List[dict] = Field(default_factory=list)
    steps: List[StepCreate] = Field(default_factory=list)
```

## 4. 执行引擎

工作流的执行流程如下：

### 4.1 启动执行

```python
@router.post("/{workflow_id}/execute")
async def execute_workflow(workflow_id: str,
    variables: Optional[str] = Query(None, description="JSON string of variables"),
    db: AsyncSession = Depends(get_db)):
```

### 4.2 执行步骤

1. **创建执行记录** — 创建 `WorkflowExecution`，status 设为 `"running"`
2. **加载步骤** — 按 `WorkflowStep.order` 升序查询所有步骤
3. **遍历步骤** — 为每个步骤创建 `WorkflowExecutionStep`
4. **标记完成** — 所有步骤标记为 `"completed"`，execution status 更新为 `"completed"`

当前实现（路线 335-372）为同步顺序执行框架：

```python
execution = WorkflowExecution(
    workflow_id=workflow_id, status="running",
    variables=json.dumps(parsed_vars),
    started_at=datetime.now(timezone.utc))
db.add(execution)
await db.flush()

steps = await db.execute(
    select(WorkflowStep).where(WorkflowStep.workflow_id == workflow_id)
    .order_by(WorkflowStep.order))
steps_list = steps.scalars().all()

for step in steps_list:
    es = WorkflowExecutionStep(
        execution_id=execution.id, step_id=step.id,
        step_name=step.name, step_order=step.order, status="completed")
    db.add(es)

execution.status = "completed"
execution.completed_at = datetime.now(timezone.utc)
await db.commit()
```

### 4.3 取消执行

```python
@router.post("/executions/{execution_id}/cancel")
async def cancel_execution(execution_id: str, ...):
    execution.status = "cancelled"
    execution.completed_at = datetime.now(timezone.utc)
    await db.commit()
    return {"success": True}
```

### 4.4 状态流转

```
pending → running → completed
                   → failed
                   → cancelled
```

`WorkflowExecutionStep` 的状态包括：`pending / running / completed / failed / skipped`

## 5. 步骤编排

`WorkflowStep` 是工作流的编排核心，以下是关键设计：

### 5.1 执行顺序

`step.order`（对应模型中的 `order` 字段）控制步骤的执行顺序。数据库查询时使用 `order_by(WorkflowStep.order)` 确保按照定义的顺序执行。在前端展示时，步骤编号从 1 开始递增。

### 5.2 Agent 关联

`agent_id` 字段关联 `aidp_agents` 表中的 Agent。每个步骤可以被分配给不同的 Agent 来执行。还支持 `skill_ids`（技能列表）和 `rule_ids`（规则列表），实现更精细的控制。

### 5.3 输入输出映射

```python
input_mapping  = Column(Text, default="{}")    # 定义步骤入参
output_mapping = Column(Text, default="{}")     # 定义步骤出参
```

这两个 JSON 字段定义如何从工作流变量或上游步骤的输出中提取输入，以及如何将本步骤的输出映射回工作流变量空间。

### 5.4 条件与分支

```python
conditions = Column(Text, default="{}")    # 条件判断
on_success = Column(Text, default="{}")    # 成功后处理
on_fail    = Column(Text, default="{}")    # 失败后处理
```

`conditions` 支持条件执行（满足条件才执行本步骤），`on_success` 和 `on_fail` 定义成功/失败后的动作（如跳转到指定步骤、重试、终止等）。

### 5.5 超时与重试

```python
timeout     = Column(Integer, default=300)    # 超时时间（秒）
```

每个步骤可以设置独立的超时时间（默认 300 秒）。`WorkflowExecutionStep` 中的 `retry_count` 记录重试次数，`duration_ms` 记录执行耗时。

## 6. 前端

前端模板位于 `apps/controller/app/web/templates/modules/workflows/list_content.html`，使用 Alpine.js 进行状态管理。

### 核心 Alpine 组件：`workflowsPage()`

```javascript
window.workflowsPage = function workflowsPage() {
    return {
        workflows: [],         // 工作流列表
        templates: [],         // 模板列表
        executions: [],        // 执行记录
        searchQuery: '',
        filterCategory: '',
        loading: false,
        showCreateModal: false,
        showDetailModal: false,
        showTemplateModal: false,
        detail: null,
        detailTab: 'info',
        form: { name: '', description: '', category: 'development' },

        async init() {
            await Promise.all([this.loadWorkflows(), this.loadTemplates()]);
        },
        // ...
    };
};
```

### 关键 UI 元素

| UI 元素 | 功能 |
|---------|------|
| **搜索框** | 按名称/描述搜索工作流 |
| **分类筛选** | development/testing/deployment/review |
| **创建流程按钮** | 弹出创建模态框 |
| **从模板按钮** | 从模板创建工作流 |
| **工作流卡片列表** | 展示名称、分类、版本、描述 |
| **详情模态框** | 含三个 tab：信息 / 步骤 / 执行记录 |
| **执行按钮** | 触发工作流执行 |
| **删除按钮** | 软删除工作流 |

### 分类图标映射

- **development** → 蓝色 + `fa-code`
- **testing** → 绿色 + `fa-vial`
- **deployment** → 紫色 + `fa-rocket`
- **review** → 黄色 + `fa-search`

## 7. 依赖

Workflows 模块**直接依赖 Agents 模块**（在 `dependencies = ['agents']` 中声明）。每个 `WorkflowStep.agent_id` 外键关联到 `aidp_agents` 表。运行时，工作流引擎通过 Agent 模块的能力来执行每个步骤的具体任务。

此外，还依赖以下基础设施：
- **Database** — SQLAlchemy + PostgreSQL，4 张业务表（`aidp_workflows`、`aidp_workflow_steps`、`aidp_workflow_executions`、`aidp_workflow_execution_steps`）
- **Auth** — 通过 `require_permissions` 和 `get_current_user` 做权限控制
- **Projects** — `project_id` 外键关联项目