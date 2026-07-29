# Knowledge Module — 知识库模块

## 1. 模块概述

知识库管理模块（Knowledge Module）是 AIDP 统一平台的核心数据管理模块之一，提供文档知识库的全生命周期管理能力。该模块集成了原有的 Knowledge Tool 功能，支持知识库 CRUD、文档上传与管理、自动分块处理、语义搜索以及文档模板管理。

**模块信息**:
- 名称: `knowledge`
- 版本: `1.0.0`
- 描述: 文档知识库管理，支持语义搜索和智能分块
- 启用状态: 默认启用
- 依赖: 无（推荐项目模块先加载）
- 路由前缀: `/api/knowledge`

**模块注册代码** (`apps/controller/app/modules/knowledge/__init__.py`):

```python
@register_module(name='knowledge', enabled=True)
class KnowledgeModule(BaseModule):
    name = "knowledge"
    description = "文档知识库管理，支持语义搜索和智能分块"
    version = "1.0.0"
    enabled = True
    dependencies = []

    def register_routes(self, app):
        from .routes import router as knowledge_router
        app.include_router(knowledge_router, prefix="/api/knowledge")
        from .templates_routes import router as templates_router
        app.include_router(templates_router, prefix="/api/knowledge")

    def on_startup(self):
        print(f"[KnowledgeModule] 知识库模块已启动")

    def on_shutdown(self):
        print(f"[KnowledgeModule] 知识库模块已停止")
```

---

## 2. 数据模型

### 2.1 KnowledgeBase — 知识库

**表名**: `aidp_knowledge_bases`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | String(36), PK | 主键 UUID |
| project_id | Integer, FK→aidp_projects.id | 所属项目 |
| user_id | String(100) | 创建用户 |
| name | String(200), NOT NULL | 知识库名称 |
| description | Text | 描述 |
| category | String(50), default="general" | 分类: general/research/prd/arch/plan/dev/test/ops/meeting |
| chunking_strategy | String(50), default="fixed" | 分块策略 |
| chunk_size | Integer, default=500 | 分块大小 |
| chunk_overlap | Integer, default=50 | 分块重叠量 |
| embedding_model | String(128), default="text-embedding-3-small" | 嵌入模型 |
| document_count | Integer, default=0 | 文档计数 |
| total_chunks | Integer, default=0 | 总分块数 |
| extra_data | Text, default="{}" | 扩展数据 |
| created_at | DateTime(timezone=True) | 创建时间 |
| updated_at | DateTime(timezone=True) | 更新时间 |
| deleted_at | DateTime(timezone=True), nullable | 软删除时间 |

**代码**:

```python
class KnowledgeBase(Base):
    __tablename__ = "aidp_knowledge_bases"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    project_id = Column(Integer, ForeignKey("aidp_projects.id"), nullable=True, index=True)
    user_id = Column(String(100), nullable=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), default="general", index=True)
    chunking_strategy = Column(String(50), default="fixed")
    chunk_size = Column(Integer, default=500)
    chunk_overlap = Column(Integer, default=50)
    embedding_model = Column(String(128), default="text-embedding-3-small")
    document_count = Column(Integer, default=0)
    total_chunks = Column(Integer, default=0)
    extra_data = Column(Text, default="{}")
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    documents = relationship("KnowledgeDocument", back_populates="base", cascade="all, delete-orphan")
```

### 2.2 KnowledgeDocument — 知识库文档

**表名**: `aidp_knowledge_documents`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | String(36), PK | 主键 UUID |
| base_id | String(36), FK→aidp_knowledge_bases.id | 所属知识库 |
| project_id | Integer, FK→aidp_projects.id | 所属项目 |
| user_id | String(100) | 创建用户 |
| title | String(500), NOT NULL | 文档标题 |
| source_type | String(50), default="manual" | 来源类型 |
| source_uri | String(1000) | 来源 URI |
| content | Text | 文档内容 |
| mime_type | String(100) | MIME 类型 |
| file_size | Integer, default=0 | 文件大小 |
| chunk_count | Integer, default=0 | 分块数 |
| processing_status | String(20), default="pending" | 处理状态 |
| extra_data | Text, default="{}" | 扩展数据 |
| created_at | DateTime(timezone=True) | 创建时间 |
| updated_at | DateTime(timezone=True) | 更新时间 |
| deleted_at | DateTime(timezone=True), nullable | 软删除时间 |

**代码**:

```python
class KnowledgeDocument(Base):
    __tablename__ = "aidp_knowledge_documents"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    base_id = Column(String(36), ForeignKey("aidp_knowledge_bases.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("aidp_projects.id"), nullable=True, index=True)
    user_id = Column(String(100), nullable=True, index=True)
    title = Column(String(500), nullable=False)
    source_type = Column(String(50), default="manual")
    source_uri = Column(String(1000), nullable=True)
    content = Column(Text, nullable=True)
    mime_type = Column(String(100), nullable=True)
    file_size = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)
    processing_status = Column(String(20), default="pending", index=True)
    extra_data = Column(Text, default="{}")
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    base = relationship("KnowledgeBase", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
```

### 2.3 DocumentChunk — 文档分块

**表名**: `aidp_document_chunks`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | String(36), PK | 主键 UUID |
| document_id | String(36), FK→aidp_knowledge_documents.id | 所属文档 |
| base_id | String(36), FK→aidp_knowledge_bases.id | 所属知识库 |
| chunk_index | Integer, NOT NULL | 分块序号 |
| content | Text, NOT NULL | 分块内容 |
| embedding | Text | 向量嵌入(JSON) |
| token_count | Integer, default=0 | Token 数 |
| extra_data | Text, default="{}" | 扩展数据 |
| created_at | DateTime(timezone=True) | 创建时间 |

**代码**:

```python
class DocumentChunk(Base):
    __tablename__ = "aidp_document_chunks"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    document_id = Column(String(36), ForeignKey("aidp_knowledge_documents.id"), nullable=False, index=True)
    base_id = Column(String(36), ForeignKey("aidp_knowledge_bases.id"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Text, nullable=True)
    token_count = Column(Integer, default=0)
    extra_data = Column(Text, default="{}")
    created_at = Column(DateTime(timezone=True), default=utcnow)

    document = relationship("KnowledgeDocument", back_populates="chunks")
```

### 2.4 KnowledgeSearchLog — 搜索日志

**表名**: `aidp_knowledge_search_logs`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | String(36), PK | 主键 UUID |
| base_id | String(36) | 知识库 ID |
| project_id | Integer | 项目 ID |
| user_id | String(100) | 用户 ID |
| query | Text, NOT NULL | 搜索查询 |
| results_count | Integer, default=0 | 结果数 |
| top_score | Float | 最高分 |
| duration_ms | Float | 耗时(ms) |
| created_at | DateTime(timezone=True) | 创建时间 |

**代码**:

```python
class KnowledgeSearchLog(Base):
    __tablename__ = "aidp_knowledge_search_logs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    base_id = Column(String(36), nullable=True, index=True)
    project_id = Column(Integer, nullable=True, index=True)
    user_id = Column(String(100), nullable=True)
    query = Column(Text, nullable=False)
    results_count = Column(Integer, default=0)
    top_score = Column(Float, nullable=True)
    duration_ms = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
```

### 2.5 DocumentTemplate — 文档模板

**表名**: `aidp_document_templates`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | String(36), PK | 主键 UUID |
| name | String(200), NOT NULL | 模板名称 |
| category | String(50), NOT NULL | 分类: research/prd/arch/plan/dev/test/ops/meeting |
| content | Text, NOT NULL | 模板内容 |
| variables | Text, default="[]" | 变量定义(JSON) |
| scope | String(20), default="global" | 作用域 |
| project_id | Integer, FK→aidp_projects.id | 项目 ID |
| user_id | String(100) | 用户 ID |
| description | Text | 描述 |
| is_active | Boolean, default=True | 是否启用 |
| created_at | DateTime(timezone=True) | 创建时间 |
| updated_at | DateTime(timezone=True) | 更新时间 |

**代码**:

```python
class DocumentTemplate(Base):
    __tablename__ = "aidp_document_templates"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(200), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)
    content = Column(Text, nullable=False)
    variables = Column(Text, default="[]")
    scope = Column(String(20), default="global", index=True)
    project_id = Column(Integer, ForeignKey("aidp_projects.id"), nullable=True, index=True)
    user_id = Column(String(100), nullable=True, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
```

---

## 3. API 端点

### 3.1 知识库路由 (`/api/knowledge`)

| 方法 | 路径 | 权限 | 功能 |
|---|---|---|---|
| GET | `/api/knowledge/bases` | 登录用户 | 知识库列表(支持 project_id/skip/limit) |
| POST | `/api/knowledge/bases` | knowledge:write | 创建知识库 |
| GET | `/api/knowledge/bases/{base_id}` | 登录用户 | 获取知识库详情 |
| DELETE | `/api/knowledge/bases/{base_id}` | knowledge:delete | 软删除知识库 |
| GET | `/api/knowledge/bases/{base_id}/documents` | 登录用户 | 获取知识库文档列表 |
| POST | `/api/knowledge/bases/{base_id}/documents` | knowledge:write | 创建文档 |
| GET | `/api/knowledge/documents/{doc_id}` | 登录用户 | 获取文档详情 |
| DELETE | `/api/knowledge/documents/{doc_id}` | knowledge:delete | 软删除文档 |
| POST | `/api/knowledge/search` | 登录用户 | 语义搜索文档 |
| GET | `/api/knowledge/stats` | 登录用户 | 知识库统计 |

**搜索接口请求体** (`SearchQuery`):

```python
class SearchQuery(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(10, ge=1, le=50)
```

### 3.2 文档模板路由 (`/api/knowledge/templates`)

| 方法 | 路径 | 权限 | 功能 |
|---|---|---|---|
| GET | `/api/knowledge/templates/list` | 登录用户 | 模板列表(支持 category/scope/search 过滤) |
| POST | `/api/knowledge/templates/create` | 登录用户 | 创建模板 |
| GET | `/api/knowledge/templates/{template_id}` | 登录用户 | 获取模板详情(含完整 content) |
| POST | `/api/knowledge/templates/{template_id}/render` | 登录用户 | 渲染模板(变量替换) |
| DELETE | `/api/knowledge/templates/{template_id}` | 登录用户 | 禁用模板(软删除, is_active=false) |
| GET | `/api/knowledge/templates/stats` | 登录用户 | 模板统计 |

**渲染接口**:

```python
class TemplateRender(BaseModel):
    variables: dict = Field(default_factory=dict)
```

渲染逻辑: 遍历模板的 variables 定义，将 `{{key}}` 替换为传入的变量值，缺失的变量使用 default 值替代。

---

## 4. 前端

### 4.1 模板文件

- **主模板**: `modules/knowledge/bases.html` (父页面)
- **内容面板**: `modules/knowledge/bases_content.html` (188 行，核心 UI)

### 4.2 Alpine.js 组件

**函数名**: `knowledgeBasesPage()`

**状态**:

```javascript
{
    knowledgeBases: [],        // 知识库列表
    searchQuery: '',           // 搜索关键字
    showCreateModal: false,    // 创建模态框开关
    loading: false,            // 加载状态
    stats: {},                 // 统计数据
    newKB: {                   // 创建表单数据
        name: '',
        description: '',
        chunking_strategy: 'fixed',
        chunk_size: 500
    }
}
```

**方法**:

| 方法 | 功能 |
|---|---|
| `init()` | 初始化，同时调用 loadKnowledgeBases() 和 loadStats() |
| `loadKnowledgeBases()` | GET `/api/knowledge/bases?search=...` 加载列表 |
| `loadStats()` | GET `/api/knowledge/stats` 加载统计 |
| `createKnowledgeBase()` | POST `/api/knowledge/bases` 创建知识库 |
| `viewKnowledgeBase(kb)` | 查看知识库（当前为 alert） |

### 4.3 关键 UI 布局

```
┌─────────────────────────────────────────────────┐
│  页头: 标题「知识库」+ 副标题 + 「创建知识库」按钮    │
├─────────────────────────────────────────────────┤
│  统计卡片 (4列栅格)                               │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐          │
│  │ 知识库 │ │ 文档  │ │ 待处理 │ │ 搜索  │          │
│  └──────┘ └──────┘ └──────┘ └──────┘          │
├─────────────────────────────────────────────────┤
│  搜索栏 (带搜索图标, 300ms 防抖)                  │
├─────────────────────────────────────────────────┤
│  列表: 每行显示图标 + 名称 + 描述 + 文档数         │
│  空状态: 引导创建第一个知识库                     │
│  加载中: 旋转动画                                │
├─────────────────────────────────────────────────┤
│  创建模态框: 名称 / 描述 / 分块策略 / 分块大小     │
└─────────────────────────────────────────────────┘
```

---

## 5. 核心流程

### 5.1 知识库 CRUD

```
创建: POST /api/knowledge/bases
  → 校验 BaseCreate (name, description, chunking_strategy, chunk_size, chunk_overlap, embedding_model)
  → require_permissions("knowledge:write")
  → 创建 KnowledgeBase 实例 → db.commit → 返回 to_dict()

读取: GET /api/knowledge/bases/{base_id}
  → 查询 id + deleted_at IS NULL
  → 404 返回 "Knowledge base not found"
  → 返回 to_dict()

删除: DELETE /api/knowledge/bases/{base_id}
  → require_permissions("knowledge:delete")
  → 软删除: 设置 deleted_at = datetime.now(timezone.utc)
  → 级联删除关联的 documents (cascade="all, delete-orphan")
```

### 5.2 文档上传与分块

```
创建文档: POST /api/knowledge/bases/{base_id}/documents
  → 校验 DocumentCreate (title, content, source_type, source_uri, mime_type)
  → require_permissions("knowledge:write")
  → 创建 KnowledgeDocument, processing_status="completed"
  → 递增知识库的 document_count
  → 返回 to_dict(include_content=True)

分块策略:
  - fixed: 按固定大小拆分 (chunk_size=500, overlap=50)
  - semantic: 语义分块 (预留, 需集成 embedding 服务)
```

### 5.3 语义搜索

```
POST /api/knowledge/search
  → 校验 SearchQuery (query, top_k)
  → 可选过滤: base_id, project_id
  → SQL LIKE 搜索: title ILIKE %query% OR content ILIKE %query%
  → 返回结果带 score=0.9 (当前为固定值, 预留 embedding 相似度)
  → 记录搜索日志 (KnowledgeSearchLog)
```

---

## 6. 模板系统

### 6.1 模板 CRUD

- **列出模板** `GET /api/knowledge/templates/list`: 支持 category/scope/search 过滤，默认 scope="global"
- **创建模板** `POST /api/knowledge/templates/create`: 需提供 name/category/content/variables
- **获取模板** `GET /api/knowledge/templates/{template_id}`: 返回完整 content（非截断）
- **删除模板** `DELETE /api/knowledge/templates/{template_id}`: 设置 is_active=false（软删除）

### 6.2 模板渲染

```
POST /api/knowledge/templates/{template_id}/render
  → 获取模板的 variables 定义 (JSON array of {key, default})
  → 遍历 variables, 将 {{key}} 替换为用户传入的值
  → 额外替换未在 variables 中定义但用户传入了的变量
  → 返回 rendered (渲染后的文本) + variables_used (使用的变量列表)

示例:
  模板内容: "项目名称: {{project_name}}, 版本: {{version}}"
  变量: [{"key": "project_name", "default": "未知"}, {"key": "version", "default": "1.0"}]
  传入: {"project_name": "AIDP"}
  输出: "项目名称: AIDP, 版本: 1.0"
```

### 6.3 分类体系

模板和知识库共用分类体系: `research / prd / arch / plan / dev / test / ops / meeting`