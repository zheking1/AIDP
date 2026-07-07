# Memory Tool Web UI - 详细开发计划

## 1. 概述

构建生产级记忆管理界面，核心特色是**记忆图谱可视化**和**上下文包交互生成**。

### 1.1 核心功能

```
┌─────────────────────────────────────────────────────────────┐
│                    Memory Explorer                           │
├──────────────────┬──────────────────────────────────────────┤
│  🧠 记忆图谱      │  📋 记忆详情                             │
│  (D3.js 可视化)   │                                          │
│                  │  标题: API Error Handling Pattern        │
│    ○───○         │  类型: pattern                           │
│   /│\  │         │  层级: semantic                          │
│  ○─○─○ ○         │  置信度: 95%                             │
│                  │                                          │
│  ○ = 记忆节点     │  内容:                                   │
│  │ = 关联关系     │  When handling API errors in FastAPI... │
│  颜色 = 类型      │                                          │
│                  │  关联记忆:                               │
│  图例:           │  • Error Logging Standards               │
│  🔵 决策         │  • Retry Strategy                        │
│  🟢 模式         │  • FastAPI Middleware                    │
│  🟡 问题         │                                          │
│  🔴 Bug          │  [提升层级] [编辑] [删除]                │
└──────────────────┴──────────────────────────────────────────┘
```

### 1.2 参考项目

- **AgentMemory / MemGPT**: 记忆分层、自动总结
- **LLM Memory**: 向量检索、时间衰减

---

## 2. 功能需求

### 2.1 记忆图谱可视化（核心）

#### 2.1.1 力导向图
- 节点：记忆条目（颜色区分类型）
- 边：关联关系（强度表示关联度）
- 交互：
  - 拖拽节点
  - 缩放/平移
  - 点击显示详情
  - 双击展开关联

#### 2.1.2 多种视图模式
1. **网络视图**：力导向图，展示全部关联
2. **层次视图**：树形结构，按父子关系
3. **时间轴视图**：按时间顺序排列
4. **分类视图**：按类型分组

### 2.2 记忆管理器

#### 2.2.1 记忆列表
- 卡片/列表/表格视图
- 过滤器（类型、层级、时间、标签）
- 排序（相关度、时间、访问次数）
- 批量操作

#### 2.2.2 记忆编辑
- 富文本编辑器
- 标签输入（自动补全）
- 类型选择
- 父记忆关联

### 2.3 上下文包生成器

#### 2.3.1 交互式构建
```
任务描述: [输入任务描述...]

预算: [2000] tokens

选择的记忆:
☑️ 记忆1 - Error Handling Pattern (256 tokens)
☑️ 记忆2 - FastAPI Best Practices (512 tokens)
☐ 记忆3 - Database Connection (128 tokens)

预览上下文:
┌─────────────────────────────────────────────────┐
│ ## 项目背景                                     │
│ [自动生成的摘要...]                             │
│                                                 │
│ ## 相关记忆                                     │
│ 1. Error Handling Pattern                       │
│    [记忆内容摘要...]                            │
│ 2. FastAPI Best Practices                       │
│    [记忆内容摘要...]                            │
└─────────────────────────────────────────────────┘

[生成上下文包] [复制到剪贴板]
```

### 2.4 记忆审核队列

- 待审核记忆列表
- AI 预审核建议
- 批量批准/拒绝
- 审核历史

---

## 3. 技术增强

### 3.1 向量搜索（pgvector）
```sql
-- 添加向量列
ALTER TABLE memory_entries ADD COLUMN embedding VECTOR(384);

-- 创建 HNSW 索引
CREATE INDEX idx_memory_embedding ON memory_entries 
USING hnsw (embedding vector_cosine_ops);
```

### 3.2 记忆合并算法
- 检测相似记忆（余弦相似度 > 0.85）
- 自动合并建议
- 冲突解决界面

---

## 4. 开发计划（2 周）

### Week 1: 基础与可视化
- Day 1-2: 数据库迁移（向量支持）
- Day 3-4: D3.js 图谱可视化
- Day 5: 记忆管理 CRUD

### Week 2: 高级功能
- Day 1-2: 上下文包生成器
- Day 3: 向量搜索集成
- Day 4: 记忆审核队列
- Day 5: 测试与优化

---

## 5. 数据模型扩展

```python
class MemoryEntry(Base):
    # 新增字段
    embedding = Column(Vector(384))  # pgvector
    merged_from = Column(JSONB, default=list)  # 合并来源
    ai_suggested = Column(Boolean, default=False)  # AI生成
    ai_review_status = Column(String(20), default='pending')  # AI审核状态
```

---

**详见完整文档在开发过程中补充**
