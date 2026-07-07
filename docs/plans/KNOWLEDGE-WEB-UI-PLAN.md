# Knowledge Tool Web UI - 详细开发计划

## 文档信息

| 属性 | 值 |
|------|-----|
| 版本 | v1.0 |
| 创建日期 | 2026-07-07 |
| 优先级 | P0 (最高) |
| 预估工时 | 3 周 |
| 状态 | 待开发 |

---

## 1. 项目概述

### 1.1 目标

构建一个**生产级的文档知识库管理界面**，提供完整的文档生命周期管理、智能搜索和知识可视化能力。

### 1.2 参考标准

以 **SkillRouter** 的 Web UI 为标杆，实现：
- 专业的外观和交互体验
- 完整的 CRUD 操作
- 高级搜索和过滤
- 数据可视化
- 多语言支持 (i18n)

### 1.3 核心原则

1. **用户友好**：直观的操作界面，低学习成本
2. **功能完整**：覆盖文档管理的所有场景
3. **性能优异**：快速响应，支持大文档
4. **视觉专业**：统一的暗色主题设计

---

## 2. 功能需求

### 2.1 文档管理仪表盘

#### 2.1.1 项目/知识库选择器

**功能描述**：
- 左侧边栏显示项目/知识库树形结构
- 支持多层级分类（类似 SkillRouter 的技能组）
- 支持创建、编辑、删除知识库

**界面布局**：
```
┌─────────────────────────────────────────────────────────────┐
│  📁 知识库列表          │  📄 文档管理                      │
│  ─────────────────────  │  ───────────────────────────────  │
│  + 新建知识库           │                                   │
│                         │  [列表视图 ▼] [筛选 ▼] [排序 ▼]   │
│  ▼ 默认知识库           │  ┌─────────────────────────────┐  │
│  ├─ 📂 API 文档        │  │ 🔍 搜索文档...              │  │
│  ├─ 📂 技术规范        │  └─────────────────────────────┘  │
│  ├─ 📂 产品文档        │                                   │
│  │  ├─ 📄 用户手册      │  ┌──────────┐ ┌──────────┐      │
│  │  └─ 📄 快速入门      │  │ 📄 Doc 1 │ │ 📄 Doc 2 │      │
│  └─ 📂 开发文档        │  │ [PDF]    │ │ [MD]     │      │
│      ├─ 📄 架构设计    │  │ 已索引   │ │ 处理中   │      │
│      └─ 📄 数据库设计  │  └──────────┘ └──────────┘      │
│                         │                                   │
│  🏷️ 标签云             │  [分页: < 1 2 3 ... 10 >]        │
│  #API #Auth            │                                   │
│  #Database             │                                   │
└─────────────────────────────────────────────────────────────┘
```

**数据模型扩展**：
```python
class KnowledgeBase(Base):
    """知识库（类似 SkillRouter 的 Project）"""
    __tablename__ = "knowledge_bases"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(128), nullable=False)
    slug = Column(String(128), unique=True)
    description = Column(Text)
    parent_id = Column(UUID, ForeignKey("knowledge_bases.id"))
    owner_id = Column(UUID, ForeignKey("users.id"))
    visibility = Column(String(20), default="private")  # private, workspace, public
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联
    documents = relationship("KtDocument", back_populates="knowledge_base")
```

---

#### 2.1.2 文档卡片/列表视图

**视图模式**：
1. **卡片视图**：缩略图、标题、状态、标签
2. **列表视图**：详细信息的表格展示
3. **树形视图**：按目录结构展示

**文档卡片元素**：
```
┌─────────────────────────────┐
│  [📄 文档类型图标]          │
│                             │
│  文档标题                   │
│  这是文档的描述...          │
│                             │
│  🏷️ API 🏷️ Auth            │
│                             │
│  ✅ 已索引  |  2026-07-07   │
│                             │
│  [👁️ 预览] [✏️ 编辑] [🗑️] │
└─────────────────────────────┘
```

**文档状态**：
- `pending` - 待处理（灰色）
- `processing` - 处理中（黄色）
- `indexed` - 已索引（绿色）
- `failed` - 失败（红色）

---

#### 2.1.3 批量操作

**功能**：
- 批量选择（复选框）
- 批量删除
- 批量移动到其他知识库
- 批量重新索引
- 批量导出

**界面**：
```
已选择 5 项  [全选]  [取消选择]

批量操作: [移动到... ▼] [重新索引] [导出] [删除]
```

---

### 2.2 文档预览与分块可视化

#### 2.2.1 文档预览器

**支持的格式**：
- Markdown (渲染预览)
- PDF (PDF.js 预览)
- 纯文本 (语法高亮)
- Word (转为 HTML 预览)

**界面布局**：
```
┌─────────────────────────────────────────────────────────────┐
│ 📄 文档名称.md                              [✕] 关闭      │
├─────────────────────────────────────────────────────────────┤
│  📖 预览    │    🔍 分块视图    │    📊 索引详情          │
├─────────────┴───────────────────────────────────────────────┤
│                                                             │
│  # 文档标题                                                 │
│                                                             │
│  这是文档的详细内容...                                      │
│                                                             │
│  ## 章节 1                                                  │
│                                                             │
│  章节内容...                                                │
│                                                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 2.2.2 分块可视化（核心功能）

**功能描述**：
展示文档如何被切分成知识块，以及每个块的索引状态。

**界面设计**：
```
🔍 分块视图

分块策略: [固定长度 ▼]  块大小: 512 tokens  重叠: 50 tokens

┌─────────────────────────────────────────────────────────────┐
│ 块 #1 (tokens: 512)                          ✅ 已索引     │
├─────────────────────────────────────────────────────────────┤
│ 这是第一段的内容...                                         │
│ 显示了如何被切分...                                         │
│ [查看向量] [查看关键词]                                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 块 #2 (tokens: 498)                          ✅ 已索引     │
├─────────────────────────────────────────────────────────────┤
│ 这是第二段的内容...                                         │
│ 与第一段有重叠部分...                                       │
│ [查看向量] [查看关键词]                                     │
└─────────────────────────────────────────────────────────────┘
```

**技术实现**：
- 使用 Monaco Editor 展示原文
- 高亮显示分块边界
- 点击块跳转到对应位置

---

#### 2.2.3 索引详情面板

**显示信息**：
- 索引状态和时间
- 分块数量
- Token 总数
- 存储大小
- 关键词提取结果
- 向量维度

**界面**：
```
📊 索引详情

基本信息
━━━━━━━━━━━━━━━━━━━━
状态:        ✅ 已索引
索引时间:    2026-07-07 14:32:18
分块数:      12
Token 数:    6,240
存储大小:    2.4 MB

分块统计
━━━━━━━━━━━━━━━━━━━━
平均块大小:  520 tokens
最小块:      256 tokens
最大块:      512 tokens
重叠率:      10%

关键词 (Top 10)
━━━━━━━━━━━━━━━━━━━━
1. API (45次)
2. Authentication (32次)
3. Token (28次)
...
```

---

### 2.3 高级搜索中心

#### 2.3.1 搜索界面

**设计目标**：类似 Google 的简洁搜索 + 高级过滤

**界面布局**：
```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│                    🔍 AIDP 知识库搜索                       │
│                                                             │
│    ┌─────────────────────────────────────────────────┐     │
│    │  搜索知识库...                           [🔍]  │     │
│    └─────────────────────────────────────────────────┘     │
│                                                             │
│    过滤器: [全部知识库 ▼] [全部类型 ▼] [全部标签 ▼] [时间 ▼] │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 2.3.2 搜索结果展示

**混合搜索结果**：
```
找到 15 个相关结果 (耗时 0.23s)

📄 文档结果 (8)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1.  API 设计规范.md                          相似度: 95%
    ...用户认证应该使用 JWT Token，有效期设置为 24 小时...
    来源: 技术规范 > API 文档 | 2026-06-15

2.  认证流程说明.md                          相似度: 87%
    ...Token 的生成和验证流程如下...
    来源: 产品文档 > 用户手册 | 2026-06-10

🔍 知识块结果 (7)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1.  来自 "Authentication Service.md"
    ...JWT Token 包含 header、payload、signature 三部分...
    相似度: 92% | 块 #3

2.  来自 "Security Best Practices.md"
    ...Token 不应该包含敏感信息，应该设置合理的过期时间...
    相似度: 89% | 块 #7
```

#### 2.3.3 搜索过滤器和排序

**过滤器**：
- 知识库范围（单选/多选）
- 文档类型（PDF/Markdown/Word/...）
- 标签（多选）
- 时间范围（最近1天/7天/30天/自定义）
- 索引状态（已索引/未索引）

**排序选项**：
- 相关度（默认）
- 创建时间
- 更新时间
- 访问次数
- 文档名称

---

#### 2.3.4 搜索高亮和预览

**功能**：
- 关键词高亮显示
- 搜索结果预览（带上下文）
- 点击跳转到原文位置

**实现**：
```python
# 后端返回带高亮标记的结果
{
    "results": [
        {
            "type": "document",
            "title": "API 设计规范.md",
            "preview": "用户认证应该使用 <mark>JWT Token</mark>，有效期设置为 24 小时...",
            "highlights": ["JWT Token", "认证"],
            "score": 0.95,
            "url": "/documents/123#section-2"
        }
    ]
}
```

---

### 2.4 文档上传与导入

#### 2.4.1 上传界面

**支持方式**：
1. 点击上传
2. 拖拽上传
3. 批量上传

**上传界面**：
```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│     ┌─────────────────────────────────────────────────┐    │
│     │                                                 │    │
│     │              📁 拖拽文件到此处                  │    │
│     │                                                 │    │
│     │         或 [点击选择文件] 支持多选             │    │
│     │                                                 │    │
│     │    支持格式: PDF, Markdown, Word, TXT, HTML    │    │
│     │    单文件最大: 50MB | 批量最多: 100 个文件     │    │
│     │                                                 │    │
│     └─────────────────────────────────────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 2.4.2 上传队列和进度

**上传队列显示**：
```
上传队列 (3/5 完成)

┌─────────────────────────────────────────────────────────────┐
│ 📄 文档1.pdf                     [██████░░░░] 60% 上传中   │
├─────────────────────────────────────────────────────────────┤
│ 📄 文档2.md                      [██████████] 100% ✓ 完成  │
├─────────────────────────────────────────────────────────────┤
│ 📄 文档3.docx                    [░░░░░░░░░░] 0% 排队中    │
└─────────────────────────────────────────────────────────────┘

[全部取消]  [暂停]  [后台上传]
```

#### 2.4.3 导入设置

**配置选项**：
```
导入设置
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

目标知识库:    [默认知识库 ▼]

索引选项:
  [x] 立即开始索引
  [ ] 仅导入不索引
  [ ] 增量更新（仅处理变更）

分块策略:
  策略: [固定长度 ▼]
  块大小: [512 ▼] tokens
  重叠: [50 ▼] tokens

处理选项:
  [x] 提取关键词
  [x] 生成摘要
  [ ] OCR 识别（PDF图片）
  [ ] 翻译为英文

冲突处理:
  [同名跳过] [覆盖] [重命名] [询问]

[开始导入]
```

---

### 2.5 知识图谱（高级功能）

#### 2.5.1 文档关系图谱

**功能**：展示文档之间的引用、关联关系

**可视化**：
```
📊 知识图谱

┌─────────────────────────────────────────────────────────────┐
│  [力导向图]  [环形图]  [层次图]        [放大] [缩小] [重置] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                        ┌──────────┐                        │
│                        │ API 规范 │                        │
│                        └────┬─────┘                        │
│                             │                              │
│            ┌────────────────┼────────────────┐             │
│            ▼                ▼                ▼             │
│     ┌──────────┐     ┌──────────┐     ┌──────────┐        │
│     │ 认证流程 │◄───►│ 授权设计 │◄───►│ Token设计│        │
│     └──────────┘     └──────────┘     └──────────┘        │
│            │                │                │             │
│            └────────────────┼────────────────┘             │
│                             ▼                              │
│                        ┌──────────┐                        │
│                        │ 安全规范 │                        │
│                        └──────────┘                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 技术架构

### 3.1 后端 API 扩展

#### 3.1.1 新增 API 端点

```python
# 知识库管理
GET    /api/knowledge-bases              # 列表
POST   /api/knowledge-bases              # 创建
GET    /api/knowledge-bases/{id}         # 详情
PUT    /api/knowledge-bases/{id}         # 更新
DELETE /api/knowledge-bases/{id}         # 删除

# 文档管理（已有基础上扩展）
GET    /api/documents/{id}/chunks        # 获取文档分块
GET    /api/documents/{id}/preview       # 预览文档
GET    /api/documents/{id}/index-info    # 索引详情
POST   /api/documents/bulk-index         # 批量索引

# 搜索（增强）
GET    /api/search                       # 混合搜索
GET    /api/search/suggest               # 搜索建议
GET    /api/search/filters               # 获取过滤器选项

# 统计
GET    /api/statistics/overview          # 概览统计
GET    /api/statistics/trend             # 趋势统计
```

#### 3.1.2 数据模型扩展

```python
# 知识库模型（新增）
class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(128), nullable=False)
    slug = Column(String(128), unique=True)
    description = Column(Text)
    parent_id = Column(UUID, ForeignKey("knowledge_bases.id"))
    owner_id = Column(UUID, ForeignKey("users.id"))
    visibility = Column(String(20), default="private")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

# 文档模型（扩展）
class KtDocument(Base):
    # ... 已有字段 ...
    
    # 新增字段
    knowledge_base_id = Column(UUID, ForeignKey("knowledge_bases.id"))
    thumbnail_url = Column(String(512))  # 缩略图
    summary = Column(Text)               # 自动生成的摘要
    keywords = Column(JSONB, default=list)  # 提取的关键词
    metadata = Column(JSONB, default=dict)  # 扩展元数据
    view_count = Column(Integer, default=0)
```

---

### 3.2 前端技术栈

| 技术 | 用途 | 版本 |
|------|------|------|
| Alpine.js | 响应式框架 | 3.x |
| Tailwind CSS | 样式框架 | 3.x |
| Monaco Editor | 代码/文本预览 | Latest |
| PDF.js | PDF 预览 | 3.x |
| Chart.js | 统计图表 | 4.x |
| D3.js | 知识图谱可视化 | 7.x |

### 3.3 页面结构

```
tools/knowledge-tool/app/web/
├── static/
│   ├── css/
│   │   └── knowledge.css       # 知识库专用样式
│   ├── js/
│   │   ├── components.js       # 通用组件
│   │   ├── search.js           # 搜索功能
│   │   └── graph.js            # 图谱可视化
│   └── components/
│       ├── document-card.html  # 文档卡片组件
│       ├── chunk-view.html     # 分块视图组件
│       └── search-result.html  # 搜索结果组件
│
├── templates/
│   ├── layouts/
│   │   └── base.html           # 基础布局
│   ├── pages/
│   │   ├── dashboard.html      # 仪表盘
│   │   ├── documents.html      # 文档列表
│   │   ├── document-detail.html # 文档详情
│   │   ├── search.html         # 搜索中心
│   │   ├── upload.html         # 上传页面
│   │   └── statistics.html     # 统计页面
│   └── components/
│       ├── knowledge-base-tree.html  # 知识库树
│       ├── document-preview.html     # 文档预览
│       └── search-filters.html       # 搜索过滤器
│
└── routes.py                   # Web 路由
```

---

## 4. 数据库迁移

### 4.1 新增表

```sql
-- 知识库表
CREATE TABLE knowledge_bases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(128) NOT NULL,
    slug VARCHAR(128) UNIQUE NOT NULL,
    description TEXT,
    parent_id UUID REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    owner_id UUID REFERENCES users(id),
    visibility VARCHAR(20) DEFAULT 'private',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 文档标签关联表（多对多）
CREATE TABLE document_tags (
    document_id UUID REFERENCES kt_documents(id) ON DELETE CASCADE,
    tag VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (document_id, tag)
);

-- 索引
CREATE INDEX idx_knowledge_bases_owner ON knowledge_bases(owner_id);
CREATE INDEX idx_knowledge_bases_parent ON knowledge_bases(parent_id);
CREATE INDEX idx_document_tags_tag ON document_tags(tag);
```

### 4.2 文档表扩展

```sql
-- 为 kt_documents 添加新列
ALTER TABLE kt_documents 
    ADD COLUMN knowledge_base_id UUID REFERENCES knowledge_bases(id),
    ADD COLUMN summary TEXT,
    ADD COLUMN keywords JSONB DEFAULT '[]',
    ADD COLUMN view_count INTEGER DEFAULT 0,
    ADD COLUMN metadata JSONB DEFAULT '{}';

-- 索引
CREATE INDEX idx_documents_kb ON kt_documents(knowledge_base_id);
```

---

## 5. 开发计划

### Week 1: 基础架构与文档列表

| 天数 | 任务 | 产出 |
|------|------|------|
| Day 1-2 | 数据库迁移、API 扩展 | 新的表结构和 API |
| Day 3-4 | 知识库管理功能 | 知识库 CRUD 界面 |
| Day 5 | 文档列表视图 | 卡片/列表视图 |

### Week 2: 文档预览与搜索

| 天数 | 任务 | 产出 |
|------|------|------|
| Day 1-2 | 文档预览功能 | Markdown/PDF 预览 |
| Day 3-4 | 分块可视化 | 分块展示界面 |
| Day 5 | 搜索中心 | 搜索界面和结果展示 |

### Week 3: 高级功能与优化

| 天数 | 任务 | 产出 |
|------|------|------|
| Day 1-2 | 上传导入功能 | 拖拽上传、批量导入 |
| Day 3 | 统计仪表盘 | 数据可视化 |
| Day 4 | 知识图谱（可选） | 文档关系图 |
| Day 5 | 测试与优化 | Bug 修复、性能优化 |

---

## 6. 验收标准

### 6.1 功能验收

- [ ] 知识库 CRUD 功能完整
- [ ] 文档列表支持卡片/列表/树形视图
- [ ] 文档预览支持 Markdown/PDF/文本
- [ ] 分块可视化清晰展示索引状态
- [ ] 搜索支持语义+关键词混合
- [ ] 搜索结果高亮显示
- [ ] 批量上传和导入功能正常
- [ ] 统计仪表盘数据准确

### 6.2 性能验收

- [ ] 文档列表加载 < 1s（1000条）
- [ ] 搜索响应 < 500ms
- [ ] 文档预览加载 < 2s（10MB）
- [ ] 批量上传支持 100 个文件同时处理

### 6.3 体验验收

- [ ] 界面风格与 SkillRouter 一致
- [ ] 支持中英文切换
- [ ] 移动端适配（响应式）
- [ ] 键盘快捷键支持

---

## 7. 风险评估

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| PDF 预览兼容性 | 高 | 中 | 使用成熟的 PDF.js 库 |
| 大文件上传性能 | 中 | 高 | 分片上传 + 进度显示 |
| 搜索精度不足 | 高 | 中 | 混合搜索策略 + 调优 |
| 数据库迁移失败 | 高 | 低 | 备份 + 回滚方案 |

---

## 8. 参考资源

- SkillRouter Web UI 实现
- ElasticSearch Kibana 界面设计
- Notion 文档管理界面
- Obsidian 知识库界面

---

**文档结束**

*本计划将在开发过程中根据实际情况调整*
