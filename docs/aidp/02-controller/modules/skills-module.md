# Skills Module (技能模块)

## 概述

技能模块管理 AI Agent 使用的技能定义，包括指令、内容、执行配置、文件、版本演进。采用三层架构: `global` / `personal` / `project`。

**源码**: `apps/controller/app/modules/skills/`
**路由前缀**: `/api/skills`
**模型表**: 全部前缀 `aidp_skill*`

## 数据模型

### Skill (技能)

**表**: `aidp_skills`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) PK | UUID |
| name | String(200) | 技能名称 (可索引) |
| description | Text | 描述 |
| scope | String(20) | `"global"` / `"personal"` / `"project"` |
| instruction | Text | 指令 |
| content | Text | 内容 |
| tags | Text (JSON) | 标签列表 |
| version | Integer | 版本号 |
| dependencies | Text (JSON) | 依赖列表 |
| exec_config | Text (JSON) | 执行配置 |
| embedding | Text | 向量嵌入 |
| embedding_model | String(128) | 嵌入模型 |
| review_status | String(20) | 审核状态 (approved/pending) |
| review_report | Text | 审核报告 |
| review_log | Text (JSON) | 审核日志 |
| allow_risk_patterns | Text (JSON) | 允许的风险模式 |
| allowed_roles | Text (JSON) | 允许的角色 |
| sensitive | Boolean | 是否敏感 |
| promotion_status | String(20) | 推广状态: none/pending/reviewed/promoted/rejected/rolled_back |
| promotion_report | Text | 推广报告 |
| promotion_source_id | String(36) | 推广源 ID |
| promotion_source_scope | String(20) | 推广源 scope |
| promotion_promoted_at | DateTime | 推广时间 |
| weight_config | Text (JSON) | 权重配置 |
| examples | Text (JSON) | 示例列表 |
| source_url | String(500) | 来源 URL |
| source_type | String(50) | `"manual"` / `"web"` / `"package"` |
| source_id | String(200) | 来源 ID |
| group_id | String(36) FK | 关联分组 |
| user_id | String(100) | 创建者 |
| project_id | Integer FK | 关联项目 |
| access_count | Integer | 访问计数 |
| last_accessed_at | DateTime | 最后访问时间 |
| extra_data | Text (JSON) | 扩展数据 |
| deleted_at | DateTime | 软删除时间 |

### SkillGroup (技能分组)

**表**: `aidp_skill_groups`

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

### SkillFile (技能文件)

**表**: `aidp_skill_files`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) PK | UUID |
| skill_id | String(36) FK | 关联技能 |
| path | String(500) | 文件路径 |
| content | Text | 文件内容 |
| language | String(50) | 语言 |
| is_entry | Boolean | 是否入口文件 |
| sort_order | Integer | 排序 |

### SkillEvolution (版本演进)

**表**: `aidp_skill_evolutions`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) PK | UUID |
| skill_id | String(36) FK | 关联技能 |
| old_version | Integer | 旧版本号 |
| old_content | Text | 旧内容 |
| new_content | Text | 新内容 |
| diff_summary | Text | 变更摘要 |
| trigger_reason | String(100) | 触发原因 (`"manual"` 等) |
| status | String(20) | 状态 |
| rollback_to | Integer | 回滚目标版本 |
| created_at | DateTime | 创建时间 |

## API 端点

### 技能 (Skill)

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/skills/capabilities` | GET | - | 返回模块能力声明 |
| `/api/skills/list` | GET | scope_read_access | 列出技能 (scope, project_id, group_id, search, tag) |
| `/api/skills/create` | POST | `skills:write:personal` | 创建技能 |
| `/api/skills/search` | POST | scope_read_access | 搜索技能 |
| `/api/skills/stats` | GET | scope_read_access | 统计 (total, by_scope) |
| `/api/skills/{skill_id}` | GET | scope_read_access | 获取技能详情 (access_count++) |
| `/api/skills/{skill_id}` | PUT | `skills:write:personal` | 更新技能 |
| `/api/skills/{skill_id}` | DELETE | `skills:write:personal` | 软删除技能 |
| `/api/skills/{skill_id}/move` | POST | `skills:write:personal` | 移动技能 (group_id, scope) |

### 分组 (SkillGroup)

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/skills/groups/list` | GET | scope_read_access | 列出分组 |
| `/api/skills/groups/create` | POST | `skills:write:personal` | 创建分组 |
| `/api/skills/groups/{group_id}` | PUT | `skills:write:personal` | 更新分组 |
| `/api/skills/groups/{group_id}` | DELETE | `skills:write:personal` | 删除分组 |

### 文件 (SkillFile)

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/skills/{skill_id}/files` | GET | - | 获取技能文件列表 |
| `/api/skills/{skill_id}/files` | POST | `skills:write:personal` | 保存技能文件 (替换全部) |

### 版本演进 (SkillEvolution)

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/skills/{skill_id}/evolutions` | GET | - | 列出演进历史 |
| `/api/skills/{skill_id}/evolutions` | POST | `skills:write:personal` | 创建演进记录 (自动 version++) |

### 审核

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/skills/{skill_id}/review` | POST | `skills:write:personal` | 审核技能 (report, status, log, risk_patterns) |
| `/api/skills/{skill_id}/exec-config` | POST | `skills:write:personal` | 保存执行配置 |

### 导入/导出

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/skills/import` | POST | `skills:write:personal` | 从 URL 导入技能 (httpx + BeautifulSoup) |
| `/api/skills/upload` | POST | `skills:write:personal` | 上传技能包 (tar.gz) |
| `/api/skills/{skill_id}/package` | GET | - | 下载技能包 (tar.gz, 含 skill.json + 文件) |

## 三层架构 (Scope System)

技能模块实现三层访问隔离:

| Scope | 说明 | 可见性 |
|-------|------|--------|
| `global` | 全局共享 | 所有人可见 (scope == "global") |
| `personal` | 个人私有 | 仅创建者可见 (scope == "personal" AND user_id == current_user) |
| `project` | 项目级 | 仅项目成员可见 (scope == "project" AND project_id == current_project) |

实现函数 `_scope_filter(model, scope, user_id, project_id)` 动态构造 SQL WHERE 条件。

## 数据关系图

```
aidp_skill_groups (1) ----< aidp_skill_groups (自引用 parent_id)
aidp_skill_groups (1) ----< aidp_skills (N)
aidp_skills (1) ----< aidp_skill_files (N)
aidp_skills (1) ----< aidp_skill_evolutions (N)  -- 版本演进历史
aidp_projects (1) ----< aidp_skills (N)
aidp_projects (1) ----< aidp_skill_groups (N)
```