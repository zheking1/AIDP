# Knowledge Base Tool 开发计划

---

## 目录

1. [项目概述](#1-项目概述)
2. [技术选型](#2-技术选型)
3. [Phase 1: 基础索引](#3-phase-1-基础索引)
4. [Phase 2: Wiki 生成 + 知识图谱](#4-phase-2-wiki-生成--知识图谱)
5. [Phase 3: 文档-代码集成](#5-phase-3-文档-代码集成)
6. [Phase 4: 高级能力](#6-phase-4-高级能力)
7. [风险评估](#7-风险评估)
8. [资源需求](#8-资源需求)

---

## 1. 项目概述

### 1.1 项目范围

为 AIDP 系统构建 Knowledge Base Tool，提供文档知识库能力。

### 1.2 项目目标

- 支持 AI Agent 快速理解项目文档
- 自动维护文档与代码的关联
- 提供语义搜索能力
- 检测文档过期并告警

### 1.3 项目周期

- Phase 1: 2 周（基础索引）
- Phase 2: 2 周（Wiki 生成 + 知识图谱）
- Phase 3: 2 周（文档-代码集成）
- Phase 4: 1 周（高级能力）
- **总计: 7 周**

---

## 2. 技术选型

| 组件 | 技术 | 理由 |
|------|------|------|
| **语言** | Python 3.13 | 统一技术栈 |
| **Web 框架** | FastAPI | 异步、高性能 |
| **存储** | SQLite + FTS5 | 零依赖、本地性能好 |
| **向量存储** | LanceDB | 嵌入式、高性能 |
| **模板引擎** | Jinja2 | 与现有工具一致 |
| **前端** | Alpine.js + Tailwind CSS | 轻量级 |
| **LLM** | OpenAI 兼容 API | 灵活性 |
| **图谱** | NetworkX | 纯 Python |
| **社区检测** | python-louvain | 成熟算法 |

---

## 3. Phase 1: 基础索引（P0）

**周期**: 2 周（10-12 天）

### 3.1 目标

能导入文档并建立基础索引。

### 3.2 任务清单

| 任务 | 估时 | 依赖 |
|------|------|------|
| 项目结构搭建 | 1 天 | 无 |
| SQLite + FTS5 存储层 | 2 天 | 无 |
| 文档导入模块 | 2 天 | 存储层 |
| SHA256 增量缓存 | 1 天 | 存储层 |
| 持久化摄入队列 | 2 天 | 存储层 |
| 基础搜索 API | 1 天 | 存储层 |
| Web UI（文档列表、导入、搜索） | 2 天 | API |
| 测试 | 1 天 | 全部 |

### 3.3 技术实现

**存储层**:
```python
# app/db/models.py
class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    doc_type = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    content = Column(Text)
    checksum = Column(String, nullable=False)
    directory_path = Column(String)
    metadata = Column(JSON, default={})
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
```

**增量缓存**:
```python
# app/services/cache_service.py
class CacheService:
    async def should_ingest(self, file_path: str) -> bool:
        """检查文件是否需要导入"""
        current_checksum = await self.compute_checksum(file_path)
        stored_checksum = await self.get_stored_checksum(file_path)
        return current_checksum != stored_checksum
```

**持久化队列**:
```python
# app/services/queue_service.py
class QueueService:
    async def enqueue(self, task: IngestTask):
        """添加任务到队列"""
        await db.execute("""
            INSERT INTO ingest_queue (task_type, document_id, status, priority)
            VALUES (?, ?, 'pending', ?)
        """, (task.type, task.document_id, task.priority))
    
    async def process_queue(self):
        """处理队列"""
        while True:
            task = await self.get_next_task()
            if task:
                await self.execute_task(task)
            else:
                await asyncio.sleep(1)
```

### 3.4 验收标准

- [ ] 能导入 Markdown 文件
- [ ] 能导入代码文件（提取注释）
- [ ] 能搜索文档（FTS5）
- [ ] 能显示文档列表
- [ ] 能显示摄入进度
- [ ] 增量导入跳过未变更文件

---

## 4. Phase 2: Wiki 生成 + 知识图谱（P1）

**周期**: 2 周（10-12 天）

### 4.1 目标

LLM 自动生成 Wiki + 知识图谱。

### 4.2 任务清单

| 任务 | 估时 | 依赖 |
|------|------|------|
| 两步思维链摄入引擎 | 3 天 | Phase 1 |
| Wiki 页面生成 | 2 天 | 摄入引擎 |
| 四信号知识图谱 | 2 天 | Wiki 页面 |
| Louvain 社区检测 | 1 天 | 图谱 |
| 知识图谱可视化（D3.js） | 2 天 | 图谱 |
| Web UI（Wiki、图谱、审核） | 2 天 | 全部 |
| 测试 | 1 天 | 全部 |

### 4.3 技术实现

**两步摄入**:
```python
# app/services/ingest_service.py
class IngestService:
    async def ingest(self, document: Document) -> IngestResult:
        """两步摄入"""
        # Step 1: 分析
        analysis = await self.analyze(document)
        
        # Step 2: 生成
        wiki_pages = await self.generate(document, analysis)
        
        # 保存
        await self.save(wiki_pages)
        
        # 更新图谱
        await self.update_graph(wiki_pages)
        
        return IngestResult(pages_generated=len(wiki_pages))
    
    async def analyze(self, document: Document) -> Analysis:
        """Step 1: LLM 分析"""
        prompt = f"""
        分析以下文档，提取结构化信息：
        
        文档内容：
        {document.content}
        
        已有 Wiki 页面：
        {await self.get_existing_wiki()}
        
        请提取：
        1. 关键实体（类、函数、API 端点）
        2. 核心概念（设计模式、架构概念）
        3. 与现有 Wiki 的关联
        4. 与现有知识的矛盾
        5. Wiki 结构建议
        """
        
        response = await self.llm.call(prompt)
        return Analysis.parse(response)
```

**四信号图谱**:
```python
# app/services/graph_service.py
class GraphService:
    WEIGHTS = {
        "direct_link": 3.0,
        "source_overlap": 2.0,
        "adamic_adar": 1.0,
        "type_affinity": 1.5
    }
    
    async def compute_relevance(self, page_a: WikiPage, page_b: WikiPage) -> float:
        """计算两个页面的关联度"""
        score = 0.0
        
        if await self.has_direct_link(page_a, page_b):
            score += self.WEIGHTS["direct_link"]
        
        overlap = await self.source_overlap(page_a, page_b)
        score += overlap * self.WEIGHTS["source_overlap"]
        
        aa = await self.adamic_adar(page_a, page_b)
        score += aa * self.WEIGHTS["adamic_adar"]
        
        if await self.types_are_compatible(page_a, page_b):
            score += self.WEIGHTS["type_affinity"]
        
        return score
```

### 4.4 验收标准

- [ ] 能自动生成 Wiki 页面
- [ ] Wiki 页面带 frontmatter
- [ ] 能构建知识图谱
- [ ] 能检测社区
- [ ] 能可视化图谱
- [ ] 审核系统工作

---

## 5. Phase 3: 文档-代码集成（P2）

**周期**: 2 周（10-12 天）

### 5.1 目标

文档与代码链接 + 过期检测。

### 5.2 任务清单

| 任务 | 估时 | 依赖 |
|------|------|------|
| 文档-代码链接器 | 2 天 | Phase 2 |
| 从文档提取代码引用 | 2 天 | 链接器 |
| 文档过期检测 | 2 天 | 链接器 |
| 与 code-index-tool 集成 | 2 天 | 过期检测 |
| 语义搜索（LanceDB） | 2 天 | Phase 1 |
| Web UI（过期列表、链接详情） | 1 天 | 全部 |
| 测试 | 1 天 | 全部 |

### 5.3 技术实现

**文档-代码链接器**:
```python
# app/services/code_linker.py
class CodeLinker:
    async def link_document_to_code(self, document: Document, code_index: CodeIndex):
        """链接文档与代码"""
        links = []
        
        # 1. 从文档提取代码引用
        code_refs = await self.extract_code_references(document)
        
        # 2. 在代码索引中查找匹配
        for ref in code_refs:
            matches = await code_index.search_symbol(ref.name)
            
            for match in matches:
                link = Link(
                    document_id=document.id,
                    code_node_id=match.id,
                    link_type=ref.type,
                    confidence=match.score
                )
                links.append(link)
        
        # 3. 保存链接
        await self.save_links(links)
        
        return links
    
    async def detect_drift(self, document: Document, code_index: CodeIndex) -> List[Drift]:
        """检测文档过期"""
        drifts = []
        
        links = await self.get_document_links(document.id)
        
        for link in links:
            code_node = await code_index.get_node(link.code_node_id)
            
            if not code_node:
                drifts.append(Drift(
                    document_id=document.id,
                    drift_type="code_deleted",
                    description=f"代码 {link.code_name} 已删除",
                    severity="high"
                ))
            elif self.is_signature_changed(code_node, link.expected_signature):
                drifts.append(Drift(
                    document_id=document.id,
                    drift_type="signature_changed",
                    description=f"代码 {link.code_name} 签名已变更",
                    severity="medium"
                ))
        
        return drifts
```

### 5.4 验收标准

- [ ] 能创建文档-代码链接
- [ ] 能检测文档过期
- [ ] 能与 code-index-tool 联动
- [ ] 语义搜索工作
- [ ] 过期告警显示

---

## 6. Phase 4: 高级能力（P3）

**周期**: 1 周（5-7 天）

### 6.1 目标

深度研究 + PDF + Chrome 剪藏。

### 6.2 任务清单

| 任务 | 估时 | 依赖 |
|------|------|------|
| 深度研究（LLM 生成搜索主题） | 2 天 | Phase 2 |
| PDF 导入 | 2 天 | Phase 1 |
| Chrome 剪藏 API | 1 天 | Phase 1 |
| 多模态图片摄入 | 1 天 | Phase 2 |
| 性能优化 | 1 天 | 全部 |

### 6.3 验收标准

- [ ] 深度研究工作
- [ ] PDF 导入工作
- [ ] Chrome 剪藏工作
- [ ] 图片摄入工作

---

## 7. 风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| **LLM 质量不稳定** | 中 | 高 | 使用多模型对比、人工审核 |
| **大文档处理慢** | 高 | 中 | 分块处理、异步队列 |
| **索引体积过大** | 中 | 中 | 增量索引、压缩 |
| **code-index-tool 未完成** | 低 | 高 | 设计为可选依赖 |

---

## 8. 资源需求

### 8.1 开发资源

| 资源 | 数量 | 说明 |
|------|------|------|
| **开发人员** | 1-2 人 | Python + FastAPI |
| **开发环境** | 1 套 | 本地开发 |
| **测试环境** | 1 套 | NAS 部署 |

### 8.2 基础设施

| 资源 | 规格 | 说明 |
|------|------|------|
| **NAS** | 192.168.0.100 | 部署环境 |
| **PostgreSQL** | 127.0.0.1:5432 | 结构化存储 |
| **Redis** | 192.168.0.100:6379 | 缓存 |
| **LLM** | OpenAI 兼容 | Wiki 生成 |

### 8.3 依赖关系

| 依赖 | 版本 | 说明 |
|------|------|------|
| **Python** | 3.13 | 运行环境 |
| **FastAPI** | latest | Web 框架 |
| **SQLite** | 3.x | 存储 |
| **LanceDB** | latest | 向量存储 |
| **NetworkX** | latest | 图谱 |
| **python-louvain** | latest | 社区检测 |
