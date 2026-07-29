# Knowledge Tool — 完整设计与开发计划

## 文档信息

| 属性 | 值 |
|------|-----|
| 版本 | v2.0 |
| 创建日期 | 2026-07-07 |
| 最后更新 | 2026-07-07 |
| 优先级 | P0 (最高) |
| 预估工时 | 4 周 |
| 状态 | 开发中 |

---

## 1. 设计目标

构建一个**生产级文档知识库管理与检索系统**，核心解决3个问题：

| 问题 | 当前状态 | 目标 |
|------|---------|------|
| **知识无层级** | 文档平铺在 `workspace_id` + `project_id` 字符串上 | framework → template → project 三层知识体系 |
| **项目无法匹配知识库** | 无关联表，靠字符串约定 | ProjectKnowledgeBinding 显式+隐式+自动绑定 |
| **检索带入大量噪音** | 全量chunk搜索，无LLM过滤 | 2-step检索：元数据过滤向量搜索 → Reranker精选 |

---

## 2. 三层知识体系

### 2.1 架构概览

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: 框架级知识 (Framework Knowledge)               │
│  kb_level = "framework", parent = null                   │
│  ─────────────────────────────────────────────────────  │
│  通用框架/库的官方知识，跨所有项目共享                       │
│  例: Spring Boot, MyBatis-Plus, Nacos, Sa-Token          │
│  可见性: public (全平台)                                  │
└─────────────────────────────────────────────────────────┘
                          ▲ 继承
┌─────────────────────────────────────────────────────────┐
│  Layer 2: 模板级知识 (Template Knowledge)                 │
│  kb_level = "template", parent = framework_kb             │
│  ─────────────────────────────────────────────────────  │
│  框架的特定实现/脚手架约定                                 │
│  例: ruoyi-cloud-plus, Spring-Cloud-Microservice         │
│  可见性: public 或 workspace                              │
└─────────────────────────────────────────────────────────┘
                          ▲ 继承
┌─────────────────────────────────────────────────────────┐
│  Layer 3: 项目级知识 (Project Knowledge)                  │
│  kb_level = "project", parent = template_kb               │
│  ─────────────────────────────────────────────────────  │
│  具体项目的私有业务知识                                     │
│  例: my-erp-system, my-crm-system                        │
│  可见性: private (仅项目成员)                              │
└─────────────────────────────────────────────────────────┘
```

### 2.2 具体示例：ruoyi-cloud-plus

```
spring-boot (framework)
  domains: [orm, web, security, config]
  tech_stack: [java, spring-boot, maven]
    │
    └── ruoyi-cloud-plus (template)
        domains: [system, auth, generator, monitor]
        tech_stack: [java, spring-boot, mybatis-plus, nacos, sa-token, ruoyi]
          │
          ├── ruoyi-auth (template, sub-module)
          │   domains: [auth, oauth, security]
          │   keywords: [Sa-Token, JWT, OAuth2, 微信, 社交登录]
          │
          ├── ruoyi-system (template, sub-module)
          │   domains: [system, user, role, menu]
          │   keywords: [RBAC, BaseEntity, CRUD, 数据权限]
          │
          ├── ruoyi-generator (template, sub-module)
          │   domains: [codegen, template]
          │   keywords: [代码生成, Velocity, 表结构]
          │
          ├── my-erp-system (project, parent=ruoyi-cloud-plus)
          │   domains: [erp, procurement, finance]
          │   kb_level: project
          │
          └── my-crm-system (project, parent=ruoyi-cloud-plus)
              domains: [crm, customer, sales]
              kb_level: project
```

---

## 3. 项目→知识库匹配机制

### 3.1 三级绑定

```
┌─────────────────────────────────────────────────────────────┐
│  绑定方式           │  触发条件           │  优先级          │
├─────────────────────────────────────────────────────────────┤
│  explicit (显式)    │  管理员手动选择      │  100            │
│  inherited (继承)   │  通过 parent_id 链   │  50             │
│  auto_matched (自动)│  tech_stack 标签匹配  │  10             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 自动匹配流程

```
项目: my-erp-system
  tech_stack: [java, spring-boot, mybatis-plus, nacos, ruoyi]

  Step 1: 显式绑定
    my-erp-system → ruoyi-cloud-plus (binding_type=explicit)

  Step 2: 继承链 (parent_id)
    ruoyi-cloud-plus.parent → spring-boot (binding_type=inherited)

  Step 3: 技术栈自动匹配
    tech_stack 包含 "mybatis-plus" → mybatis-plus知识库 (auto_matched)
    tech_stack 包含 "nacos"        → nacos知识库 (auto_matched)

  最终绑定列表 (按优先级排序):
    1. my-erp-system      (project,   priority=200)
    2. ruoyi-cloud-plus   (template,  priority=100)
    3. spring-boot         (framework, priority=50)
    4. mybatis-plus        (framework, priority=10)
    5. nacos               (framework, priority=10)
```

---

## 4. 优化检索管线（2-step, 0次LLM）

### 4.1 管线总览

```
aidp_context(project="my-erp", task="添加微信登录")
    │
    ▼
Step 0: 准备工作 (复用已有数据, ~0ms)
    │  project_bindings → relevant_kb_ids [my-erp, ruoyi, spring-boot, ...]
    │  Stage 1 intent → task_domains: [auth, oauth]
    │  Stage 1 intent → tech_keywords: [微信, OAuth2, Sa-Token]
    │
    ▼
Step 1: 元数据过滤 + 层级向量搜索 (单次SQL, ~100ms)
    │  ┌─────────────────────────────────────────────────────┐
    │  │ 1a. 文档摘要索引 (先搜文档，缩小范围)               │
    │  │     WHERE kb_id IN ($relevant_kb_ids)                │
    │  │       AND kb.domains ?| $task_domains                │
    │  │     ORDER BY summary_embedding <=> $query_vec        │
    │  │     LIMIT 10                                         │
    │  │                                                      │
    │  │ 1b. Chunk索引 (仅搜匹配文档的chunks)                 │
    │  │     WHERE document_id IN ($matched_doc_ids)           │
    │  │     ORDER BY chunk_embedding <=> $query_vec          │
    │  │     LIMIT 30                                         │
    │  └─────────────────────────────────────────────────────┘
    │  产出: 30 候选 chunks
    │
    ▼
Step 2: Cross-Encoder Reranker 精选 (1次批量推理, ~50ms)
    │  ┌─────────────────────────────────────────────────────┐
    │  │ bge-reranker-v2-m3(query, 30_chunks)                │
    │  │                                                      │
    │  │ → 过滤: score < 0.5 的丢弃                          │
    │  │ → 排序: score 降序                                  │
    │  │ → 截断: token_budget 控制                           │
    │  │ → 去重: 高层覆盖低层 (同主题取项目级 > 模板级)       │
    │  └─────────────────────────────────────────────────────┘
    │  产出: 5-8 精选 chunks, ~2000 tokens
    │
    ▼
上下文: [Knowledge: 5 chunks, 1800 tokens]  ← 精准、紧凑
```

### 4.2 为什么用 Reranker 而非 LLM 裁判

| | LLM 裁判 | Reranker (bge-v2-m3) |
|---|---|---|
| **30个chunk耗时** | ~1500ms | **~50ms** (30x快) |
| **准确度** | 中 (不稳定) | **高** (专门训练) |
| **成本** | 高 (API调用) | **零** (本地推理) |
| **调用方式** | N次串行 | 1次批量 |
| **部署** | 大模型API | 568M参数, 2G内存 |
| **MTEB排名** | — | Reranking top-3 |

### 4.3 跨层去重

```
规则: 同一主题的知识，高层级的覆盖低层级

例: "用户认证配置"
  spring-boot: "用 Spring Security 配置认证"  → 保留 (无覆盖)
  ruoyi:       "用 Sa-Token 替代 Security"     → 覆盖 spring-boot 的
  my-erp:      "Sa-Token + 微信OAuth2"         → 最终保留

结果: 只保留 my-erp 的认证配置，框架级/模板级的不再重复
```

---

## 5. 数据模型

### 5.1 新增: KnowledgeBase

```python
class KnowledgeBase(Base):
    __tablename__ = "kt_knowledge_bases"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(128), nullable=False)          # "ruoyi-cloud-plus"
    slug = Column(String(128), unique=True, nullable=False)
    description = Column(Text)
    
    # ★ 核心: 层级类型
    kb_level = Column(String(32), nullable=False)        # framework | template | project
    
    # ★ 核心: 继承链 (parent_id)
    parent_id = Column(String(36), ForeignKey("kt_knowledge_bases.id"), nullable=True)
    
    # ★ 核心: 领域标注 (用于KB筛选)
    domains = Column(JSONB, default=list)               # ["auth","oauth","security"]
    keywords = Column(JSONB, default=list)              # ["Sa-Token","JWT","OAuth2"]
    tech_stack = Column(JSONB, default=list)            # ["java","spring-boot"]
    
    # 可见性
    visibility = Column(String(20), default="private")  # private | workspace | public
    owner_id = Column(String(128))
    
    # 索引默认配置
    chunk_size = Column(Integer, default=512)
    overlap_size = Column(Integer, default=50)
    embedding_model = Column(String(128), default="text-embedding-3-small")
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime(timezone=True))
```

### 5.2 新增: ProjectKnowledgeBinding

```python
class ProjectKnowledgeBinding(Base):
    __tablename__ = "kt_project_knowledge_bindings"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    project_id = Column(String(128), nullable=False)    # AIDP Project ID (来自Controller)
    knowledge_base_id = Column(String(36), ForeignKey("kt_knowledge_bases.id"), nullable=False)
    
    binding_type = Column(String(32), default="auto_matched")  # explicit | inherited | auto_matched
    priority = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
```

### 5.3 改造: KtDocument

```python
class KtDocument(Base):
    __tablename__ = "kt_document"
    
    # ... 现有字段 ...
    
    # ★ 替换: workspace_id/project_id → knowledge_base_id
    # workspace_id = Column(String(128), nullable=False)  ← 保留作为兼容
    # project_id = Column(String(128))                    ← 保留作为兼容
    knowledge_base_id = Column(String(36), ForeignKey("kt_knowledge_bases.id"))
    
    # ★ 新增: 文档摘要 (用于层级检索的摘要索引)
    summary = Column(Text)
    summary_embedding = Column(Text)  # 摘要的向量，JSON string of float[]
```

### 5.4 改造: KtDocumentChunk

```python
class KtDocumentChunk(Base):
    # ... 现有字段 ...
    # knowledge_base_id 从文档继承 (通过 JOIN 获取，不单独存)
```

---

## 6. API 设计

### 6.1 知识库管理

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/knowledge-bases` | 列表 (filter: kb_level, parent_id, visibility) |
| POST | `/api/knowledge-bases` | 创建知识库 |
| GET | `/api/knowledge-bases/{id}` | 详情 + 子KB列表 + 文档数量 |
| PUT | `/api/knowledge-bases/{id}` | 更新 (name, domains, keywords等) |
| DELETE | `/api/knowledge-bases/{id}` | 删除 (级联删除关联) |

### 6.2 项目绑定管理

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/knowledge-bases/{id}/bindings` | KB的项目绑定列表 |
| POST | `/api/projects/bindings` | 创建绑定 (project_id, kb_id, binding_type) |
| DELETE | `/api/projects/bindings/{id}` | 删除绑定 |
| GET | `/api/projects/{project_id}/knowledge-bases` | 获取项目的所有KB (含继承+自动) |
| POST | `/api/projects/{project_id}/auto-match` | 触发自动匹配 |

### 6.3 文档管理 (改造)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/documents` | 创建文档 (新增 knowledge_base_id) |
| GET | `/api/documents` | 列表 (新增 kb_id 过滤) |

### 6.4 优化检索 (改造)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/knowledge/search` | 元数据过滤向量搜索 |
| POST | `/api/knowledge/search/rerank` | Reranker 重排 (内部调用) |

---

## 7. aidp_context 管线改造

### 7.1 StagedRetriever 修改

```python
# 当前 (有问题的)
payload = {
    "trace_id": "",
    "capability": "knowledge.search",
    "context": {},                          # ← 空!
    "input": {"query": query_text, "top_k": limit}
}

# 改造后
payload = {
    "trace_id": trace_id,
    "capability": "knowledge.search",
    "context": {
        "workspace_id": workspace_id,        # ★ 从Stage 0传入
        "project_id": project_id,            # ★ 从Stage 0传入
        "knowledge_base_ids": kb_ids,        # ★ 项目绑定的KB列表
        "task_domains": task_domains,        # ★ Stage 1意图分析产出的领域
        "tech_keywords": tech_keywords,      # ★ Stage 1意图分析产出的关键词
    },
    "input": {
        "query": query_text,
        "top_k": limit,
        "search_mode": "hybrid",
        "enable_rerank": True,              # ★ 启用 reranker
    }
}
```

### 7.2 改造点汇总

| 组件 | 改动 | 优先级 |
|------|------|--------|
| `staged_retriever.py` | 传递 project_id, kb_ids, domains | P0 |
| `classification_service.py` (skill-router) | 产出 task_domains, tech_keywords | P0 |
| `tool.py` (knowledge-tool) | 接收 context, 执行元数据过滤搜索 | P0 |
| `search_service.py` | 实现真正的向量搜索 + reranker | P0 |

---

## 8. Web UI 设计

### 8.1 布局

```
┌─────────────────────────────────────────────────────────────┐
│  📁 知识库列表          │  📄 文档管理                      │
│  ─────────────────────  │  ───────────────────────────────  │
│  + 新建知识库           │  [卡片 ▼] [筛选 ▼] [排序 ▼]       │
│                         │  ┌─────────────────────────────┐  │
│  ▼ 框架级               │  │ 🔍 搜索文档...              │  │
│  ├─ 📦 spring-boot      │  └─────────────────────────────┘  │
│  ├─ 📦 mybatis-plus     │                                   │
│  │                      │  ┌──────────┐ ┌──────────┐       │
│  ▼ 模板级               │  │ 📄 Doc 1 │ │ 📄 Doc 2 │       │
│  ├─ 📦 ruoyi-...        │  │ [kb:ruoyi]│ │ [kb:erp] │       │
│  │  ├─ 📦 ruoyi-auth    │  │ ✅已索引  │ │ 🔄处理中 │       │
│  │  ├─ 📦 ruoyi-system  │  └──────────┘ └──────────┘       │
│  │  └─ 📦 ruoyi-gen     │                                   │
│  │                      │  知识库详情:                        │
│  ▼ 项目级               │  ┌─────────────────────────────┐  │
│  ├─ 📦 my-erp-system    │  │ 级别: 项目级                 │  │
│  │  ├─ 📂 API文档       │  │ 父KB: ruoyi-cloud-plus      │  │
│  │  ├─ 📂 ER图          │  │ 领域: [erp, procurement]    │  │
│  │  └─ 📂 部署文档      │  │ 文档数: 23 | 已索引: 20     │  │
│  └─ 📦 my-crm-system    │  └─────────────────────────────┘  │
│                         │                                   │
│  🏷️ 领域标签:           │  继承链:                          │
│  #auth #security        │  spring-boot → ruoyi → my-erp     │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 新增页面

| 页面 | 路由 | 功能 |
|------|------|------|
| KB管理 | `/knowledge-bases` | 三层树形结构 + CRUD |
| KB详情 | `/knowledge-bases/{id}` | 领域标签、继承链、绑定项目、文档列表 |
| 项目绑定 | `/projects/{id}/knowledge` | 管理项目的KB绑定，触发自动匹配 |
| 检索测试 | `/search` | 完整检索管线测试入口 |
| 检索结果 | `/search/results` | Reranker前后对比、分块高亮 |

### 8.3 组件树

```
tools/knowledge-tool/app/web/
├── static/
│   ├── css/knowledge.css
│   └── js/
│       ├── kb-tree.js         # 知识库树形组件
│       ├── search.js          # 检索管线前端
│       └── graph.js           # 可视化
│
├── templates/
│   ├── layouts/base.html
│   ├── pages/
│   │   ├── dashboard.html
│   │   ├── documents.html
│   │   ├── document-detail.html
│   │   ├── knowledge-bases.html       # ★ 新增
│   │   ├── knowledge-base-detail.html  # ★ 新增
│   │   ├── project-bindings.html       # ★ 新增
│   │   ├── search.html
│   │   └── upload.html
│   └── components/
│       ├── kb-tree.html
│       ├── inheritance-chain.html      # ★ 新增: 继承链可视化
│       └── domain-tags.html            # ★ 新增: 领域标签编辑器
```

---

## 9. 开发任务拆分

### Phase 0: 数据模型 (1天)

| ID | 任务 | 产出 |
|----|------|------|
| **T0-1** | 新增 `KnowledgeBase` 模型 | `models.py` |
| **T0-2** | 新增 `ProjectKnowledgeBinding` 模型 | `models.py` |
| **T0-3** | 改造 `KtDocument` — 新增 `knowledge_base_id`, `summary`, `summary_embedding` | `models.py` |
| **T0-4** | 数据库迁移脚本 + `init_db.py` 更新 | `init_db.py` |

### Phase 1: API 层 (2天)

| ID | 任务 | 产出 |
|----|------|------|
| **T1-1** | 知识库 CRUD API (`knowledge_bases.py`) | routes |
| **T1-2** | 项目绑定 API (`bindings.py`) | routes |
| **T1-3** | 自动匹配服务 (`auto_matcher.py`) | service + route |
| **T1-4** | 文档API适配 — `knowledge_base_id` 替代 `workspace_id/project_id` | `documents.py` |
| **T1-5** | 优化检索服务 — 元数据过滤向量搜索 | `search_service.py` 重写 |
| **T1-6** | Reranker 集成 — `reranker.py` + Docker | 新service + compose |

### Phase 2: 管线集成 (1天)

| ID | 任务 | 产出 |
|----|------|------|
| **T2-1** | skill-router 产出 `task_domains` + `tech_keywords` | `classification_service.py` |
| **T2-2** | `staged_retriever.py` 传递 project context | `staged_retriever.py` |
| **T2-3** | knowledge-tool `tool/invoke` 接收新 context | `tool.py` |

### Phase 3: Web UI (2-3天)

| ID | 任务 | 产出 |
|----|------|------|
| **T3-1** | KB管理页面 — 三层树 + CRUD | `knowledge-bases.html` |
| **T3-2** | KB详情 — 领域标签编辑、继承链展示 | `knowledge-base-detail.html` |
| **T3-3** | 项目绑定管理页面 | `project-bindings.html` |
| **T3-4** | 检索测试+结果页面 | `search.html` 改造 |
| **T3-5** | Controller workspace iframe 集成 | workspace路由 |

---

## 10. 验收标准

### 10.1 功能验收

- [ ] 三层知识库 (framework/template/project) 创建/编辑/删除
- [ ] 知识库父子继承链正确 (parent_id)
- [ ] 项目显式绑定 + 继承 + 自动匹配均正确
- [ ] 元数据过滤向量搜索返回结果正确 (领域+KB过滤)
- [ ] Reranker 过滤噪声，只保留相关chunk (score >= 0.5)
- [ ] 跨层去重生效 (同主题取最高层级)
- [ ] aidp_context 管线传入正确的 project/kb context
- [ ] 检索回退 (reranker不可用时使用阈值过滤)

### 10.2 性能验收

- [ ] 搜索响应 < 200ms (Step1 + Step2)
- [ ] Reranker 推理 < 60ms (30 chunks)
- [ ] KB树形结构加载 < 500ms

### 10.3 UI验收

- [ ] KB树正确展示三层结构 + 继承关系
- [ ] 项目绑定页可手动选择KB + 查看继承链
- [ ] 检索结果页展示 reranker 筛选前后对比

---

## 11. 风险评估

| 风险 | 影响 | 概率 | 缓解 |
|------|------|------|------|
| pgvector 搜索性能 | 高 | 低 | IVFFlat/HNSW 索引 |
| Reranker 首次部署失败 | 中 | 中 | 回退到阈值过滤 |
| 数据迁移兼容性 | 高 | 中 | 保留 workspace_id 字段，渐进切换 |
| 大规模知识库搜索慢 | 中 | 中 | 层级摘要索引缩小搜索空间 |

---

## 12. 参考资料

- Reranker: [BAAI/bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3)
- 向量搜索: pgvector HNSW indexing
- SkillRouter Web UI: 参考标杆

---

**文档结束**