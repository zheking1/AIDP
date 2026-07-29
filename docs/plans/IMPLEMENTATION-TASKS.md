# Knowledge Tool — 实现任务清单

> 关联计划: `docs/plans/KNOWLEDGE-WEB-UI-PLAN.md` (v2.0)
> 开始日期: 2026-07-07

---

## Phase 0: 数据模型 (1天)

### T0-1: 新增 KnowledgeBase 模型
- [ ] 在 `models.py` 添加 `KnowledgeBase` 类
- [ ] 字段: `id`, `name`, `slug`, `description`, `kb_level`, `parent_id`, `domains`, `keywords`, `tech_stack`, `visibility`, `owner_id`, `chunk_size`, `overlap_size`, `embedding_model`, `created_at`, `updated_at`, `deleted_at`
- [ ] 自引用外键: `parent_id → kt_knowledge_bases.id`

### T0-2: 新增 ProjectKnowledgeBinding 模型  
- [ ] 在 `models.py` 添加 `ProjectKnowledgeBinding` 类
- [ ] 字段: `id`, `project_id`, `knowledge_base_id`, `binding_type`, `priority`, `created_at`

### T0-3: 改造 KtDocument 模型
- [ ] 新增 `knowledge_base_id` (FK → kt_knowledge_bases.id)
- [ ] 新增 `summary` (Text)
- [ ] 新增 `summary_embedding` (Text, JSON float array)
- [ ] 保留 `workspace_id` / `project_id` 用于向后兼容 (nullable)

### T0-4: 数据库初始化脚本更新
- [ ] 更新 `init_db.py` CREATE TABLE SQL（新增3张表）
- [ ] 添加索引: `idx_kb_parent`, `idx_kb_level`, `idx_kb_tech_stack`, `idx_binding_project`, `idx_binding_kb`, `idx_document_kb`

---

## Phase 1: SQLite 数据库迁移适配
> **重要**: knowledge-tool 使用 SQLite，但 PostgreSQL 的 JSONB/pgvector 不能直接迁移。
> 当前策略: 先用 SQLite + JSON text 列 + 简单相似度，后续迁移到 PostgreSQL + pgvector。

### T1-0: 数据库引擎确认
- [ ] 确认当前 `DATABASE_URL` 指向 SQLite
- [ ] JSONB → JSON Text 列映射（SQLite 用 TEXT 存 JSON）
- [ ] 向量嵌入暂时用 TEXT 列存 JSON string

---

## Phase 2: API 层 (2天)

### T2-1: KnowledgeBase CRUD API
- [ ] 创建 `app/api/knowledge_bases.py`
- [ ] `GET /api/knowledge-bases` — 列表 (filter: kb_level, parent_id, visibility)
- [ ] `POST /api/knowledge-bases` — 创建
- [ ] `GET /api/knowledge-bases/{id}` — 详情 (含子KB列表 + 文档数量)
- [ ] `PUT /api/knowledge-bases/{id}` — 更新
- [ ] `DELETE /api/knowledge-bases/{id}` — 软删除
- [ ] 注册路由到 `main.py`

### T2-2: ProjectBinding API
- [ ] 创建 `app/api/bindings.py`
- [ ] `GET /api/knowledge-bases/{id}/bindings` — KB绑定列表
- [ ] `POST /api/projects/bindings` — 创建绑定
- [ ] `DELETE /api/projects/bindings/{id}` — 删除绑定
- [ ] `GET /api/projects/{project_id}/knowledge-bases` — 项目所有KB (含继承+自动)
- [ ] `POST /api/projects/{project_id}/auto-match` — 触发自动匹配
- [ ] 注册路由到 `main.py`

### T2-3: 自动匹配服务
- [ ] 创建 `app/services/auto_matcher.py`
- [ ] 根据 project tech_stack 匹配 framework 级 KB
- [ ] 创建 `auto_matched` 类型绑定
- [ ] 去重检查 (已有 explicit/inherited 的不再创建 auto)

### T2-4: 文档API适配
- [ ] 修改 `documents.py` POST — 接受 `knowledge_base_id`
- [ ] 修改 `documents.py` GET — 支持 `kb_id` 过滤
- [ ] 保持 `workspace_id` / `project_id` 向后兼容

### T2-5: 优化检索服务
- [ ] 重写 `search_service.py`
- [ ] 实现元数据过滤: `WHERE kb_id IN (...) AND domains ?| task_domains`
- [ ] 实现层级摘要检索 (先搜 document summary, 再搜 chunks)
- [ ] 实现 Jaccard+词频混合评分 (临时方案, 替代 pgvector)
- [ ] 支持 search_mode: `hybrid` | `semantic` | `fts`
- [ ] 支持 context: `workspace_id`, `project_id`, `knowledge_base_ids`, `task_domains`

---

## Phase 3: 管线集成 (1天)

### T3-1: skill-router 改造
- [ ] 修改 `classification_service.py` intent analysis
- [ ] 产出 `task_domains` (任务所属领域列表)
- [ ] 产出 `tech_keywords` (技术关键词列表)

### T3-2: staged_retriever 改造
- [ ] 修改 `staged_retriever.py`
- [ ] 接收 project_id, workspace_id (从 aidp_context Stage 0)
- [ ] 查询 project knowledge bindings
- [ ] 构建完整的 context 传给 knowledge-tool
- [ ] context 包含: `workspace_id`, `project_id`, `knowledge_base_ids`, `task_domains`, `tech_keywords`

### T3-3: knowledge-tool tool/invoke 适配
- [ ] 修改 `tool.py` invoke_tool
- [ ] 从 context 提取 `knowledge_base_ids`, `task_domains`
- [ ] 传给 search_service

---

## Phase 4: Web UI (2-3天)

### T4-1: KB管理页面
- [ ] `knowledge-bases.html` — 三层树形结构 + CRUD表单
- [ ] 知识库级别标签 (framework/template/project)
- [ ] 继承链可视化 (`parent_id` 向上追溯)

### T4-2: KB详情页面
- [ ] `knowledge-base-detail.html` — 领域标签编辑器
- [ ] keywords/tech_stack 标签管理
- [ ] 绑定项目列表
- [ ] 文档数量统计

### T4-3: 项目绑定管理
- [ ] `project-bindings.html` — 绑定列表 + 管理
- [ ] 手动添加/删除绑定
- [ ] 自动匹配触发按钮
- [ ] 继承链展示

### T4-4: 检索测试页面
- [ ] `search.html` 改造 — 显示完整管线结果
- [ ] 展示: 匹配的KB → 候选chunks → 精选结果
- [ ] 过滤/截断过程可视化

---

## 验收 Checklist

- [ ] KnowledgeBase CRUD 全部正常
- [ ] 三层KB (framework→template→project) 正确创建和继承
- [ ] Project 通过显式/继承/自动方式绑定到正确KB
- [ ] 文档关联到 knowledge_base_id 正确
- [ ] 元数据过滤搜索返回结果在所选KB内
- [ ] 跨层去重生效
- [ ] aidp_context 管线传入正确 context
- [ ] KB管理 UI 三层树形结构正确
- [ ] 项目绑定管理界面功能完整