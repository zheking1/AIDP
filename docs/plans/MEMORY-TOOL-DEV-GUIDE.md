# Memory Tool Web UI - 完整开发文档

> **版本**: v1.0  
> **状态**: 可直接开发  
> **预估工期**: 10 个工作日  

---

## 1. 项目概述

### 1.1 目标
构建生产级记忆管理界面，核心特色是**记忆图谱可视化**和**上下文包交互生成**。

### 1.2 功能范围
1. **记忆图谱可视化** (D3.js) - 力导向图展示记忆关联
2. **记忆管理器** - CRUD + 搜索 + 过滤
3. **上下文包生成器** - 交互式选择记忆构建上下文
4. **记忆审核队列** - 待审核记忆管理

### 1.3 技术栈
- **Backend**: FastAPI + SQLAlchemy + PostgreSQL + pgvector
- **Frontend**: Alpine.js + TailwindCSS + D3.js v7
- **Database**: PostgreSQL 16 + pgvector extension

---

## 2. 架构设计

### 2.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Browser                              │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP/WebSocket
┌──────────────────────────▼──────────────────────────────────────┐
│                      Nginx (Reverse Proxy)                       │
└──────────────────────────┬──────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
┌───────▼──────┐  ┌───────▼──────┐  ┌───────▼──────┐
│  Controller  │  │ Memory Tool  │  │  Other Tools │
│   :8883      │  │   :18085     │  │              │
└──────────────┘  └───────┬──────┘  └──────────────┘
                          │
              ┌───────────┴───────────┐
              │                       │
    ┌─────────▼──────────┐  ┌────────▼─────────┐
    │   PostgreSQL       │  │   Qdrant/        │
    │   (Metadata)       │  │   pgvector       │
    └────────────────────┘  │   (Vectors)      │
                            └──────────────────┘
```

### 2.2 数据流

```
1. 记忆创建/更新
   User → API → Database → Vector DB (embedding)
   
2. 记忆搜索
   User → Query → Vector Search → Similarity Ranking → Results
   
3. 图谱可视化
   User → Request All Memories → Build Graph (D3.js) → Force Simulation
   
4. 上下文包生成
   User → Select Memories → Calculate Tokens → Generate Context
```

---

## 3. 数据库设计

### 3.1 扩展内存表结构

执行以下 SQL 扩展 memory_entries 表：

```sql
-- 启用 pgvector 扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 扩展 memory_entries 表
ALTER TABLE memory_entries ADD COLUMN IF NOT EXISTS embedding VECTOR(384);
ALTER TABLE memory_entries ADD COLUMN IF NOT EXISTS merged_from JSONB DEFAULT '[]';
ALTER TABLE memory_entries ADD COLUMN IF NOT EXISTS ai_suggested BOOLEAN DEFAULT FALSE;
ALTER TABLE memory_entries ADD COLUMN IF NOT EXISTS ai_review_status VARCHAR(20) DEFAULT 'approved';
ALTER TABLE memory_entries ADD COLUMN IF NOT EXISTS memory_tier VARCHAR(20) DEFAULT 'semantic';
ALTER TABLE memory_entries ADD COLUMN IF NOT EXISTS parent_id UUID REFERENCES memory_entries(id);
ALTER TABLE memory_entries ADD COLUMN IF NOT EXISTS confidence_score FLOAT DEFAULT 1.0;
ALTER TABLE memory_entries ADD COLUMN IF NOT EXISTS access_count INTEGER DEFAULT 0;
ALTER TABLE memory_entries ADD COLUMN IF NOT EXISTS last_accessed_at TIMESTAMP;

-- 创建向量索引 (HNSW - 高性能近似最近邻搜索)
CREATE INDEX IF NOT EXISTS idx_memory_embedding_hnsw ON memory_entries 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- 创建其他索引
CREATE INDEX IF NOT EXISTS idx_memory_parent ON memory_entries(parent_id);
CREATE INDEX IF NOT EXISTS idx_memory_tier ON memory_entries(memory_tier);
CREATE INDEX IF NOT EXISTS idx_memory_category ON memory_entries(category);
CREATE INDEX IF NOT EXISTS idx_memory_project ON memory_entries(project);

-- 记忆关系表 (用于图谱边)
CREATE TABLE IF NOT EXISTS memory_relations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES memory_entries(id) ON DELETE CASCADE,
    target_id UUID NOT NULL REFERENCES memory_entries(id) ON DELETE CASCADE,
    relation_type VARCHAR(50) NOT NULL, -- 'similar', 'parent_child', 'reference', 'sequence'
    strength FLOAT DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_id, target_id, relation_type)
);

-- 上下文包表
CREATE TABLE IF NOT EXISTS context_packages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    project VARCHAR(100),
    created_by VARCHAR(100),
    total_tokens INTEGER DEFAULT 0,
    memory_ids JSONB DEFAULT '[]',
    generated_context TEXT,
    is_template BOOLEAN DEFAULT FALSE,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.2 SQLAlchemy 模型

**文件**: `tools/memory-tool/app/db/models.py`

```python
"""Memory Tool Database Models."""
import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    Column, String, Text, DateTime, Float, Integer, 
    Boolean, JSON, ForeignKey, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, VECTOR
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class MemoryEntry(Base):
    """Memory entry with vector embedding support."""
    __tablename__ = "memory_entries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project = Column(String(100), index=True)
    category = Column(String(50), index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    
    memory_tier = Column(String(20), default="semantic", index=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("memory_entries.id"), nullable=True, index=True)
    confidence_score = Column(Float, default=1.0)
    
    embedding = Column(VECTOR(384), nullable=True)
    
    ai_suggested = Column(Boolean, default=False, index=True)
    ai_review_status = Column(String(20), default="approved")
    merged_from = Column(JSON, default=list)
    
    access_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime, nullable=True)
    
    source_type = Column(String(50), default="manual")
    source_uri = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    parent = relationship("MemoryEntry", remote_side=[id], back_populates="children")
    children = relationship("MemoryEntry", back_populates="parent", cascade="all, delete-orphan")
    outgoing_relations = relationship("MemoryRelation", foreign_keys="MemoryRelation.source_id", back_populates="source")
    incoming_relations = relationship("MemoryRelation", foreign_keys="MemoryRelation.target_id", back_populates="target")
    
    def to_dict(self, include_embedding: bool = False) -> dict:
        data = {
            "id": str(self.id),
            "project": self.project,
            "category": self.category,
            "title": self.title,
            "content": self.content[:500] + "..." if len(self.content) > 500 else self.content,
            "memory_tier": self.memory_tier,
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "confidence_score": self.confidence_score,
            "ai_suggested": self.ai_suggested,
            "access_count": self.access_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_embedding and self.embedding:
            data["embedding"] = self.embedding.tolist()
        return data


class MemoryRelation(Base):
    """Relationship between memories."""
    __tablename__ = "memory_relations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("memory_entries.id", ondelete="CASCADE"), nullable=False)
    target_id = Column(UUID(as_uuid=True), ForeignKey("memory_entries.id", ondelete="CASCADE"), nullable=False)
    relation_type = Column(String(50), nullable=False, index=True)
    strength = Column(Float, default=0.5)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    source = relationship("MemoryEntry", foreign_keys=[source_id], back_populates="outgoing_relations")
    target = relationship("MemoryEntry", foreign_keys=[target_id], back_populates="incoming_relations")
    
    __table_args__ = (UniqueConstraint('source_id', 'target_id', 'relation_type', name='unique_relation'),)


class ContextPackage(Base):
    """User-generated context packages."""
    __tablename__ = "context_packages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    project = Column(String(100), index=True)
    created_by = Column(String(100), nullable=True)
    total_tokens = Column(Integer, default=0)
    memory_ids = Column(JSON, default=list)
    generated_context = Column(Text, nullable=True)
    is_template = Column(Boolean, default=False, index=True)
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

---

## 4. API 设计

### 4.1 REST API 端点列表

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/memories | 列表查询 |
| POST | /api/memories | 创建记忆 |
| GET | /api/memories/{id} | 获取详情 |
| PUT | /api/memories/{id} | 更新 |
| DELETE | /api/memories/{id} | 删除 |
| POST | /api/memories/search/vector | 向量搜索 |
| POST | /api/memories/search/hybrid | 混合搜索 |
| GET | /api/memories/graph/data | 获取图谱数据 |
| GET | /api/memories/graph/neighbors/{id} | 获取邻居节点 |
| POST | /api/memories/relations | 创建关系 |
| POST | /api/memories/relations/auto-generate | 自动生成关系 |
| POST | /api/memories/context-packages/generate | 生成上下文 |
| GET | /api/memories/review/queue | 审核队列 |

### 4.2 Pydantic Schemas

**文件**: `tools/memory-tool/app/schemas/memory.py`

```python
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

class MemoryCreateRequest(BaseModel):
    project: Optional[str] = None
    category: str = Field(..., description="architecture|decision|pattern|issue|bug|other")
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    memory_tier: str = Field(default="semantic", description="episodic|semantic|procedural")
    parent_id: Optional[UUID] = None
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)

class MemoryResponse(BaseModel):
    id: UUID
    project: Optional[str]
    category: str
    title: str
    content: str
    memory_tier: str
    parent_id: Optional[UUID]
    confidence_score: float
    ai_suggested: bool
    access_count: int
    created_at: datetime

class GraphNode(BaseModel):
    id: str
    title: str
    category: str
    memory_tier: str
    confidence_score: float
    access_count: int
    radius: float = 5.0
    color: str = "#3b82f6"

class GraphLink(BaseModel):
    source: str
    target: str
    relation_type: str
    strength: float

class GraphDataResponse(BaseModel):
    nodes: List[GraphNode]
    links: List[GraphLink]
    total_nodes: int
    total_links: int

class VectorSearchRequest(BaseModel):
    query: str
    project: Optional[str] = None
    top_k: int = Field(default=10, ge=1, le=50)
    min_similarity: float = Field(default=0.7, ge=0.0, le=1.0)

class GenerateContextRequest(BaseModel):
    memory_ids: List[UUID]
    max_tokens: int = Field(default=2000, ge=100, le=8000)
    format: str = Field(default="markdown", description="markdown|json|xml")
```

---

## 5. 开发步骤

### Week 1: 后端开发

#### Day 1-2: 数据库迁移
- [ ] 执行 SQL 迁移脚本
- [ ] 更新 SQLAlchemy 模型
- [ ] 创建数据库迁移文件

#### Day 3-4: API 实现
- [ ] 实现 Memory CRUD API
- [ ] 实现 Vector Search API
- [ ] 实现 Graph Data API

#### Day 5: 关系管理
- [ ] 实现 MemoryRelation CRUD
- [ ] 实现 auto-generate relations
- [ ] 上下文包 API

### Week 2: 前端开发

#### Day 6-7: D3.js 图谱
- [ ] 实现 Force Simulation
- [ ] 节点渲染与交互
- [ ] 缩放/平移/点击事件

#### Day 8: 其他页面
- [ ] 记忆列表页
- [ ] 记忆详情页
- [ ] 审核队列页

#### Day 9: 上下文生成器
- [ ] Token 计算
- [ ] 记忆选择交互
- [ ] 上下文预览

#### Day 10: 测试与优化
- [ ] 集成测试
- [ ] 性能优化
- [ ] Bug 修复

---

## 6. 关键实现代码

### 6.1 向量搜索实现

```python
async def vector_search(
    query: str,
    project: Optional[str],
    top_k: int = 10,
    db: AsyncSession = Depends(get_db)
):
    # 1. 生成查询向量 (使用 text-embedding-3-small)
    embedding = await generate_embedding(query)
    
    # 2. 执行向量搜索
    sql = """
    SELECT id, title, content, embedding <=> :embedding as distance
    FROM memory_entries
    WHERE deleted_at IS NULL
    AND (:project IS NULL OR project = :project)
    ORDER BY embedding <=> :embedding
    LIMIT :top_k
    """
    
    results = await db.execute(
        text(sql),
        {"embedding": embedding, "project": project, "top_k": top_k}
    )
    
    return results.fetchall()
```

### 6.2 D3.js 图谱配置

```javascript
const simulation = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links).id(d => d.id).distance(100))
    .force("charge", d3.forceManyBody().strength(-300))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collision", d3.forceCollide().radius(d => d.radius + 5));

// 颜色映射
const colorScale = d3.scaleOrdinal()
    .domain(["architecture", "decision", "pattern", "issue", "bug"])
    .range(["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#dc2626"]);
```

### 6.3 Token 计算

```python
def estimate_tokens(text: str) -> int:
    # 简单估算: 1 token ≈ 4 字符 (英文)
    # 中文需要更复杂处理
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    other_chars = len(text) - chinese_chars
    
    # 中文字符占用更多 tokens
    return int(chinese_chars * 2 + other_chars / 4)
```

---

## 7. 部署配置

### 7.1 Docker Compose 更新

```yaml
# 在 docker-compose.yml 中添加 pgvector 支持
services:
  memory-tool:
    image: aidp/memory-tool:0.2.0
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/aidp
      - ENABLE_VECTOR_SEARCH=true
    depends_on:
      - postgres

  postgres:
    image: ankane/pgvector:latest
    environment:
      - POSTGRES_DB=aidp
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
```

### 7.2 数据库初始化

```bash
# 在 PostgreSQL 中启用 pgvector
docker exec -it novel-postgres psql -U novel_os -d aidp -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

---

## 8. 验收标准

- [ ] 支持 1000+ 记忆节点的图谱渲染
- [ ] 向量搜索响应时间 < 500ms
- [ ] Token 计算误差 < 10%
- [ ] 上下文包生成正确
- [ ] 审核队列正常工作
- [ ] 所有 API 通过测试

---

**文档版本**: v1.0  
**最后更新**: 2026-07-07  
**作者**: AIDP Team
