# Rules Module (规则模块)

## 概述

规则模块管理 AI Agent 的行为约束和代码规范。采用三层架构: `global` / `personal` / `project`。支持规则分组、审核、推广机制。

**源码**: `apps/controller/app/modules/rules/`
**路由前缀**: `/api/rules`
**模型表**: `aidp_rules`, `aidp_rule_groups`

## 数据模型

### Rule (规则)

**表**: `aidp_rules`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) PK | UUID |
| name | String(200) | 规则名称 (可索引) |
| description | Text | 描述 |
| content | Text | 规则内容 |
| category | String(50) | 分类 (默认 `"code_style"`) |
| severity | String(20) | 严重级别 (默认 `"medium"`) |
| priority | Integer | 优先级 (可索引) |
| version | Integer | 版本号，默认 1 |
| scope | String(20) | `"global"` / `"personal"` / `"project"` |
| pattern | Text | 正则匹配模式 |
| auto_fix | Text | 自动修复规则 |
| allowed_roles | Text (JSON) | 允许的角色 |
| tags | Text (JSON) | 标签 |
| review_status | String(20) | 审核状态 (默认 `"approved"`) |
| review_report | Text | 审核报告 |
| review_log | Text (JSON) | 审核日志 |
| promotion_status | String(20) | 推广状态: none/pending/reviewed/promoted/rejected/rolled_back |
| promotion_report | Text | 推广报告 |
| promotion_source_id | String(36) | 推广源 ID |
| promotion_source_scope | String(20) | 推广源 scope |
| promotion_promoted_at | DateTime | 推广时间 |
| embedding | Text | 向量嵌入 |
| embedding_model | String(128) | 嵌入模型 |
| group_id | String(36) FK | 关联分组 |
| user_id | String(100) | 创建者 |
| project_id | Integer FK | 关联项目 |
| is_active | Boolean | 是否启用 (可索引) |
| access_count | Integer | 访问计数 |
| extra_data | Text (JSON) | 扩展数据 |
| deleted_at | DateTime | 软删除时间 |

### RuleGroup (规则分组)

**表**: `aidp_rule_groups`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) PK | UUID |
| name | String(100) | 分组名 |
| description | Text | 描述 |
| scope | String(20) | `"personal"` 等 |
| parent_id | String(36) FK | 父分组 (自引用) |
| user_id | String(100) | 创建者 |
| project_id | Integer FK | 关联项目 |
| sort_order | Integer | 排序 |

## API 端点

### 规则 (Rule)

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/rules/list` | GET | scope_read_access | 列出规则 (scope, category, severity, project_id, group_id, search) |
| `/api/rules/create` | POST | `skills:write:personal` | 创建规则 |
| `/api/rules/search` | POST | scope_read_access | 搜索规则 |
| `/api/rules/stats` | GET | scope_read_access | 统计 (total, by_category, by_severity) |
| `/api/rules/{rule_id}` | GET | scope_read_access | 获取规则详情 (access_count++) |
| `/api/rules/{rule_id}` | PUT | `skills:write:personal` | 更新规则 (含 review/promotion 字段) |
| `/api/rules/{rule_id}` | DELETE | `skills:write:personal` | 软删除规则 |
| `/api/rules/{rule_id}/move` | POST | `skills:write:personal` | 移动规则 (group_id, scope) |

### 分组 (RuleGroup)

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/rules/groups/list` | GET | scope_read_access | 列出分组 (按 sort_order) |
| `/api/rules/groups/create` | POST | `skills:write:personal` | 创建分组 |
| `/api/rules/groups/{group_id}` | DELETE | `skills:write:personal` | 删除分组 |

## 审核和推广机制

规则支持完整的审核和推广生命周期:

### 审核字段
- `review_status`: `"approved"` (默认) — 审核结果
- `review_report`: 审核报告
- `review_log`: JSON 数组形式的审核日志

### 推广字段
- `promotion_status`: `"none"` → `"pending"` → `"reviewed"` → `"promoted"` → 可 `"rejected"` 或 `"rolled_back"`
- `promotion_source_id` / `promotion_source_scope`: 记录推广来源，用于追踪个人规则 → 项目规则 → 全局规则的升迁路径

## 三层架构

与 Skills 相同的 scope 隔离:

| Scope | 说明 | filter 条件 |
|-------|------|-------------|
| `global` | 全局规则 | `Rule.scope == "global"` |
| `personal` | 个人规则 | `Rule.scope == "personal" AND Rule.user_id == uid` |
| `project` | 项目规则 | `Rule.scope == "project" AND Rule.project_id == pid` |

## 数据关系图

```
aidp_rule_groups (1) ----< aidp_rule_groups (自引用 parent_id)
aidp_rule_groups (1) ----< aidp_rules (N)
aidp_projects (1) ----< aidp_rules (N)
aidp_projects (1) ----< aidp_rule_groups (N)
```