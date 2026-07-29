# Workflows Module (流程引擎)

## 概述

工作流引擎定义和执行多步骤的开发流程。每步可关联 Agent、Skills、Rules，支持条件判断和成功/失败分支。

**源码**: `apps/controller/app/modules/workflows/`
**路由前缀**: `/api/workflows`
**模型表**: `aidp_workflows`, `aidp_workflow_steps`, `aidp_workflow_executions`, `aidp_workflow_execution_steps`

## 数据模型

### Workflow (流程定义)

**表**: `aidp_workflows`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) PK | UUID |
| name | String(200) | 流程名称 (可索引) |
| description | Text | 描述 |
| category | String(50) | 分类: `"development"` / `"testing"` / `"deployment"` / `"review"` |
| trigger | String(50) | 触发器: `"manual"` / `"webhook"` / `"schedule"` / `"event"` |
| trigger_config | Text (JSON) | 触发器配置 |
| variables | Text (JSON) | 流程变量定义 |
| extra_data | Text (JSON) | 扩展数据 |
| project_id | Integer FK | 关联项目 |
| user_id | String(100) | 创建者 |
| is_active | Boolean | 是否启用 |
| is_template | Boolean | 是否模板 |
| version | Integer | 版本号 |
| deleted_at | DateTime | 软删除 |

### WorkflowStep (流程步骤)

**表**: `aidp_workflow_steps`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) PK | UUID |
| workflow_id | String(36) FK | 关联流程 (CASCADE) |
| name | String(200) | 步骤名称 |
| order | Integer | 执行顺序 |
| agent_id | String(36) FK | 关联 Agent |
| skill_ids | Text (JSON) | 关联 Skill ID 列表 |
| rule_ids | Text (JSON) | 关联 Rule ID 列表 |
| conditions | Text (JSON) | 条件配置 |
| input_mapping | Text (JSON) | 输入映射 |
| output_mapping | Text (JSON) | 输出映射 |
| timeout | Integer | 超时秒数 (默认 300) |
| on_success | Text (JSON) | 成功分支 |
| on_fail | Text (JSON) | 失败分支 |

### WorkflowExecution (执行记录)

**表**: `aidp_workflow_executions`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) PK | UUID |
| workflow_id | String(36) FK | 关联流程 |
| status | String(20) | `"running"` / `"completed"` / `"failed"` / `"cancelled"` |
| trigger_type | String(50) | 触发类型 |
| trigger_data | Text (JSON) | 触发数据 |
| current_step | Integer | 当前步骤序号 |
| variables | Text (JSON) | 运行时变量 |
| started_at | DateTime | 开始时间 |
| completed_at | DateTime | 完成时间 |

### WorkflowExecutionStep (步骤执行记录)

**表**: `aidp_workflow_execution_steps`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) PK | UUID |
| execution_id | String(36) FK | 关联执行记录 |
| step_id | String(36) FK | 关联步骤定义 |
| step_name | String(200) | 步骤名称 (冗余) |
| step_order | Integer | 步骤序号 (冗余) |
| status | String(20) | `"pending"` / `"running"` / `"completed"` / `"failed"` / `"skipped"` |
| started_at | DateTime | 开始时间 |
| completed_at | DateTime | 完成时间 |
| duration_ms | Integer | 耗时 (毫秒) |
| input_data | Text (JSON) | 输入数据 |
| output_data | Text (JSON) | 输出数据 |
| error | Text | 错误信息 |
| retry_count | Integer | 重试次数 |

## API 端点

### 工作流 CRUD

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/workflows/list` | GET | - | 列出工作流 (category, project_id, search, is_template) |
| `/api/workflows/create` | POST | `skills:write:personal` | 创建流程 (含 steps) |
| `/api/workflows/templates/list` | GET | - | 列出模板 (原生 SQL 查询) |
| `/api/workflows/stats` | GET | - | 统计 (total, by_category, active_executions) |
| `/api/workflows/{workflow_id}` | GET | - | 获取流程 (含 steps) |
| `/api/workflows/{workflow_id}` | PUT | `skills:write:personal` | 更新流程 |
| `/api/workflows/{workflow_id}` | DELETE | `skills:write:personal` | 软删除流程 |

### 步骤管理

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/workflows/{workflow_id}/steps` | POST | `skills:write:personal` | 添加步骤 |
| `/api/workflows/{workflow_id}/steps/{step_id}` | PUT | `skills:write:personal` | 更新步骤 |
| `/api/workflows/{workflow_id}/steps/{step_id}` | DELETE | `skills:write:personal` | 删除步骤 |

### 执行

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/workflows/{workflow_id}/execute` | POST | - | 执行工作流 (支持 variables 参数) |
| `/api/workflows/executions/list` | GET | - | 列出执行历史 (workflow_id, status) |
| `/api/workflows/executions/{execution_id}` | GET | - | 获取执行详情 |
| `/api/workflows/executions/{execution_id}/cancel` | POST | `skills:write:personal` | 取消执行 |

## 执行流程

`POST /api/workflows/{workflow_id}/execute`:

1. 加载 Workflow 定义
2. 解析 `variables` 参数 (JSON 字符串)
3. 创建 `WorkflowExecution` (status=running, started_at=now)
4. 按 order 加载所有 WorkflowStep
5. 为每个 step 创建 `WorkflowExecutionStep` (status=completed)
6. 更新 execution.status = "completed", completed_at=now
7. 返回 execution.to_dict()

## 数据关系图

```
aidp_workflows (1) ----< aidp_workflow_steps (N, CASCADE)
aidp_workflows (1) ----< aidp_workflow_executions (N)
aidp_workflow_executions (1) ----< aidp_workflow_execution_steps (N, CASCADE)
aidp_workflow_steps (1) ----< aidp_workflow_execution_steps (N)
aidp_agents (1) ----< aidp_workflow_steps (agent_id)
aidp_projects (1) ----< aidp_workflows (N)
```