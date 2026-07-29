# Memory Module (记忆模块)

## 概述

记忆模块管理项目级别的开发经验记忆，支持语义搜索、图谱关系、AI 审核和上下文包。

**源码**: `apps/controller/app/modules/memory/`
**路由前缀**: `/api/memory`
**模型表**: 全部前缀 `aidp_memory_*`

## 数据模型

### MemoryEntry (记忆条目)

**表**: `aidp_memory_entries`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) PK | UUID |
| project_id | Integer FK | 关联 `aidp_projects.id` |
| user_id | String(100) | 创建者 |
| category | String(50) | 分类 (可索引) |
| memory_tier | String(20) | 记忆层级 (默认 `"semantic"`) |
| title | String(200) | 标题 |
| content | Text | 内容 |
| embedding | Text | 向量嵌入 |
| embedding_model | String(128) | 嵌入模型 |
| parent_id | String(36) FK | 自引用父记忆 |
| confidence_score | Float | 置信度 (0.0-1.0) |
| ai_suggested | Boolean | AI 建议标记 (可索引) |
| ai_review_status | String(20) | AI 审核状态 (approved/pending) |
| ai_review_comment | Text | AI 审核意见 |
| merged_from | Text | 合并来源 |
| access_count | Integer | 访问计数 |
| last_accessed_at | DateTime | 最后访问时间 |
| source_type | String(50) | `"manual"` 等 |
| source_uri | String(500) | 来源 URI |
| extra_data | Text (JSON) | 扩展数据 |
| deleted_at | DateTime | 软删除时间 |

**关系**:
- `parent` / `children`: 自引用层级结构
- `outgoing_relations` / `incoming_relations`: 关联 MemoryRelation

### MemoryRelation (记忆关系)

**表**: `aidp_memory_relations`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) PK | UUID |
| source_id | String(36) FK | 源记忆 |
| target_id | String(36) FK | 目标记忆 |
| relation_type | String(50) | 关系类型，如 `"related"` |
| strength | Float | 关系强度 (0.0-1.0) |
| description | Text | 关系描述 |

### MemoryAccessLog (访问日志)

**表**: `aidp_memory_access_logs`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) PK | UUID |
| memory_id | String(36) FK | 关联记忆 |
| project_id | Integer FK | 关联项目 |
| action | String(50) | 操作类型 |
| query | Text | 查询词 |
| user_id | String(100) | 用户 ID |
| ip_address | String(45) | IP 地址 |

### ContextPackage (上下文包)

**表**: `aidp_context_packages`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) PK | UUID |
| name | String(200) | 包名 |
| description | Text | 描述 |
| project_id | Integer FK | 关联项目 |
| user_id | String(100) | 创建者 |
| created_by | String(100) | 创建者名称 |
| memory_ids | Text (JSON) | 包含的记忆 ID 列表 |
| generated_context | Text | 生成的上下文 |
| total_tokens | Integer | 总 token 数 |
| is_template | Boolean | 是否模板 (可索引) |
| usage_count | Integer | 使用次数 |

## API 端点

### 记忆 (MemoryEntry)

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/memory/memories` | GET | - | 列出记忆 (project_id, category, memory_tier, search) |
| `/api/memory/memories` | POST | `memory:write` | 创建记忆 |
| `/api/memory/memories/{memory_id}` | GET | - | 获取记忆详情 (含 content, 自动 access_count++) |
| `/api/memory/memories/{memory_id}` | PUT | `memory:write` | 更新记忆 (title, content, category, memory_tier, confidence_score, extra_data) |
| `/api/memory/memories/{memory_id}` | DELETE | `memory:delete` | 软删除记忆 |

### 关系 (MemoryRelation)

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/memory/memories/{memory_id}/relations` | GET | - | 获取记忆的 outgoing + incoming 关系 |
| `/api/memory/memories/{memory_id}/relations` | POST | `memory:write` | 创建关系 (source→target) |
| `/api/memory/relations/{relation_id}` | DELETE | `memory:write` | 删除关系 |
| `/api/memory/relations/auto-generate` | POST | `memory:write` | 自动生成关系 (基于共享 category) |

### 搜索与统计

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/memory/search` | POST | - | 搜索记忆 (title+content 全文匹配) |
| `/api/memory/graph` | GET | - | 获取记忆图谱 (nodes + links) |
| `/api/memory/stats` | GET | - | 统计 (total, by_category, by_tier) |

### 审核 (AI Review)

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/memory/review/queue` | GET | - | 获取待审队列 (ai_suggested=true) |
| `/api/memory/review/{memory_id}` | POST | `memory:write` | 审核记忆 (status, comment) |
| `/api/memory/review/{memory_id}/reset` | POST | `memory:write` | 重置审核状态为 pending |

### 上下文包 (ContextPackage)

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/memory/context/list` | GET | - | 列出上下文包 |
| `/api/memory/context/create` | POST | `memory:write` | 创建上下文包 |
| `/api/memory/context/{pkg_id}` | GET | - | 获取上下文包 (含 generated_context) |
| `/api/memory/context/{pkg_id}` | PUT | `memory:write` | 更新上下文包 |
| `/api/memory/context/{pkg_id}` | DELETE | `memory:write` | 删除上下文包 |
| `/api/memory/context/preview` | POST | - | 预览上下文 (传入 memory_ids 列表) |

## 数据关系图

```
aidp_projects (1) ----< aidp_memory_entries (N)
aidp_memory_entries (1) ----< aidp_memory_entries (自引用 parent_id)
aidp_memory_entries (1) ----< aidp_memory_relations (source)
aidp_memory_entries (1) ----< aidp_memory_relations (target)
aidp_memory_entries (1) ----< aidp_memory_access_logs (N)
aidp_projects (1) ----< aidp_context_packages (N)
```