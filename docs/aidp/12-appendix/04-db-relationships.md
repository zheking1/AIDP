# 数据库 ER 关系图

## 数据库清单

AIDP 使用 6 个独立数据库:

| 数据库 | 类型 | 用途 |
|--------|------|------|
| aidp | PostgreSQL 16 + pgvector | Controller 主数据库 (核心表 + 模块表) |
| skill_manager | PostgreSQL + pgvector | Skill Router 独立数据库 |
| code_index | SQLite | 代码索引工具 (AST 节点/边) |
| memory | SQLite | 记忆工具 (记忆/关系) |
| knowledge | SQLite | 知识库工具 (文档/分块) |
| doc_index | SQLite | 文档索引工具 (章节/代码引用) |

---

## 一、PostgreSQL aidp (主数据库) - 完整 ER

### 认证与系统表

```
users ──< user_sessions (1:N, CASCADE)
users ──< api_keys (1:N, CASCADE)
users ──< login_logs (1:N)
users ──< audit_logs (1:N)
permissions ──< role_permissions (1:N, CASCADE)
```

### 项目表 (中心枢纽)

```
aidp_projects (PK: id) ──< aidp_project_members (1:N)
aidp_projects ──< aidp_project_settings (1:1, unique)
aidp_projects ──< aidp_project_access_logs (1:N)
aidp_projects ──< aidp_project_mappings (1:N)
aidp_projects ──< aidp_project_init_tasks (1:N)
aidp_projects ──< aidp_knowledge_bases (1:N)
aidp_projects ──< aidp_memory_entries (1:N)
aidp_projects ──< aidp_skills (1:N)
aidp_projects ──< aidp_skill_groups (1:N)
aidp_projects ──< aidp_rules (1:N)
aidp_projects ──< aidp_rule_groups (1:N)
aidp_projects ──< aidp_agents (1:N)
aidp_projects ──< aidp_workflows (1:N)
aidp_projects ──< aidp_assets (1:N)
aidp_projects ──< aidp_document_templates (1:N)
aidp_projects ──< aidp_context_packages (1:N)
```

### 工具注册

```
tool_registry (独立)
tool_invocation (独立)
```

### 模型管理

```
aidp_models (独立)
```

### Knowledge 模块内部关系

```
aidp_knowledge_bases ──< aidp_knowledge_bases (自引用 parent_id, 1:N)
aidp_knowledge_bases ──< aidp_knowledge_documents (1:N)
aidp_knowledge_documents ──< aidp_document_chunks (1:N)
aidp_knowledge_bases ──< aidp_project_knowledge_bindings (1:N)
aidp_knowledge_bases ──< aidp_knowledge_search_logs (1:N)
```

### Memory 模块内部关系

```
aidp_memory_entries ──< aidp_memory_entries (自引用 parent_id, 1:N)
aidp_memory_entries(FK source_id) ──< aidp_memory_relations (1:N)
aidp_memory_entries(FK target_id) ──< aidp_memory_relations (1:N)
aidp_memory_entries ──< aidp_memory_access_logs (1:N)
```

### Skills 模块内部关系

```
aidp_skill_groups ──< aidp_skill_groups (自引用 parent_id, 1:N)
aidp_skill_groups ──< aidp_skills (1:N)
aidp_skills ──< aidp_skill_files (1:N, CASCADE)
aidp_skills ──< aidp_skill_evolutions (1:N, CASCADE)
```

### Rules 模块内部关系

```
aidp_rule_groups ──< aidp_rule_groups (自引用 parent_id, 1:N)
aidp_rule_groups ──< aidp_rules (1:N)
```

### Agents 模块内部关系 (多对多)

```
aidp_agents ──< aidp_agent_skills >── aidp_skills (M:N, CASCADE)
aidp_agents ──< aidp_agent_rules >── aidp_rules (M:N, CASCADE)
aidp_agents ──< aidp_agent_knowledge >── aidp_knowledge_bases (M:N, CASCADE)
aidp_agents ──< aidp_agents (自引用 parent_agent_id, 1:N)
```

### Workflows 模块内部关系

```
aidp_workflows ──< aidp_workflow_steps (1:N, CASCADE)
aidp_workflows ──< aidp_workflow_executions (1:N)
aidp_workflow_executions ──< aidp_workflow_execution_steps (1:N, CASCADE)
aidp_agents ──< aidp_workflow_steps (1:N, FK agent_id)
```

### Assets 模块内部关系

```
aidp_assets ──< aidp_asset_tags (1:N, CASCADE ON DELETE)
```

---

## 二、PostgreSQL skill_manager

Skill Router 使用独立的 PostgreSQL 数据库存储 skills/rules/skill_executions，含 pgvector 向量扩展。

---

## 三、SQLite code-index (data/code_index.db)

```
nodes (PK: id)
  ├── project_id, file_path, name, type
  └── line_start, line_end
edges (PK: id)
  ├── FK: source_node_id, target_node_id -> nodes.id
  └── relation_type (calls/extends/imports)
symbols (PK: id)
  └── node_id, name, kind (function/class/variable)
```

---

## 四、SQLite memory-tool (data/memory.db)

```
memories (PK: id)
  └── project_id, title, content, category, embedding
memory_tags (PK: id)
  └── FK: memory_id -> memories.id
memory_relations (PK: id)
  ├── FK: source_id -> memories.id
  ├── FK: target_id -> memories.id
  └── relation_type, strength
```

---

## 五、SQLite knowledge-tool (data/knowledge.db)

```
knowledge_bases (PK: id)
  └── name, project_id, chunking_config
documents (PK: id)
  ├── FK: kb_id -> knowledge_bases.id
  └── title, content, file_path, mime_type
chunks (PK: id)
  ├── FK: document_id -> documents.id
  └── content, embedding, chunk_index
```

---

## 六、SQLite doc-index (data/doc_index.db)

```
doc_nodes (PK: id)
  └── project_id, title, path, content_type
doc_sections (PK: id)
  ├── FK: doc_id -> doc_nodes.id
  ├── FK: parent_id -> doc_sections.id
  └── heading_level, title, content
code_references (PK: id)
  ├── FK: section_id -> doc_sections.id
  └── file_path, line_range, symbol_name
```

---

## 跨数据库映射

```
aidp_project_mappings (PostgreSQL aidp)
  ├── controller_project_id -> aidp_projects.id
  ├── tool_name: "code-index"      -> code-index SQLite 的 project_id
  ├── tool_name: "skillrouter"     -> skill_manager PostgreSQL 的 project_id
  └── tool_name: "knowledge-tool"  -> knowledge-tool SQLite 的 project_id
```

Controller 通过 HTTP REST 调用各工具的 `/tool/invoke` 端点获取数据，`aidp_project_mappings` 记录跨数据库的 ID 对应关系。

## 完整关系汇总

| 父表 | 子表 | 类型 | 数据库 |
|------|------|------|--------|
| users | user_sessions | 1:N | aidp |
| users | api_keys | 1:N | aidp |
| users | login_logs | 1:N | aidp |
| users | audit_logs | 1:N | aidp |
| aidp_projects | project_members | 1:N | aidp |
| aidp_projects | project_settings | 1:1 | aidp |
| aidp_projects | knowledge_bases | 1:N | aidp |
| aidp_projects | memory_entries | 1:N | aidp |
| aidp_projects | skills | 1:N | aidp |
| aidp_projects | rules | 1:N | aidp |
| aidp_projects | agents | 1:N | aidp |
| aidp_projects | workflows | 1:N | aidp |
| aidp_projects | assets | 1:N | aidp |
| knowledge_bases | knowledge_documents | 1:N | aidp |
| knowledge_documents | document_chunks | 1:N | aidp |
| memory_entries | memory_relations | 1:N | aidp |
| skill_groups | skills | 1:N | aidp |
| skills | skill_files | 1:N | aidp |
| skills | skill_evolutions | 1:N | aidp |
| rule_groups | rules | 1:N | aidp |
| agents | agent_skills | M:N | aidp |
| agents | agent_rules | M:N | aidp |
| agents | agent_knowledge | M:N | aidp |
| workflows | workflow_steps | 1:N | aidp |
| workflows | workflow_executions | 1:N | aidp |
| workflow_executions | execution_steps | 1:N | aidp |
| assets | asset_tags | 1:N | aidp |