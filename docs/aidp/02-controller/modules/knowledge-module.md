# Knowledge Module (知识库模块)

## 概述

知识库模块管理项目文档、知识库 (KnowledgeBase)、文档分块 (DocumentChunk)、文档模板 (DocumentTemplate) 和项目-知识库绑定 (ProjectKnowledgeBinding)。

**源码**: `apps/controller/app/modules/knowledge/`
**路由前缀**: `/api/knowledge`
**模型表**: 全部前缀 `aidp_knowledge_*`

## 数据模型

### KnowledgeBase (知识库)

**表**: `aidp_knowledge_bases`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) PK | UUID |
| project_id | Integer FK | 关联 `aidp_projects.id` |
| user_id | String(100) | 创建者 |
| name | String(200) | 知识库名称 |
| slug | String(128) | URL 友好名 |
| kb_level | String(32) | `"framework"` / `"template"` / `"project"` |
| parent_id | String(36) FK | 父知识库 (层级结构) |
| domains | Text (JSON) | 领域标签 |
| keywords | Text (JSON) | 关键词 |
| tech_stack | Text (JSON) | 技术栈 |
| visibility | String(20) | `"private"` / `"team"` / `"public"` |
| chunking_strategy | String(50) | 分块策略，默认 `"fixed"` |
| chunk_size | Integer | 分块大小，默认 500 |
| chunk_overlap | Integer | 重叠大小，默认 50 |
| embedding_model | String(128) | `"text-embedding-3-small"` |
| document_count | Integer | 文档计数 |
| total_chunks | Integer | 总块数 |
| extra_data | Text (JSON) | 扩展数据 |
| deleted_at | DateTime | 软删除时间 |

**关系**:
- `documents`: one-to-many → KnowledgeDocument
- `children`: self-referential (parent_id), 支持层级知识库

### KnowledgeDocument (知识库文档)

**表**: `aidp_knowledge_documents`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) PK | UUID |
| base_id | String(36) FK | 关联知识库 |
| project_id | Integer FK | 关联项目 |
| user_id | String(100) | 创建者 |
| title | String(500) | 文档标题 |
| source_type | String(50) | `"manual"` 等 |
| source_uri | String(1000) | 来源 URI |
| content | Text | 文档内容 |
| mime_type | String(100) | MIME 类型 |
| file_size | Integer | 文件大小 |
| chunk_count | Integer | 分块数 |
| category | String(100) | 分类，可索引 |
| embedding | Text | 向量嵌入 |
| embedding_model | String(128) | 嵌入模型 |
| tags | Text (JSON) | 标签 |
| checksum | String(128) | 校验和 |
| version | String(128) | 版本号，默认 `"v1"` |
| index_status | String(20) | 索引状态: pending/indexing/indexed/error |
| summary | Text | 摘要 |
| visibility | String(20) | `"private"` / `"team"` / `"public"` |
| owner_type | String(32) | `"personal"` / `"team"` / `"system"` |
| processing_status | String(20) | 处理状态 (pending/completed) |
| promotion_status | String(20) | 推广状态: none/pending/reviewed/promoted/rejected/rolled_back |
| promotion_report | Text | 推广报告 |
| promotion_source_id | String(36) | 推广来源 ID |
| promotion_source_scope | String(20) | 推广来源 scope |
| deleted_at | DateTime | 软删除时间 |

### DocumentChunk (文档分块)

**表**: `aidp_document_chunks`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) PK | UUID |
| document_id | String(36) FK | 关联文档 |
| base_id | String(36) FK | 关联知识库 |
| chunk_index | Integer | 块序号 |
| content | Text | 块内容 |
| embedding | Text | 向量嵌入 |
| token_count | Integer | token 数 |

### ProjectKnowledgeBinding (项目-知识库绑定)

**表**: `aidp_project_knowledge_bindings`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) PK | UUID |
| project_id | String(128) | 项目 ID |
| knowledge_base_id | String(36) FK | 知识库 ID |
| binding_type | String(32) | `"explicit"` / `"auto_matched"` |
| priority | Integer | 优先级 |

### DocumentTemplate (文档模板)

**表**: `aidp_document_templates`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) PK | UUID |
| name | String(200) | 模板名称 |
| category | String(50) | 分类: research/prd/arch/plan/dev/test/ops/meeting |
| content | Text | 模板内容 |
| variables | Text (JSON) | 模板变量列表 |
| scope | String(20) | `"global"` 或自定义 |
| project_id | Integer FK | 关联项目 |
| user_id | String(100) | 创建者 |
| is_active | Boolean | 是否启用 |

### KnowledgeSearchLog (搜索日志)

**表**: `aidp_knowledge_search_logs`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) PK | UUID |
| base_id | String(36) | 知识库 ID |
| query | Text | 搜索查询 |
| results_count | Integer | 结果数 |
| top_score | Float | 最高分 |
| duration_ms | Float | 耗时 |

## API 端点

### 知识库 (KnowledgeBase)

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/knowledge/bases` | GET | scope_read_access | 列出知识库 (支持 project_id, search 过滤) |
| `/api/knowledge/bases` | POST | `knowledge:write` | 创建知识库 |
| `/api/knowledge/bases/{base_id}` | GET | scope_read_access | 获取知识库详情 (含 children, parent) |
| `/api/knowledge/bases/{base_id}` | PUT | `knowledge:write` | 更新知识库 |
| `/api/knowledge/bases/{base_id}` | DELETE | `knowledge:delete` | 软删除知识库 |

### 文档 (KnowledgeDocument)

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/knowledge/documents-list` | GET | scope_read_access | 全局文档列表 (支持 base_id, doc_type, category, status, search 过滤) |
| `/api/knowledge/documents` | POST | `knowledge:write` | 独立创建文档 (无需 base_id) |
| `/api/knowledge/bases/{base_id}/documents` | GET | scope_read_access | 列出知识库下的文档 |
| `/api/knowledge/bases/{base_id}/documents` | POST | `knowledge:write` | 在知识库下创建文档 |
| `/api/knowledge/documents/{doc_id}` | GET | scope_read_access | 获取文档详情 (含 content) |
| `/api/knowledge/documents/{doc_id}` | PUT | `knowledge:write` | 更新文档 (标题/内容/分类/推广状态) |
| `/api/knowledge/documents/{doc_id}` | DELETE | `knowledge:delete` | 软删除文档 |
| `/api/knowledge/documents/{doc_id}/chunks` | GET | scope_read_access | 获取文档分块列表 |

### 搜索

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/knowledge/search` | POST | scope_read_access | 关键词搜索 (title + content 全文匹配 + 评分) |
| `/api/knowledge/search/semantic` | POST | - | 语义搜索 (通过 semantic_search service) |

### 绑定

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/knowledge/bindings/{kb_id}` | GET | scope_read_access | 列出知识库的项目绑定 |
| `/api/knowledge/bindings` | POST | `knowledge:write` | 创建项目-知识库绑定 |
| `/api/knowledge/bindings/{binding_id}` | DELETE | `knowledge:delete` | 删除绑定 |

### 文档模板 (前缀 `/api/knowledge/templates`)

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/knowledge/templates/list` | GET | - | 列出模板 (支持 category, scope, search) |
| `/api/knowledge/templates/create` | POST | - | 创建模板 |
| `/api/knowledge/templates/{template_id}` | GET | - | 获取模板详情 |
| `/api/knowledge/templates/{template_id}/render` | POST | - | 渲染模板 (替换 `{{key}}`) |
| `/api/knowledge/templates/{template_id}` | DELETE | - | 禁用模板 |
| `/api/knowledge/templates/stats` | GET | - | 模板统计 |

### 网页导入

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/knowledge/import-web/analyze` | POST | - | 分析 URL |
| `/api/knowledge/import-web/direct-import` | POST | - | 从 URL 直接导入到知识库 |

### 统计

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/knowledge/stats` | GET | scope_read_access | 获取知识库统计 (total_bases, total_documents) |

## 访问隔离

知识库 (KnowledgeBase) 的访问隔离 `_kb_base_filter`:
- `public` → 所有人可见
- `team` → 登录用户可见
- `private` → 仅创建者可见

文档 (KnowledgeDocument) 的访问隔离 `_kb_doc_filter`:
- 未登录 → 仅 `public` + `owner_type` 为 `team`/`system`
- 已登录 → `public`/`team` 全部 + `personal` 仅创建者

创建者校验 `_check_kb_owner`: 非创建者不能修改他人的 personal/private 内容。

## 数据关系图

```
aidp_projects (1) ----< aidp_knowledge_bases (N)
aidp_knowledge_bases (1) ----< aidp_knowledge_documents (N)
aidp_knowledge_bases (1) ----< aidp_knowledge_bases (自引用 parent_id)
aidp_knowledge_documents (1) ----< aidp_document_chunks (N)
aidp_knowledge_bases (1) ----< aidp_project_knowledge_bindings (N)
aidp_knowledge_bases (1) ----< aidp_knowledge_search_logs (N)
aidp_projects (1) ----< aidp_document_templates (N)
```