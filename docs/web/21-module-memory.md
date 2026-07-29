# Memory Module — 记忆模块

## 1. 模块概述

记忆模块（Memory Module）是 AIDP 统一平台的核心知识管理模块之一，提供项目记忆的全生命周期管理能力。该模块支持记忆条目的 CRUD 操作、三层记忆层级体系（情景/语义/程序）、记忆关系图谱构建以及语义搜索。

**模块信息**:
- 名称: `memory`
- 版本: `1.0.0`
- 描述: 项目记忆管理，支持向量搜索和记忆图谱
- 启用状态: 默认启用
- 依赖: 无
- 路由前缀: `/api/memory`

**模块注册代码** (`apps/controller/app/modules/memory/__init__.py`):

```python
@register_module(name='memory', enabled=True)
class MemoryModule(BaseModule):
    name = "memory"
    description = "项目记忆管理，支持向量搜索和记忆图谱"
    version = "1.0.0"
    enabled = True
    dependencies = []

    def register_routes(self, app):
        from .routes import router as memory_router
        app.include_router(memory_router, prefix="/api/memory")

    def on_startup(self):
        print(f"[MemoryModule] 记忆模块已启动")

    def on_shutdown(self):
        print(f"[MemoryModule] 记忆模块已停止")
```

---

## 2. 数据模型

### 2.1 MemoryEntry — 记忆条目

**表名**: `aidp_memory_entries`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | String(36), PK | 主键 UUID |
| project_id | Integer, FK→aidp_projects.id | 所属项目 |
| user_id | String(100) | 创建用户 |
| category | String(50), NOT NULL, default="other" | 分类: architecture/decision/pattern/issue/bug/other |
| memory_tier | String(20), default="semantic" | 记忆层级: episodic/semantic/procedural |
| title | String(200), NOT NULL | 标题 |
| content | Text, NOT NULL | 内容 |
| embedding | Text | 向量嵌入(JSON) |
| embedding_model | String(128), default="text-embedding-3-small" | 嵌入模型 |
| parent_id | String(36), FK→aidp_memory_entries.id | 父记忆(支持层级结构) |
| confidence_score | Float, default=1.0 | 置信度 [0.0-1.0] |
| ai_suggested | Boolean, default=False | 是否 AI 建议 |
| ai_review_status | String(20), default="approved" | AI 审核状态 |
| ai_review_comment | Text | AI 审核评论 |
| merged_from | Text | 合并来源(JSON array) |
| access_count | Integer, default=0 | 访问次数 |
| last_accessed_at | DateTime(timezone=True) | 最后访问时间 |
| source_type | String(50), default="manual" | 来源类型 |
| source_uri | String(500) | 来源 URI |
| extra_data | Text, default="{}" | 扩展数据 |
| created_at | DateTime(timezone=True) | 创建时间 |
| updated_at | DateTime(timezone=True) | 更新时间 |
| deleted_at | DateTime(timezone=True), nullable | 软删除时间 |

**代码**:

```python
class MemoryEntry(Base):
    __tablename__ = "aidp_memory_entries"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    project_id = Column(Integer, ForeignKey("aidp_projects.id"), nullable=True, index=True)
    user_id = Column(String(100), nullable=True, index=True)
    category = Column(String(50), nullable=False, index=True, default="other")
    memory_tier = Column(String(20), default="semantic", index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Text, nullable=True)
    embedding_model = Column(String(128), default="text-embedding-3-small")
    parent_id = Column(String(36), ForeignKey("aidp_memory_entries.id"), nullable=True, index=True)
    confidence_score = Column(Float, default=1.0)
    ai_suggested = Column(Boolean, default=False, index=True)
    ai_review_status = Column(String(20), default="approved")
    ai_review_comment = Column(Text, nullable=True)
    merged_from = Column(Text, nullable=True)
    access_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    source_type = Column(String(50), default="manual")
    source_uri = Column(String(500), nullable=True)
    extra_data = Column(Text, default="{}")
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    parent = relationship("MemoryEntry", remote_side="MemoryEntry.id", back_populates="children")
    children = relationship("MemoryEntry", back_populates="parent", cascade="all, delete-orphan")
    outgoing_relations = relationship("MemoryRelation", foreign_keys="MemoryRelation.source_id",
                                       back_populates="source", cascade="all, delete-orphan")
    incoming_relations = relationship("MemoryRelation", foreign_keys="MemoryRelation.target_id",
                                       back_populates="target", cascade="all, delete-orphan")
```

### 2.2 MemoryRelation — 记忆关系

**表名**: `aidp_memory_relations`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | String(36), PK | 主键 UUID |
| source_id | String(36), FK→aidp_memory_entries.id, NOT NULL | 源记忆 |
| target_id | String(36), FK→aidp_memory_entries.id, NOT NULL | 目标记忆 |
| relation_type | String(50), NOT NULL | 关系类型 |
| strength | Float, default=1.0 | 关系强度 [0.0-1.0] |
| description | Text | 关系描述 |
| extra_data | Text, default="{}" | 扩展数据 |
| created_at | DateTime(timezone=True) | 创建时间 |
| updated_at | DateTime(timezone=True) | 更新时间 |

**代码**:

```python
class MemoryRelation(Base):
    __tablename__ = "aidp_memory_relations"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    source_id = Column(String(36), ForeignKey("aidp_memory_entries.id"), nullable=False, index=True)
    target_id = Column(String(36), ForeignKey("aidp_memory_entries.id"), nullable=False, index=True)
    relation_type = Column(String(50), nullable=False, index=True)
    strength = Column(Float, default=1.0)
    description = Column(Text, nullable=True)
    extra_data = Column(Text, default="{}")
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    source = relationship("MemoryEntry", foreign_keys=[source_id], back_populates="outgoing_relations")
    target = relationship("MemoryEntry", foreign_keys=[target_id], back_populates="incoming_relations")
```

### 2.3 MemoryAccessLog — 访问日志

**表名**: `aidp_memory_access_logs`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | String(36), PK | 主键 UUID |
| memory_id | String(36), FK→aidp_memory_entries.id, NOT NULL | 记忆条目 |
| project_id | Integer, FK→aidp_projects.id | 项目 ID |
| action | String(50), NOT NULL | 操作类型 |
| query | Text | 查询内容 |
| user_id | String(100) | 用户 ID |
| ip_address | String(45) | IP 地址 |
| created_at | DateTime(timezone=True) | 创建时间 |

**代码**:

```python
class MemoryAccessLog(Base):
    __tablename__ = "aidp_memory_access_logs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    memory_id = Column(String(36), ForeignKey("aidp_memory_entries.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("aidp_projects.id"), nullable=True, index=True)
    action = Column(String(50), nullable=False)
    query = Column(Text, nullable=True)
    user_id = Column(String(100), nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
```

---

## 3. API 端点

### 3.1 路由表 (`/api/memory`)

| 方法 | 路径 | 权限 | 功能 |
|---|---|---|---|
| GET | `/api/memory/memories` | 登录用户 | 记忆列表(支持分页/分类/层级/搜索过滤) |
| POST | `/api/memory/memories` | memory:write | 创建记忆 |
| GET | `/api/memory/memories/{memory_id}` | 登录用户 | 获取记忆详情(含完整 content，递增 access_count) |
| PUT | `/api/memory/memories/{memory_id}` | memory:write | 更新记忆 |
| DELETE | `/api/memory/memories/{memory_id}` | memory:delete | 软删除记忆 |
| GET | `/api/memory/memories/{memory_id}/relations` | 登录用户 | 获取记忆的关系(出边+入边) |
| POST | `/api/memory/memories/{memory_id}/relations` | memory:write | 创建关系 |
| DELETE | `/api/memory/relations/{relation_id}` | memory:write | 删除关系 |
| POST | `/api/memory/search` | 登录用户 | 语义搜索记忆 |
| GET | `/api/memory/graph` | 登录用户 | 获取记忆图谱(节点+边) |
| GET | `/api/memory/stats` | 登录用户 | 记忆统计(总数/按分类/按层级) |

### 3.2 请求体定义

**MemoryCreate**:

```python
class MemoryCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    category: str = Field("other")
    memory_tier: str = Field("semantic")
    parent_id: Optional[str] = None
    confidence_score: float = Field(1.0, ge=0.0, le=1.0)
    source_type: str = Field("manual")
    extra_data: Optional[dict] = Field(default_factory=dict)
```

**MemoryUpdate**:

```python
class MemoryUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = None
    category: Optional[str] = None
    memory_tier: Optional[str] = None
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    extra_data: Optional[dict] = None
```

**MemoryRelationCreate**:

```python
class MemoryRelationCreate(BaseModel):
    target_id: str = Field(...)
    relation_type: str = Field(...)
    strength: float = Field(1.0, ge=0.0, le=1.0)
    description: Optional[str] = None
```

**SearchQuery**:

```python
class SearchQuery(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(10, ge=1, le=50)
    category: Optional[str] = None
    memory_tier: Optional[str] = None
```

---

## 4. 前端

### 4.1 模板文件

- **内容面板**: `modules/memory/memories_content.html`（594 行，完整页面）

### 4.2 Alpine.js 组件

**函数名**: `memoriesPage()`

**完整状态定义**:

```javascript
{
    memories: [],              // 记忆列表
    loading: false,            // 加载状态
    skip: 0,                   // 分页偏移
    limit: 12,                 // 每页条数
    total: 0,                  // 总数
    searchQuery: '',           // 搜索关键字
    categoryFilter: '',        // 分类过滤器
    tierFilter: '',            // 层级过滤器
    stats: { total: 0, by_tier: {}, by_category: {} },

    showCreateModal: false,    // 创建模态框
    showViewModal: false,      // 查看模态框
    creating: false,           // 创建中
    newMemory: {
        title: '',
        content: '',
        category: 'other',
        memory_tier: 'semantic',
        confidence_score: 1.0
    },
    viewingMemory: null,       // 查看中的记忆

    toasts: [],                // Toast 通知队列
    toastId: 0                // Toast ID 计数器
}
```

**方法**:

| 方法 | 功能 |
|---|---|
| `init()` | 初始化，调用 loadMemories() 和 loadStats() |
| `loadMemories()` | GET `/api/memory/memories?skip=&limit=&search=&category=&memory_tier=` |
| `loadStats()` | GET `/api/memory/stats` |
| `createMemory()` | POST `/api/memory/memories`，验证标题和内容非空 |
| `viewMemory(memory)` | GET `/api/memory/memories/{id}`，打开查看模态框 |
| `editMemory(memory)` | 编辑（开发中） |
| `deleteMemory(memory)` | DELETE `/api/memory/memories/{id}`，确认后删除 |
| `getCategoryClass(category)` | 返回分类对应的颜色样式 |
| `getTierClass(tier)` | 返回层级对应的颜色样式 |
| `getTierText(tier)` | 返回层级的中文名 |
| `formatDate(dateString)` | 日期格式化 (zh-CN locale) |
| `nextPage()` / `prevPage()` | 分页翻页 |
| `showToast(type, message)` | 显示 Toast 通知(3秒自动消失) |

### 4.3 分类颜色映射

| 分类 | 颜色 | 样式类 |
|---|---|---|
| architecture | 蓝色 | `bg-blue-600/20 text-blue-400` |
| decision | 绿色 | `bg-green-600/20 text-green-400` |
| pattern | 紫色 | `bg-purple-600/20 text-purple-400` |
| issue | 黄色 | `bg-yellow-600/20 text-yellow-400` |
| bug | 红色 | `bg-red-600/20 text-red-400` |
| other | 灰色 | `bg-gray-600/20 text-gray-400` |

### 4.4 关键 UI 布局

```
┌─────────────────────────────────────────────────────┐
│  页头: 标题「记忆管理」+ 副标题 + 按钮组              │
│        ┌──────────┐ ┌──────────┐                    │
│        │ 记忆图谱  │ │ 新建记忆  │                    │
│        └──────────┘ └──────────┘                    │
├─────────────────────────────────────────────────────┤
│  统计卡片 (4列栅格)                                  │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐              │
│  │总记忆 │ │情景记忆│ │语义记忆│ │今日新增│              │
│  └──────┘ └──────┘ └──────┘ └──────┘              │
├─────────────────────────────────────────────────────┤
│  过滤栏: 搜索框 + 分类下拉 + 层级下拉                 │
├─────────────────────────────────────────────────────┤
│  记忆列表 (3列网格卡片)                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐  │
│  │ 分类标签 层级 │ │ 分类标签 层级 │ │ 分类标签 层级 │  │
│  │ 标题        │ │ 标题        │ │ 标题        │  │
│  │ 内容预览... │ │ 内容预览... │ │ 内容预览... │  │
│  │ 置信度 日期 │ │ 置信度 日期 │ │ 置信度 日期 │  │
│  └─────────────┘ └─────────────┘ └─────────────┘  │
├─────────────────────────────────────────────────────┤
│  分页: 上一页 / 第N页 / 下一页                       │
├─────────────────────────────────────────────────────┤
│  创建模态框: 标题/分类/层级/内容/置信度滑块           │
│  查看模态框: 完整内容 + 元数据(层级/置信度/访问/日期)  │
│  Toast 通知: 右下角堆叠显示(成功/错误)                │
└─────────────────────────────────────────────────────┘
```

---

## 5. 核心功能

### 5.1 记忆条目三层体系

记忆模块采用三层记忆层级（memory_tier），类比人类记忆系统：

| 层级 | 英文 | 说明 | 颜色 | 图标 |
|---|---|---|---|---|
| 情景记忆 | Episodic | 具体的事件和经验，如"2024-03-15 部署了 v2.1 到生产环境" | 紫色 | `fa-clock` |
| 语义记忆 | Semantic | 抽象的概念和知识，如"系统使用 JWT 进行身份认证" | 蓝色 | `fa-lightbulb` |
| 程序记忆 | Procedural | 操作步骤和流程，如"部署流程: 1. 构建镜像 2. 推送到仓库 3. 滚动更新" | 绿色 | `fa-cogs` |

前端通过 `getTierClass()` 和 `getTierText()` 函数渲染层级标签：

```javascript
getTierClass(tier) {
    const classes = {
        'episodic': 'bg-purple-600/20 text-purple-400',
        'semantic': 'bg-blue-600/20 text-blue-400',
        'procedural': 'bg-green-600/20 text-green-400'
    };
    return classes[tier] || 'bg-gray-600/20 text-gray-400';
}

getTierText(tier) {
    const texts = {
        'episodic': '情景',
        'semantic': '语义',
        'procedural': '程序'
    };
    return texts[tier] || tier;
}
```

### 5.2 记忆图谱 (MemoryRelation)

记忆图谱通过 MemoryRelation 模型实现记忆条目之间的关联网络：

**关系方向**:
```
MemoryEntry A  ──(relation_type)──▶  MemoryEntry B
(source_id)                           (target_id)
```

**API 接口**:

```
获取关系: GET /api/memory/memories/{memory_id}/relations
  → 返回 { outgoing: [...], incoming: [...] }
  → outgoing: 从该记忆出发的关系
  → incoming: 指向该记忆的关系

创建关系: POST /api/memory/memories/{memory_id}/relations
  → 请求体: { target_id, relation_type, strength, description }
  → 校验 source 和 target 都存在且未删除
  → 创建 MemoryRelation

删除关系: DELETE /api/memory/relations/{relation_id}
  → 直接删除记录 (非软删除)
```

**图谱查询接口**:

```python
GET /api/memory/graph?project_id=&depth=2
  → 查询最多 100 条未删除的记忆
  → 构建 nodes: [{ id, label, category, memory_tier, confidence_score, access_count }]
  → 查询这些记忆之间的所有关系 (双向过滤 source_id + target_id)
  → 构建 links: [{ source, target, type, strength }]
  → 返回: { nodes, links, total_nodes, total_links }
```

前端 "记忆图谱" 按钮跳转到 `/memory/graph` 页面，使用 `fa-project-diagram` 图标。

### 5.3 搜索与过滤

**列表过滤**:

```
GET /api/memory/memories?skip=0&limit=20&project_id=&category=architecture&memory_tier=semantic&search=JWT
  → SQL 条件组合: deleted_at IS NULL
  → 可选: project_id 过滤
  → 可选: category 精确匹配
  → 可选: memory_tier 精确匹配
  → 可选: search → title ILIKE %search% OR content ILIKE %search%
  → 按 created_at DESC 排序
```

前端过滤栏提供三个控件:
- **搜索框**: 300ms 防抖输入，绑定 `searchQuery`
- **分类下拉**: 全部 / 架构 / 决策 / 模式 / 问题 / Bug / 其他
- **层级下拉**: 全部 / 情景 / 语义 / 程序

**语义搜索接口**:

```python
POST /api/memory/search
  → 请求体: { query, top_k, category?, memory_tier? }
  → 可选: project_id (Query 参数)
  → ILIKE 搜索 title + content
  → 返回: { query, total, results: [{ memory, score: 0.95, highlights: [] }] }
```

### 5.4 记忆访问追踪

每次通过 `GET /api/memory/memories/{memory_id}` 获取记忆详情时，自动执行:

```python
memory.access_count += 1
memory.last_accessed_at = datetime.now(timezone.utc)
```

前端卡片上显示访问次数 (`fa-eye` 图标 + `access_count` 数字)。

### 5.5 统计接口

```
GET /api/memory/stats?project_id=
  → 总数: count(MemoryEntry.id) WHERE deleted_at IS NULL
  → 按分类分组: GROUP BY category → by_category
  → 按层级分组: GROUP BY memory_tier → by_tier
  → 返回: { total, by_category: { "architecture": 5, ... }, by_tier: { "semantic": 10, ... } }
```

前端统计卡片使用 `stats.by_tier?.episodic` 和 `stats.by_tier?.semantic` 分别显示情景记忆和语义记忆的数量。

### 5.6 创建记忆流程

```
用户点击「新建记忆」按钮
  → showCreateModal = true
  → 填写标题/分类/层级/内容/置信度
  → 点击「保存」

POST /api/memory/memories
  → 校验 MemoryCreate (title, content 必填; category, memory_tier 有默认值)
  → require_permissions("memory:write")
  → 创建 MemoryEntry, extra_data 序列化为 JSON
  → 成功: showToast('success', '记忆创建成功')
  → 失败: 显示后端错误信息或网络错误
  → 刷新列表 + 统计
```

### 5.7 记忆查看与删除

**查看**:
```
点击记忆卡片 → GET /api/memory/memories/{id}
  → 返回完整内容 (include_content=True)
  → 显示查看模态框: 分类标签 + 标题 + 完整内容 + 元数据
  → 元数据: 层级 / 置信度 / 访问次数 / 创建时间
  → 提供编辑(开发中)和删除按钮
```

**删除**:
```
点击删除按钮 → confirm("确定要删除...")
  → DELETE /api/memory/memories/{id}
  → 软删除: 设置 deleted_at
  → 刷新列表 + 统计
```

---

## 6. 与 Knowledge 模块的对比

| 特性 | Memory 模块 | Knowledge 模块 |
|---|---|---|
| 核心实体 | 记忆条目 (MemoryEntry) | 知识库 (KnowledgeBase) → 文档 → 分块 |
| 层级体系 | episodic/semantic/procedural 三层 | 分类标签 (general/research/prd/...) |
| 关系图谱 | MemoryRelation 有向图 (出边/入边) | 无关系图，靠父级 ID 关联 |
| 父子结构 | parent_id + children 自引用 | base_id 引用 KnowledgeBase |
| 置信度 | confidence_score [0.0-1.0] | 无 |
| AI 审核 | ai_suggested + ai_review_status | processing_status |
| 模板系统 | 无 | DocumentTemplate 完整模板 CRUD + 渲染 |
| 访问追踪 | access_count + last_accessed_at | 无 |
| 分块引擎 | 无 | chunking_strategy + chunk_size + DocumentChunk |
| embedding | MemoryEntry.embedding (预留) | DocumentChunk.embedding (预留) |