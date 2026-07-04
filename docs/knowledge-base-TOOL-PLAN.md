# Knowledge Base Tool 规划文档

为大型项目提供文档知识库，链接代码与文档

---

## 目录

1. [定位与目标](#1-定位与目标)
2. [核心能力模型](#2-核心能力模型)
3. [架构设计](#3-架构设计)
4. [数据模型](#4-数据模型)
5. [API 设计](#5-api-设计)
6. [Web UI 设计](#6-web-ui-设计)
7. [与 code-index-tool 集成](#7-与-code-index-tool-集成)
8. [参考项目](#8-参考项目)
9. [实施计划](#9-实施计划)

---

## 1. 定位与目标

### 1.1 工具定位

**Knowledge Base Tool** 是 AIDP 工具链中的**文档知识引擎**，负责：

- 索引项目文档（README、API 文档、架构文档、注释）
- 自动生成 Wiki 页面（两步思维链摄入）
- 构建知识图谱（文档间的关联关系）
- 链接文档与代码（文档→函数/类/API 端点）
- 检测文档过期（文档与代码不匹配）
- 提供语义搜索能力

### 1.2 目标用户

| 用户 | 场景 | 期望效果 |
|------|------|----------|
| AI Agent | "用户认证怎么实现" | 返回相关文档 + 代码位置 |
| AI Agent | "这个 API 怎么调用" | 返回 API 文档 + 示例代码 |
| AI Agent | "修改这个函数会影响什么文档" | 返回受影响的文档列表 |
| 开发者 | 理解项目架构 | 可视化知识图谱 |
| 开发者 | 查找过期文档 | 文档与代码不匹配告警 |

### 1.3 与其他工具的关系

```
┌─────────────────────────────────────────────────────────────┐
│                    Skill Router                              │
│                    (任务路由)                                │
└───────────────┬─────────────────────────────────────────────┘
                │
    ┌───────────┼───────────┬───────────┬───────────┐
    ▼           ▼           ▼           ▼           ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│Knowledge│ │ Asset  │ │ Memory │ │Quality │ │ CODE   │
│  Tool  │ │  Tool  │ │  Tool  │ │  Tool  │ │ INDEX  │
│(文档)  │ │(片段)  │ │(经验)  │ │(检查)  │ │(结构)  │
└────────┘ └────────┘ └────────┘ └────────┘ └────────┘
     │                                          │
     │         ┌─────────────────┐              │
     └────────►│  Code Linker    │◄─────────────┘
               │                 │
               │  文档 ↔ 代码    │
               │  过期检测       │
               └─────────────────┘
```

### 1.4 设计来源

| 来源 | 借鉴内容 | 价值 |
|------|----------|------|
| **LLM Wiki** | 两步思维链摄入、四信号知识图谱、Louvain 社区检测 | 高质量文档生成 |
| **LLM Wiki** | 持久化摄入队列、来源可追溯、增量缓存 | 可靠性 |
| **codebase-memory-mcp** | Tree-sitter 解析、知识图谱、Cypher 查询 | 代码感知 |
| **CodeGraph** | 单一强工具、SQLite + FTS5 | 查询性能 |

---

## 2. 核心能力模型

### 2.1 能力矩阵

| 能力 | 描述 | 输入 | 输出 | 优先级 | 来源 |
|------|------|------|------|--------|------|
| **文档导入** | 导入 Markdown/PDF/代码文件 | 文件路径 | 文档列表 | P0 | LLM Wiki |
| **两步摄入** | LLM 分析→生成 Wiki | 文档 | Wiki 页面 | P0 | LLM Wiki |
| **增量缓存** | SHA256 去重，跳过未变更文件 | 文件 | 缓存状态 | P0 | LLM Wiki |
| **持久化队列** | 崩溃恢复、进度可视化 | 任务 | 队列状态 | P0 | LLM Wiki |
| **知识图谱** | 四信号关联度模型 | Wiki 页面 | 图谱边 | P1 | LLM Wiki |
| **社区检测** | Louvain 算法发现知识聚类 | 图谱 | 社区划分 | P1 | LLM Wiki |
| **向量搜索** | 语义搜索 Wiki 页面 | 查询 | 匹配结果 | P1 | LLM Wiki |
| **来源追溯** | Wiki 页面链接回源文件 | Wiki 页面 | 源文件列表 | P1 | LLM Wiki |
| **文档-代码链接** | 文档→函数/类/API 端点 | 文档 | 链接关系 | P1 | 新增 |
| **文档过期检测** | 文档与代码不匹配告警 | 文档+代码 | 过期列表 | P1 | 新增 |
| **Web UI** | 浏览器维护文档 | 用户操作 | 页面渲染 | P1 | 新增 |
| **深度研究** | LLM 生成搜索主题，自动摄入 | 查询 | 研究文档 | P2 | LLM Wiki |
| **审核系统** | LLM 标记需人工判断的项 | 摄入结果 | 审核队列 | P2 | LLM Wiki |
| **Chrome 剪藏** | 一键捕获网页内容 | 网页 URL | 文档 | P2 | LLM Wiki |

### 2.2 支持的文档类型

**Phase 1（核心）：**
- Markdown（.md）
- 代码注释（JavaDoc、docstring、JSDoc）
- API 文档（OpenAPI/Swagger）

**Phase 2（扩展）：**
- PDF 文档
- Word 文档（.docx）
- 纯文本（.txt）

**Phase 3（全量）：**
- 图片（多模态摄入）
- 网页（Chrome 剪藏）

### 2.3 ruoyi-cloud-plus 场景示例

```
项目: ruoyi-cloud-plus (Spring Cloud 微服务)

文档结构:
├── README.md                    ← 项目概述
├── docs/
│   ├── architecture.md          ← 架构设计
│   ├── api/
│   │   ├── auth-api.md          ← 认证 API
│   │   └── user-api.md          ← 用户 API
│   └── deployment.md            ← 部署指南
├── ruoyi-auth/
│   ├── README.md                ← 模块说明
│   └── src/main/java/.../
│       ├── AuthController.java  ← 含 JavaDoc
│       └── AuthService.java     ← 含 JavaDoc
└── ruoyi-system/
    ├── README.md                ← 模块说明
    └── src/main/java/.../
        └── SysUserController.java ← 含 JavaDoc

AI 查询示例:
Q: "用户认证流程"
→ 文档: docs/api/auth-api.md, ruoyi-auth/README.md
→ 代码: AuthController.java:login(), AuthService.java:authenticate()
→ 图谱: 认证相关文档聚类
→ 过期: auth-api.md 中的 oldEndpoint() 已不存在
```

---

## 3. 架构设计

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Knowledge Base Tool                       │
│                    Port: 18087                               │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                    Web Layer                             │ │
│  │                                                         │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │ │
│  │  │  Dashboard  │  │  Documents  │  │  Wiki       │    │ │
│  │  │  统计概览   │  │  文档管理   │  │  Wiki 管理  │    │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘    │ │
│  │                                                         │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │ │
│  │  │  Search     │  │  Graph      │  │  Review     │    │ │
│  │  │  搜索界面   │  │  图谱可视化 │  │  审核系统   │    │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘    │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                    Engine Layer                          │ │
│  │                                                         │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │ │
│  │  │  Ingest     │  │  Graph      │  │  Search     │    │ │
│  │  │  Engine     │  │  Engine     │  │  Engine     │    │ │
│  │  │             │  │             │  │             │    │ │
│  │  │  Two-step   │  │  4-signal   │  │  FTS5 +     │    │ │
│  │  │  Chain-of-  │  │  relevance  │  │  Vector     │    │ │
│  │  │  Thought    │  │  Louvain    │  │  LanceDB    │    │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘    │ │
│  │                                                         │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │ │
│  │  │  Code       │  │  Drift      │  │  Queue      │    │ │
│  │  │  Linker     │  │  Detector   │  │  Manager    │    │ │
│  │  │             │  │             │  │             │    │ │
│  │  │  doc→code   │  │  doc vs     │  │  persistent │    │ │
│  │  │  code→doc   │  │  code       │  │  retry      │    │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘    │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                    Storage Layer                         │ │
│  │                                                         │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │ │
│  │  │  SQLite     │  │  LanceDB    │  │  File       │    │ │
│  │  │  + FTS5     │  │  (向量)     │  │  System     │    │ │
│  │  │             │  │             │  │             │    │ │
│  │  │  结构化数据  │  │  语义搜索   │  │  Wiki 文件  │    │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘    │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                    MCP Layer                             │ │
│  │                                                         │ │
│  │  - knowledge.search: 语义搜索文档                       │ │
│  │  - knowledge.graph: 知识图谱查询                        │ │
│  │  - knowledge.ingest: 触发文档摄入                       │ │
│  │  - knowledge.drift: 文档过期检测                        │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 处理流程（借鉴 LLM Wiki）

```
┌─────────────────────────────────────────────────────────────┐
│                    两步思维链摄入 Pipeline                     │
│                                                               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │
│  │  Import     │───▶│  Analyze    │───▶│  Generate   │      │
│  │  (导入)     │    │  (分析)     │    │  (生成)     │      │
│  └─────────────┘    └─────────────┘    └─────────────┘      │
│        │                  │                  │               │
│        ▼                  ▼                  ▼               │
│  文件类型检测        LLM 结构化分析     LLM 生成 Wiki       │
│  SHA256 缓存         实体/概念提取      frontmatter         │
│  目录结构保留        关联发现           交叉引用             │
│                                           │                 │
│                                           ▼                 │
│                                    ┌─────────────┐         │
│                                    │  Link       │         │
│                                    │  (链接)     │         │
│                                    └─────────────┘         │
│                                           │                 │
│                                           ▼                 │
│                                    文档 ↔ 代码链接          │
│                                    知识图谱更新              │
│                                    过期检测                  │
└─────────────────────────────────────────────────────────────┘
```

**四个阶段详解：**

| 阶段 | 描述 | 输入 | 输出 |
|------|------|------|------|
| **Import** | 导入文档，计算 SHA256，保留目录结构 | 文件 | 文档记录 |
| **Analyze** | LLM 分析文档，提取实体、概念、关联 | 文档 | 结构化分析 |
| **Generate** | LLM 基于分析生成 Wiki 页面 | 分析结果 | Wiki 页面 |
| **Link** | 链接文档与代码，更新知识图谱 | 文档+代码 | 链接关系 |

### 3.3 引擎层设计

#### 3.3.1 两步摄入引擎（借鉴 LLM Wiki）

```python
class TwoStepIngestEngine:
    """两步思维链摄入引擎"""
    
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
        
        return IngestResult(
            pages_generated=len(wiki_pages),
            review_items=analysis.review_items,
            search_queries=analysis.search_queries
        )
    
    async def analyze(self, document: Document) -> Analysis:
        """Step 1: LLM 分析文档"""
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
        6. 需要人工判断的项（审核项）
        7. 建议的搜索查询（深度研究）
        """
        
        response = await self.llm.call(prompt)
        return Analysis.parse(response)
    
    async def generate(self, document: Document, analysis: Analysis) -> List[WikiPage]:
        """Step 2: LLM 生成 Wiki 页面"""
        prompt = f"""
        基于以下分析，生成 Wiki 页面：
        
        原始文档：
        {document.content}
        
        分析结果：
        {analysis.to_prompt()}
        
        请生成：
        1. 资料摘要页面（带 frontmatter）
        2. 实体页面（类、函数、API）
        3. 概念页面
        4. 更新 index.md
        5. 更新 log.md
        6. 更新 overview.md
        """
        
        response = await self.llm.call(prompt)
        return WikiPage.parse_all(response)
```

#### 3.3.2 四信号知识图谱（借鉴 LLM Wiki）

```python
class FourSignalGraph:
    """四信号知识图谱"""
    
    # 信号权重
    WEIGHTS = {
        "direct_link": 3.0,      # [[wikilinks]] 直接链接
        "source_overlap": 2.0,   # 共享源文件
        "adamic_adar": 1.0,      # Adamic-Adar 指数
        "type_affinity": 1.5     # 类型亲和度
    }
    
    async def compute_relevance(self, page_a: WikiPage, page_b: WikiPage) -> float:
        """计算两个页面的关联度"""
        score = 0.0
        
        # 信号 1: 直接链接
        if await self.has_direct_link(page_a, page_b):
            score += self.WEIGHTS["direct_link"]
        
        # 信号 2: 来源重叠
        overlap = await self.source_overlap(page_a, page_b)
        score += overlap * self.WEIGHTS["source_overlap"]
        
        # 信号 3: Adamic-Adar
        aa = await self.adamic_adar(page_a, page_b)
        score += aa * self.WEIGHTS["adamic_adar"]
        
        # 信号 4: 类型亲和度
        if await self.types_are_compatible(page_a, page_b):
            score += self.WEIGHTS["type_affinity"]
        
        return score
    
    async def adamic_adar(self, page_a: WikiPage, page_b: WikiPage) -> float:
        """Adamic-Adar 指数"""
        # 共同邻居
        neighbors_a = await self.get_neighbors(page_a)
        neighbors_b = await self.get_neighbors(page_b)
        common = set(neighbors_a) & set(neighbors_b)
        
        # 计算 Adamic-Adar
        score = 0.0
        for neighbor in common:
            degree = await self.get_degree(neighbor)
            if degree > 0:
                score += 1.0 / math.log(degree)
        
        return score
```

#### 3.3.3 文档-代码链接器（新增）

```python
class CodeLinker:
    """文档-代码链接器"""
    
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
                    link_type=ref.type,  # reference/usage/example
                    confidence=match.score
                )
                links.append(link)
        
        # 3. 保存链接
        await self.save_links(links)
        
        return links
    
    async def extract_code_references(self, document: Document) -> List[CodeRef]:
        """从文档提取代码引用"""
        refs = []
        
        # 匹配 JavaDoc 风格
        # 匹配 Markdown 代码块
        # 匹配函数调用
        # 匹配类名引用
        
        return refs
    
    async def detect_drift(self, document: Document, code_index: CodeIndex) -> List[Drift]:
        """检测文档过期"""
        drifts = []
        
        # 获取文档链接的代码
        links = await self.get_document_links(document.id)
        
        for link in links:
            # 检查代码是否还存在
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

#### 3.3.4 持久化队列管理器（借鉴 LLM Wiki）

```python
class PersistentQueueManager:
    """持久化队列管理器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.processing = False
    
    async def enqueue(self, task: IngestTask):
        """添加任务到队列"""
        await db.execute("""
            INSERT INTO ingest_queue (task_type, document_id, status, priority)
            VALUES (?, ?, 'pending', ?)
        """, (task.type, task.document_id, task.priority))
    
    async def process_queue(self):
        """处理队列"""
        while True:
            # 获取下一个任务
            task = await db.fetch_one("""
                SELECT * FROM ingest_queue
                WHERE status = 'pending'
                ORDER BY priority DESC, created_at ASC
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            """)
            
            if not task:
                await asyncio.sleep(1)
                continue
            
            # 标记为处理中
            await db.execute("""
                UPDATE ingest_queue SET status = 'processing'
                WHERE id = ?
            """, (task["id"],))
            
            try:
                # 执行任务
                await self.execute_task(task)
                
                # 标记为完成
                await db.execute("""
                    UPDATE ingest_queue SET status = 'completed'
                    WHERE id = ?
                """, (task["id"],))
            except Exception as e:
                # 标记为失败，增加重试次数
                await db.execute("""
                    UPDATE ingest_queue
                    SET status = 'failed',
                        error_message = ?,
                        retry_count = retry_count + 1
                    WHERE id = ?
                """, (str(e), task["id"]))
                
                # 如果重试次数 < 3，重新入队
                if task["retry_count"] < 3:
                    await db.execute("""
                        UPDATE ingest_queue SET status = 'pending'
                        WHERE id = ?
                    """, (task["id"],))
    
    async def get_progress(self) -> QueueProgress:
        """获取队列进度"""
        total = await db.fetch_one("SELECT COUNT(*) as cnt FROM ingest_queue")
        pending = await db.fetch_one("SELECT COUNT(*) as cnt FROM ingest_queue WHERE status = 'pending'")
        processing = await db.fetch_one("SELECT COUNT(*) as cnt FROM ingest_queue WHERE status = 'processing'")
        completed = await db.fetch_one("SELECT COUNT(*) as cnt FROM ingest_queue WHERE status = 'completed'")
        failed = await db.fetch_one("SELECT COUNT(*) as cnt FROM ingest_queue WHERE status = 'failed'")
        
        return QueueProgress(
            total=total["cnt"],
            pending=pending["cnt"],
            processing=processing["cnt"],
            completed=completed["cnt"],
            failed=failed["cnt"]
        )
```

### 3.4 部署模式

**独立服务（推荐）：**
```
http://192.168.0.100:18087/  # Knowledge Base Tool
├── /                         # Web UI
├── /api/documents/*          # 文档管理
├── /api/wiki/*               # Wiki 管理
├── /api/search/*             # 搜索接口
├── /api/graph/*              # 图谱接口
├── /api/ingest/*             # 摄入管理
├── /mcp/                     # MCP Server
└── /health                   # 健康检查
```

---

## 4. 数据模型

### 4.1 存储方案

**选择 SQLite + FTS5 + LanceDB：**

| 维度 | SQLite + FTS5 | PostgreSQL |
|------|---------------|------------|
| **部署** | 零依赖，单文件 | 需要安装服务 |
| **性能** | 本地 I/O，极快 | 网络开销 |
| **全文搜索** | FTS5 内置 | 需要 pg_trgm |
| **向量搜索** | LanceDB 嵌入式 | 需要 pgvector |

**文件结构：**
```
.knowledge/
├── knowledge.db          # 主数据库
├── knowledge.db-wal      # WAL 日志
├── knowledge.db-shm      # 共享内存
├── vectors.lance/        # 向量索引
├── wiki/                 # Wiki 文件
│   ├── index.md
│   ├── overview.md
│   ├── log.md
│   └── pages/
└── sources/              # 原始文档
```

### 4.2 核心表结构

```sql
-- 文档表
CREATE TABLE documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    doc_type TEXT NOT NULL,        -- markdown/pdf/code/text
    file_path TEXT NOT NULL,
    content TEXT,
    checksum TEXT NOT NULL,
    directory_path TEXT,           -- 目录结构
    metadata TEXT DEFAULT '{}',    -- JSON 扩展字段
    status TEXT DEFAULT 'pending', -- pending/indexed/failed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Wiki 页面表
CREATE TABLE wiki_pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    page_type TEXT NOT NULL,       -- summary/entity/concept/index/log
    content TEXT,
    frontmatter TEXT DEFAULT '{}', -- YAML frontmatter
    document_id INTEGER REFERENCES documents(id),
    file_path TEXT,
    checksum TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 文档-代码链接表
CREATE TABLE code_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id),
    code_node_id INTEGER NOT NULL,
    code_name TEXT NOT NULL,
    link_type TEXT NOT NULL,       -- reference/usage/example
    confidence FLOAT DEFAULT 0.0,
    expected_signature TEXT,       -- 期望的代码签名
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 文档过期表
CREATE TABLE document_drifts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id),
    drift_type TEXT NOT NULL,      -- code_deleted/signature_changed/api_changed
    description TEXT,
    severity TEXT DEFAULT 'medium', -- low/medium/high
    resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 摄入队列表
CREATE TABLE ingest_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type TEXT NOT NULL,        -- ingest/reindex/delete
    document_id INTEGER REFERENCES documents(id),
    status TEXT DEFAULT 'pending', -- pending/processing/completed/failed
    priority INTEGER DEFAULT 0,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 知识图谱节点表
CREATE TABLE graph_nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_type TEXT NOT NULL,       -- document/entity/concept
    name TEXT NOT NULL,
    wiki_page_id INTEGER REFERENCES wiki_pages(id),
    metadata TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 知识图谱边表
CREATE TABLE graph_edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL REFERENCES graph_nodes(id),
    target_id INTEGER NOT NULL REFERENCES graph_nodes(id),
    edge_type TEXT NOT NULL,       -- link/reference/similarity
    weight FLOAT DEFAULT 1.0,
    signal TEXT,                   -- direct_link/source_overlap/adamic_adar/type_affinity
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 审核表
CREATE TABLE review_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER REFERENCES documents(id),
    item_type TEXT NOT NULL,       -- contradiction/uncertainty/improvement
    description TEXT,
    suggested_action TEXT,
    status TEXT DEFAULT 'pending', -- pending/approved/rejected
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.3 FTS5 全文搜索索引

```sql
-- 文档搜索索引
CREATE VIRTUAL TABLE documents_fts USING fts5(
    title,
    content,
    file_path,
    content=documents,
    content_rowid=id
);

-- Wiki 搜索索引
CREATE VIRTUAL TABLE wiki_pages_fts USING fts5(
    title,
    content,
    frontmatter,
    content=wiki_pages,
    content_rowid=id
);

-- 触发器：保持 FTS 索引同步
CREATE TRIGGER documents_ai AFTER INSERT ON documents BEGIN
    INSERT INTO documents_fts(rowid, title, content, file_path)
    VALUES (new.id, new.title, new.content, new.file_path);
END;

CREATE TRIGGER wiki_pages_ai AFTER INSERT ON wiki_pages BEGIN
    INSERT INTO wiki_pages_fts(rowid, title, content, frontmatter)
    VALUES (new.id, new.title, new.content, new.frontmatter);
END;
```

### 4.4 性能索引

```sql
-- 文档查询索引
CREATE INDEX idx_documents_type ON documents(doc_type);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_checksum ON documents(checksum);
CREATE INDEX idx_documents_directory ON documents(directory_path);

-- Wiki 页面查询索引
CREATE INDEX idx_wiki_pages_type ON wiki_pages(page_type);
CREATE INDEX idx_wiki_pages_document ON wiki_pages(document_id);

-- 链接查询索引
CREATE INDEX idx_code_links_document ON code_links(document_id);
CREATE INDEX idx_code_links_code ON code_links(code_node_id);

-- 过期查询索引
CREATE INDEX idx_drifts_document ON document_drifts(document_id);
CREATE INDEX idx_drifts_resolved ON document_drifts(resolved);

-- 队列查询索引
CREATE INDEX idx_queue_status ON ingest_queue(status);
CREATE INDEX idx_queue_priority ON ingest_queue(priority DESC, created_at ASC);

-- 图谱查询索引
CREATE INDEX idx_graph_nodes_type ON graph_nodes(node_type);
CREATE INDEX idx_graph_edges_source ON graph_edges(source_id);
CREATE INDEX idx_graph_edges_target ON graph_edges(target_id);
```

---

## 5. API 设计

### 5.1 单一强工具设计

**核心理念：** 一个 `knowledge.explore` 工具做所有事，Agent 不需要选择工具。

```yaml
# tool.yaml
name: knowledge-base
version: 0.1.0
description: 文档知识库 - 一个工具探索整个项目文档
transport: http

capabilities:
  - name: knowledge.explore
    description: |
      文档知识库探索的唯一入口。支持：
      - 文档搜索（关键词 + 语义）
      - Wiki 页面查询
      - 知识图谱遍历
      - 文档过期检测
      - 触发文档摄入
    endpoint: POST /api/explore
    permission: knowledge:explore
```

### 5.2 统一探索 API

```
POST /api/explore
```

**请求类型：**

```json
// 1. 文档搜索
{
    "action": "search_documents",
    "query": "用户认证",
    "filters": {
        "doc_type": "markdown",
        "directory": "docs/api"
    }
}

// 2. Wiki 搜索
{
    "action": "search_wiki",
    "query": "AuthController",
    "filters": {
        "page_type": "entity"
    }
}

// 3. 知识图谱查询
{
    "action": "graph_query",
    "node_id": 101,
    "depth": 2,
    "edge_types": ["link", "reference"]
}

// 4. 文档过期检测
{
    "action": "detect_drift",
    "document_id": 50
}

// 5. 触发摄入
{
    "action": "ingest",
    "document_path": "docs/api/auth-api.md"
}

// 6. 获取文档详情
{
    "action": "get_document",
    "document_id": 50
}

// 7. 获取 Wiki 页面
{
    "action": "get_wiki_page",
    "page_id": 201
}

// 8. 文档统计
{
    "action": "stats"
}
```

**响应格式：**

```json
{
    "success": true,
    "data": {
        "results": [...],
        "total": 10,
        "took_ms": 45
    }
}
```

### 5.3 REST API

```
# 文档管理
POST   /api/documents              # 导入文档
GET    /api/documents              # 文档列表
GET    /api/documents/{id}         # 文档详情
PUT    /api/documents/{id}         # 更新文档
DELETE /api/documents/{id}         # 删除文档

# Wiki 管理
GET    /api/wiki/pages             # Wiki 页面列表
GET    /api/wiki/pages/{id}        # Wiki 页面详情
GET    /api/wiki/index             # 获取 index.md
GET    /api/wiki/overview          # 获取 overview.md
GET    /api/wiki/log               # 获取 log.md

# 搜索
POST   /api/search/documents       # 搜索文档
POST   /api/search/wiki            # 搜索 Wiki
POST   /api/search/semantic        # 语义搜索

# 图谱
GET    /api/graph/nodes            # 图谱节点
GET    /api/graph/edges            # 图谱边
GET    /api/graph/neighbors/{id}   # 节点邻居
GET    /api/graph/communities      # 社区检测

# 摄入
POST   /api/ingest/document        # 摄入单个文档
POST   /api/ingest/folder          # 摄入整个文件夹
GET    /api/ingest/progress        # 摄入进度
POST   /api/ingest/cancel/{id}     # 取消摄入
POST   /api/ingest/retry/{id}      # 重试摄入

# 过期检测
GET    /api/drift                  # 过期列表
POST   /api/drift/detect           # 触发过期检测
POST   /api/drift/resolve/{id}     # 标记已解决

# 审核
GET    /api/review                 # 审核列表
POST   /api/review/{id}/approve    # 审核通过
POST   /api/review/{id}/reject     # 审核拒绝

# 内部 API（code-index-tool 调用）
POST   /api/internal/link          # 创建文档-代码链接
GET    /api/internal/document/{id}/code  # 获取文档关联的代码
GET    /api/internal/code/{id}/document  # 获取代码关联的文档
```

### 5.4 MCP 工具定义

```yaml
# tool.yaml
name: knowledge-base
version: 0.1.0
description: 文档知识库，提供文档索引、Wiki 生成、知识图谱、过期检测能力
transport: http

capabilities:
  - name: knowledge.search
    description: 搜索文档和 Wiki
    endpoint: POST /api/search
    permission: knowledge:search
    
  - name: knowledge.graph
    description: 查询知识图谱
    endpoint: POST /api/graph
    permission: knowledge:graph
    
  - name: knowledge.ingest
    description: 触发文档摄入
    endpoint: POST /api/ingest
    permission: knowledge:ingest
    
  - name: knowledge.drift
    description: 检测文档过期
    endpoint: POST /api/drift
    permission: knowledge:drift
    
  - name: knowledge.link
    description: 查询文档-代码链接
    endpoint: POST /api/link
    permission: knowledge:link
```

---

## 6. Web UI 设计

### 6.1 页面结构

```
┌─────────────────────────────────────────────────────────────┐
│                    Knowledge Base Tool                       │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Logo    Dashboard  Documents  Wiki  Search  Graph  ... │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                                                         │ │
│  │                    Content Area                         │ │
│  │                                                         │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │ │
│  │  │  Stats      │  │  Recent     │  │  Queue      │    │ │
│  │  │  统计卡片   │  │  最近文档   │  │  摄入队列   │    │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘    │ │
│  │                                                         │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 页面列表

| 页面 | 路由 | 描述 |
|------|------|------|
| **Dashboard** | `/` | 统计概览、最近文档、摄入队列 |
| **Documents** | `/documents` | 文档列表（筛选、分页、删除） |
| **Document Detail** | `/documents/{id}` | 文档详情、关联代码、过期检测 |
| **Document Form** | `/documents/new` | 导入文档（上传、URL、文件夹） |
| **Wiki Pages** | `/wiki` | Wiki 页面列表 |
| **Wiki Detail** | `/wiki/{id}` | Wiki 页面详情、来源追溯 |
| **Search** | `/search` | 搜索界面（关键词 + 语义） |
| **Graph** | `/graph` | 知识图谱可视化 |
| **Review** | `/review` | 审核系统 |
| **Drift** | `/drift` | 过期文档列表 |
| **Ingest Queue** | `/ingest` | 摄入队列、进度可视化 |
| **Settings** | `/settings` | LLM 配置、嵌入配置 |

### 6.3 组件库

| 组件 | 描述 |
|------|------|
| **StatsCard** | 统计卡片（文档数、Wiki 页数、过期数） |
| **DocumentList** | 文档列表（表格 + 筛选） |
| **WikiPreview** | Wiki 页面预览 |
| **SearchBox** | 搜索框（关键词 + 语义切换） |
| **GraphViewer** | 知识图谱可视化（D3.js） |
| **QueueProgress** | 摄入队列进度条 |
| **DriftAlert** | 过期告警卡片 |
| **ReviewCard** | 审核卡片（批准/拒绝按钮） |

### 6.4 技术栈

- **模板引擎**: Jinja2
- **前端框架**: Alpine.js
- **样式**: Tailwind CSS CDN
- **图表**: D3.js (知识图谱)
- **Markdown 渲染**: marked.js
- **代码高亮**: highlight.js

---

## 7. 与 code-index-tool 集成

### 7.1 集成架构

```
┌─────────────────────────────────────────────────────────────┐
│                    集成架构                                  │
│                                                               │
│  knowledge-tool (18087)         code-index-tool (18086)     │
│  ┌─────────────┐                ┌─────────────┐             │
│  │  文档索引    │                │  代码索引    │             │
│  │  Wiki 生成   │                │  AST 解析   │             │
│  │  知识图谱    │                │  调用链     │             │
│  └─────────────┘                └─────────────┘             │
│         │                               │                     │
│         └───────────┬───────────────────┘                     │
│                     ▼                                         │
│            ┌─────────────────┐                               │
│            │  Code Linker    │                               │
│            │                 │                               │
│            │  文档 → 代码    │                               │
│            │  代码 → 文档    │                               │
│            │  过期检测       │                               │
│            └─────────────────┘                               │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 集成 API

**code-index-tool 调用 knowledge-tool：**

```python
# code-index-tool 中的集成代码
class CodeIndexIntegrator:
    """code-index-tool 集成 knowledge-tool"""
    
    def __init__(self, knowledge_url: str):
        self.knowledge_url = knowledge_url
    
    async def on_code_indexed(self, project_id: int):
        """代码索引完成后，触发文档过期检测"""
        # 获取项目关联的文档
        documents = await self.get_project_documents(project_id)
        
        for doc in documents:
            # 检测过期
            drifts = await self.detect_drift(doc)
            
            if drifts:
                # 通知 knowledge-tool
                await self.notify_drift(doc, drifts)
    
    async def search_code_for_document(self, document_id: int):
        """为文档搜索相关代码"""
        # 获取文档内容
        doc = await self.get_document(document_id)
        
        # 在代码索引中搜索
        results = await self.code_index.search_symbol(doc.title)
        
        return results
```

**knowledge-tool 调用 code-index-tool：**

```python
# knowledge-tool 中的集成代码
class KnowledgeIntegrator:
    """knowledge-tool 集成 code-index-tool"""
    
    def __init__(self, code_index_url: str):
        self.code_index_url = code_index_url
    
    async def on_document_ingested(self, document: Document):
        """文档摄入后，创建文档-代码链接"""
        # 从文档提取代码引用
        code_refs = await self.extract_code_references(document)
        
        for ref in code_refs:
            # 在代码索引中查找
            matches = await self.search_code(ref)
            
            for match in matches:
                # 创建链接
                await self.create_link(document.id, match.id, ref.type)
    
    async def detect_document_drift(self, document_id: int):
        """检测文档过期"""
        # 获取文档链接的代码
        links = await self.get_document_links(document_id)
        
        drifts = []
        for link in links:
            # 在代码索引中检查
            code_node = await self.code_index.get_node(link.code_node_id)
            
            if not code_node:
                drifts.append(Drift(
                    type="code_deleted",
                    description=f"代码 {link.code_name} 已删除"
                ))
            elif self.is_changed(code_node, link.expected_signature):
                drifts.append(Drift(
                    type="signature_changed",
                    description=f"代码 {link.code_name} 签名已变更"
                ))
        
        return drifts
```

### 7.3 联动流程

```
场景：AI Agent 查询"用户认证怎么实现"

1. Skill Router 识别任务类型 → "理解"
2. 调用 knowledge-tool → 搜索相关文档
   - 返回: docs/api/auth-api.md, ruoyi-auth/README.md
3. 调用 code-index-tool → 搜索相关代码
   - 返回: AuthController.java, AuthService.java
4. 调用 knowledge-tool → 获取文档-代码链接
   - 返回: auth-api.md → AuthController.login()
5. 组合结果返回给 AI Agent

场景：开发者修改了 AuthController.java

1. code-index-tool 检测到文件变更
2. 调用 knowledge-tool → 检测文档过期
3. knowledge-tool 检查所有链接到 AuthController 的文档
4. 发现 auth-api.md 中的 oldEndpoint() 已不存在
5. 在 Web UI 显示过期告警
```

---

## 8. 参考项目

### 8.1 LLM Wiki（重点参考）

| 维度 | 描述 |
|------|------|
| **GitHub** | https://github.com/nashsu/llm_wiki |
| **核心架构** | 两步思维链摄入 + 四信号知识图谱 + 向量搜索 |
| **存储方案** | Markdown 文件 + Obsidian 兼容 |
| **工具设计** | 桌面应用 + HTTP API + MCP |
| **独特能力** | 两步摄入、四信号图谱、Louvain 社区检测、深度研究 |

**LLM Wiki 关键设计决策：**

| 决策 | 理由 | 我们可借鉴 |
|------|------|-----------|
| **两步摄入** | 分析→生成，质量显著提升 | ✅ 采用 |
| **四信号图谱** | 多维关联，比单一链接更准确 | ✅ 采用 |
| **Louvain 社区检测** | 自动发现知识聚类 | ✅ 采用 |
| **持久化队列** | 崩溃恢复，进度可视化 | ✅ 采用 |
| **来源可追溯** | 每页链接回源文件 | ✅ 采用 |
| **SHA256 缓存** | 增量摄入，跳过未变更文件 | ✅ 采用 |
| **Markdown 格式** | Obsidian 兼容，版本友好 | ✅ 采用 |
| **桌面应用** | 单用户，不适合 NAS | ❌ 改为 Web |

### 8.2 codebase-memory-mcp

| 维度 | 描述 |
|------|------|
| **核心能力** | Tree-sitter 解析、知识图谱、Cypher 查询 |
| **可借鉴** | 代码感知、文档-代码链接 |
| **适用场景** | 代码结构理解、关系建模 |

### 8.3 CodeGraph

| 维度 | 描述 |
|------|------|
| **核心能力** | 预构建知识图谱、SQLite + FTS5、MCP |
| **可借鉴** | 单一强工具、FTS5 搜索 |
| **适用场景** | 代码导航、依赖分析 |

---

## 9. 实施计划

### 9.1 Phase 1：基础索引（P0）- 2 周

**目标：** 能导入文档并建立基础索引

**任务：**
1. SQLite + FTS5 存储层搭建
2. 文档导入（Markdown、代码文件）
3. SHA256 增量缓存
4. 持久化摄入队列
5. 基础搜索 API
6. Web UI（文档列表、导入、搜索）

**技术选型：**
- 存储：SQLite + FTS5
- 队列：SQLite 持久化
- API：FastAPI
- Web UI：Jinja2 + Alpine.js + Tailwind CSS

**预计工时：** 10-12 天

**验收标准：**
- [ ] 能导入 Markdown 文件
- [ ] 能导入代码文件（提取注释）
- [ ] 能搜索文档（FTS5）
- [ ] 能显示文档列表
- [ ] 能显示摄入进度
- [ ] 增量导入跳过未变更文件

### 9.2 Phase 2：Wiki 生成 + 知识图谱（P1）- 2 周

**目标：** LLM 自动生成 Wiki + 知识图谱

**任务：**
1. 两步思维链摄入引擎
2. LLM 分析→生成 Wiki 页面
3. 四信号知识图谱
4. Louvain 社区检测
5. 知识图谱可视化（D3.js）
6. Web UI（Wiki 页面、图谱、审核）

**技术选型：**
- LLM：OpenAI 兼容 API
- 图谱：NetworkX
- 可视化：D3.js
- 社区检测：python-louvain

**预计工时：** 10-12 天

**验收标准：**
- [ ] 能自动生成 Wiki 页面
- [ ] Wiki 页面带 frontmatter
- [ ] 能构建知识图谱
- [ ] 能检测社区
- [ ] 能可视化图谱
- [ ] 审核系统工作

### 9.3 Phase 3：文档-代码集成（P2）- 2 周

**目标：** 文档与代码链接 + 过期检测

**任务：**
1. 文档-代码链接器
2. 从文档提取代码引用
3. 文档过期检测
4. 与 code-index-tool 集成
5. 语义搜索（LanceDB）
6. Web UI（过期列表、链接详情）

**技术选型：**
- 链接：正则 + LLM 辅助
- 过期：签名对比
- 集成：HTTP API
- 语义搜索：LanceDB

**预计工时：** 10-12 天

**验收标准：**
- [ ] 能创建文档-代码链接
- [ ] 能检测文档过期
- [ ] 能与 code-index-tool 联动
- [ ] 语义搜索工作
- [ ] 过期告警显示

### 9.4 Phase 4：高级能力（P3）- 1 周

**目标：** 深度研究 + PDF + Chrome 剪藏

**任务：**
1. 深度研究（LLM 生成搜索主题）
2. PDF 导入
3. Chrome 剪藏 API
4. 多模态图片摄入
5. 性能优化

**预计工时：** 5-7 天

**验收标准：**
- [ ] 深度研究工作
- [ ] PDF 导入工作
- [ ] Chrome 剪藏工作
- [ ] 图片摄入工作

### 9.5 路线图

```
Phase 1 (Week 1-2)           Phase 2 (Week 3-4)           Phase 3 (Week 5-6)           Phase 4 (Week 7)
    │                             │                             │                             │
    ├─ SQLite + FTS5              ├─ 两步摄入                   ├─ 文档-代码链接              ├─ 深度研究
    ├─ 文档导入                   ├─ Wiki 生成                  ├─ 过期检测                   ├─ PDF 导入
    ├─ 增量缓存                   ├─ 四信号图谱                 ├─ code-index 集成            ├─ Chrome 剪藏
    ├─ 持久化队列                 ├─ Louvain 社区               ├─ 语义搜索                   ├─ 图片摄入
    ├─ 基础搜索                   ├─ 图谱可视化                 │                             │
    ├─ Web UI                     ├─ 审核系统                   │                             │
    │                             │                             │                             │
    └─ 交付                      └─ 交付                       └─ 交付                       └─ 交付
```

---

## 附录

### A. 配置项

```python
# app/config.py

class KnowledgeBaseConfig:
    # 存储配置
    DB_PATH: str = ".knowledge/knowledge.db"
    VECTORS_PATH: str = ".knowledge/vectors.lance"
    WIKI_PATH: str = ".knowledge/wiki"
    SOURCES_PATH: str = ".knowledge/sources"
    
    # LLM 配置
    LLM_BASE_URL: str = "http://192.168.0.100:11434/v1"
    LLM_API_KEY: str = "sk-xxx"
    LLM_MODEL: str = "qwen2.5:14b"
    
    # 嵌入配置
    EMBEDDING_ENABLED: bool = True
    EMBEDDING_MODEL: str = "nomic-embed-code"
    
    # 摄入配置
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    SUPPORTED_EXTENSIONS: list = [".md", ".txt", ".py", ".java", ".ts", ".js"]
    EXCLUDE_PATTERNS: list = ["**/node_modules/**", "**/.git/**", "**/target/**"]
    
    # 队列配置
    MAX_RETRIES: int = 3
    RETRY_DELAY: list = [1, 5, 15]  # 指数退避
    
    # 图谱配置
    MAX_GRAPH_DEPTH: int = 5
    COMMUNITY_DETECTION: bool = True
    
    # 搜索配置
    SEARCH_RESULTS_LIMIT: int = 50
    FTS5_ENABLED: bool = True
```

### B. Docker 部署

```dockerfile
# Dockerfile
FROM docker.1ms.run/library/python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 18087

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "18087"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  knowledge-tool:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: knowledge-tool
    network_mode: host
    restart: unless-stopped
    volumes:
      - ./data:/app/data
```

---

## 附录 C. 上下文优化方案

### C.1 问题分析

```
当前数据流:

AI Agent ──► Skill Router ──► 多个工具 ──► 原始结果 ──► AI Agent
                                         │
                                         ▼
                              ┌─────────────────────┐
                              │  上下文爆炸          │
                              │                     │
                              │  Knowledge: 5000tok │
                              │  Code Index: 8000tok│
                              │  Memory: 3000tok    │
                              │  Asset: 4000tok     │
                              │  ─────────────────  │
                              │  总计: 20000tok     │
                              │  Agent 限制: 8192tok│
                              │  ─────────────────  │
                              │  溢出 → 幻觉        │
                              └─────────────────────┘
```

### C.2 优化架构

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         Context Optimizer                                       │
│                         上下文优化器                                             │
│                                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                    Phase 1: 需求分析                                        │ │
│  │                    (小模型 + 规则)                                          │ │
│  │                                                                             │ │
│  │  输入: AI Agent 的任务描述                                                  │ │
│  │                                                                             │ │
│  │  分析内容:                                                                  │ │
│  │  - 任务意图: 理解/编写/调试/优化/重构                                       │ │
│  │  - 关键实体: 类名/函数名/概念                                               │ │
│  │  - 需要工具: [knowledge, code-index, asset, memory]                        │ │
│  │  - 需要知识: [JWT认证, Spring Security, Filter链]                          │ │
│  │  - 上下文状态: Agent 已有信息列表                                           │ │
│  │                                                                             │ │
│  │  输出: RetrievalPlan                                                        │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                         │                                         │
│                                         ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                    Phase 2: 按需获取                                        │ │
│  │                    (工具层优化)                                              │ │
│  │                                                                             │ │
│  │  每个工具根据预算和查询获取:                                                 │ │
│  │  - 语义预过滤: 向量相似度 > 0.7 才返回                                     │ │
│  │  - 分层返回: 先摘要，详情按需                                               │ │
│  │  - 缓存: 相同查询直接返回                                                  │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                         │                                         │
│                                         ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                    Phase 3: 精简输出                                        │ │
│  │                    (小模型 + 规则)                                          │ │
│  │                                                                             │ │
│  │  精简策略:                                                                  │ │
│  │  - LLM 摘要: 提取关键信息，删除冗余                                        │ │
│  │  - 去重: 合并重复内容                                                       │ │
│  │  - 格式压缩: 精简代码块、列表                                              │ │
│  │  - 相关性过滤: 只保留与任务直接相关的内容                                   │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### C.3 实现代码

#### 需求分析器

```python
class RequirementAnalyzer:
    """需求分析器 - 小模型 + 规则混合"""
    
    async def analyze(self, task: str, context: AgentContext) -> RetrievalPlan:
        """分析任务需求"""
        
        # 1. 规则预分析（快速，无 LLM 调用）
        rule_result = self.rule_analysis(task)
        
        # 2. 小模型深度分析（准确，有 LLM 调用）
        llm_result = await self.llm_analysis(task, context)
        
        # 3. 合并结果
        plan = self.merge_results(rule_result, llm_result)
        
        return plan
    
    def rule_analysis(self, task: str) -> RuleResult:
        """规则预分析"""
        
        # 意图识别（关键词匹配）
        intent = self.detect_intent(task)
        # 理解: "怎么实现", "是什么", "为什么"
        # 编写: "增加", "实现", "创建"
        # 调试: "报错", "异常", "失败"
        # 优化: "性能", "优化", "重构"
        
        # 实体提取（正则匹配）
        entities = self.extract_entities(task)
        # 类名: AuthController, SecurityConfig
        # 函数名: login(), authenticate()
        # 概念: JWT, Spring Security
        
        # 工具推荐（基于意图）
        tools = self.recommend_tools(intent, entities)
        
        return RuleResult(
            intent=intent,
            entities=entities,
            tools=tools
        )
    
    async def llm_analysis(self, task: str, context: AgentContext) -> LLMResult:
        """小模型深度分析"""
        
        prompt = f"""
        分析以下编程任务，返回检索计划：
        
        任务: {task}
        
        Agent 已有信息:
        {context.existing_content}
        
        请返回 JSON:
        {{
            "intent": "理解/编写/调试/优化",
            "key_entities": ["类名", "函数名", "概念"],
            "required_tools": ["tool1", "tool2"],
            "search_queries": {{
                "tool1": ["查询1", "查询2"],
                "tool2": ["查询3"]
            }},
            "skip_topics": ["Agent已了解的内容"],
            "priority": "high/medium/low"
        }}
        """
        
        result = await self.small_model.call(prompt)
        return LLMResult.parse(result)
```

#### 工具层优化器

```python
class OptimizedTool:
    """优化后的工具"""
    
    async def invoke(self, params: dict, context: ToolContext) -> ToolResult:
        """带优化的调用"""
        
        # 1. 检查缓存
        cache_key = self.cache_key(params)
        cached = await self.cache.get(cache_key)
        if cached:
            return cached
        
        # 2. 语义预过滤
        pre_filtered = await self.semantic_pre_filter(params)
        
        # 3. 执行查询（带预算）
        raw_results = await self.raw_query(
            pre_filtered,
            budget=context.budget
        )
        
        # 4. 分层返回（先摘要）
        summarized = self.summarize_results(raw_results)
        
        # 5. 相关性过滤
        relevant = self.filter_relevance(summarized, threshold=0.7)
        
        # 6. 去重
        deduped = self.deduplicate(relevant, context.existing)
        
        # 7. 格式优化
        optimized = self.format_optimize(deduped, context.budget)
        
        # 8. 缓存结果
        await self.cache.set(cache_key, optimized)
        
        return optimized
    
    async def semantic_pre_filter(self, params: dict) -> dict:
        """语义预过滤"""
        
        # 用向量相似度快速过滤
        query_embedding = await self.embed(params["query"])
        
        # 只保留相似度 > 0.7 的文档
        candidates = await self.vector_db.search(
            query_embedding,
            threshold=0.7,
            limit=10  # 最多 10 个候选
        )
        
        # 返回过滤后的参数
        params["candidate_ids"] = [c.id for c in candidates]
        return params
    
    def summarize_results(self, results: List[Result]) -> List[SummarizedResult]:
        """分层返回 - 先摘要"""
        
        summarized = []
        for result in results:
            # 只返回关键信息
            summary = {
                "id": result.id,
                "title": result.title,
                "relevance": result.score,
                "summary": result.content[:200],  # 前 200 字符
                "key_points": self.extract_key_points(result)
            }
            summarized.append(summary)
        
        return summarized
```

#### 结果精简器

```python
class ResultRefiner:
    """结果精简器"""
    
    async def refine(self, raw_results: Dict[str, List], budget: int) -> Dict[str, List]:
        """精简结果"""
        
        refined = {}
        remaining_budget = budget
        
        for tool_name, results in raw_results.items():
            # 1. LLM 摘要
            summarized = await self.llm_summarize(results, remaining_budget // 3)
            
            # 2. 去重
            deduped = self.deduplicate(summarized)
            
            # 3. 相关性过滤
            relevant = self.filter_relevant(deduped)
            
            # 4. 格式压缩
            compressed = self.compress_format(relevant)
            
            # 5. 计算 token
            tokens = self.count_tokens(compressed)
            
            # 6. 更新预算
            remaining_budget -= tokens
            
            refined[tool_name] = compressed
        
        return refined
    
    async def llm_summarize(self, results: List[Result], budget: int) -> List[str]:
        """LLM 摘要"""
        
        prompt = f"""
        从以下结果中提取关键信息，总 token 数不超过 {budget}：
        
        结果:
        {self.format_results(results)}
        
        要求:
        1. 只保留与任务直接相关的信息
        2. 删除冗余和重复内容
        3. 用简洁的语言表达
        4. 保留关键代码片段（如有）
        """
        
        summary = await self.small_model.call(prompt)
        return self.parse_summary(summary)
    
    def compress_format(self, results: List) -> List:
        """格式压缩"""
        
        compressed = []
        for result in results:
            # 压缩代码块
            if "code" in result:
                result["code"] = self.compress_code(result["code"])
            
            # 压缩列表
            if "items" in result:
                result["items"] = result["items"][:5]  # 最多 5 项
            
            # 压缩描述
            if "description" in result:
                result["description"] = result["description"][:100]  # 最多 100 字符
            
            compressed.append(result)
        
        return compressed
```

### C.4 优化策略总结

| 策略 | 描述 | 实现层 | 效果 |
|------|------|--------|------|
| **意图识别** | 识别任务类型，减少无关工具调用 | 需求分析 | 减少 50% 工具调用 |
| **实体提取** | 精准搜索，避免泛化 | 需求分析 | 提高搜索精度 |
| **语义预过滤** | 向量相似度过滤 | 工具层 | 减少 70% 候选 |
| **分层返回** | 先摘要，详情按需 | 工具层 | 减少 60% token |
| **LLM 摘要** | 提取关键信息 | 精简层 | 减少 50% token |
| **去重合并** | 合并重复内容 | 精简层 | 减少 30% token |
| **格式压缩** | 精简输出格式 | 精简层 | 减少 20% token |
| **缓存复用** | 相同查询直接返回 | 工具层 | 减少 80% 延迟 |
| **上下文感知** | 避免重复获取 | 全局 | 减少 40% token |
