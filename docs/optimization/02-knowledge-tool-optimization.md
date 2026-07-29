# Knowledge-Tool 工具优化设计文档

## 1. 现状分析

### 1.1 当前架构
```
knowledge-tool/
├── app/services/
│   ├── document_service.py    # 文档CRUD
│   ├── search_service.py      # 两级搜索（摘要+chunk）
│   ├── indexing_service.py     # 解析→分块→embedding→存储
│   ├── knowledge_graph.py     # 知识图谱（基础）
│   ├── two_step_ingest.py     # LLM两步导入
│   └── vector_db.py           # 独立向量DB（未集成）
├── app/parser/                # Markdown/纯文本解析器
├── app/chunk/                 # 分块器
├── app/embedding/             # Embedding（仅mock）
└── app/db/models.py           # 5个表
```

### 1.2 现有能力
| 能力 | 实现方式 | 问题 |
|------|----------|------|
| 文档存储 | SQLite + 本地文件系统 | 无版本控制 |
| 文本搜索 | 子串匹配 + Jaccard词重叠 | 无语义理解 |
| Embedding | Mock（确定性哈希） | 无真实向量 |
| 向量搜索 | VectorDB类（未集成） | 不在主流程中 |
| 知识导入 | 两步LLM（分析+生成） | 未持久化到DB |

### 1.3 核心问题
1. **无真实Embedding**：Mock provider生成的向量无语义意义
2. **向量搜索未集成**：VectorDB是独立模块，不参与搜索流程
3. **搜索纯文本**：仅子串匹配+词重叠，无语义理解
4. **无知识导入**：README/docs未自动提取为知识
5. **无规则提取**：编码规范/PR评论中的规则未被捕获

---

## 2. 优化目标

| 目标 | 指标 | 当前值 | 目标值 |
|------|------|--------|--------|
| 搜索精准度 | Top-5命中率 | ~20% | >75% |
| 语义搜索 | 支持自然语言查询 | 不支持 | 支持 |
| 知识覆盖 | 项目文档导入率 | 0% | >80% |
| 规则提取 | 编码规则识别 | 0条 | >20条/项目 |
| 检索延迟 | P95延迟 | ~500ms | <200ms |

---

## 3. 优化设计

### 3.1 模块一：真实Embedding引擎

#### 3.1.1 Embedding Provider实现

**新增文件：`app/embedding/openai_provider.py`**
```python
class OpenAIEmbeddingProvider:
    """OpenAI兼容的Embedding提供者"""
    
    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
    
    async def generate(self, texts: List[str]) -> List[EmbeddingVector]:
        response = await self.client.embeddings.create(
            model=self.model,
            input=texts
        )
        return [
            EmbeddingVector(
                vector=item.embedding,
                dimension=len(item.embedding),
                model=self.model
            )
            for item in response.data
        ]
```

**新增文件：`app/embedding/local_provider.py`**
```python
class LocalEmbeddingProvider:
    """本地sentence-transformers模型"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)
    
    async def generate(self, texts: List[str]) -> List[EmbeddingVector]:
        embeddings = self.model.encode(texts, show_progress_bar=False)
        return [
            EmbeddingVector(
                vector=emb.tolist(),
                dimension=len(emb),
                model=self.model_name
            )
            for emb in embeddings
        ]
```

#### 3.1.2 向量存储集成

**修改：`app/services/indexing_service.py`**
```python
async def run_index_job(db, job_id):
    # 1. 读取文档内容
    content = await get_document_content(db, job_id.document_id)
    
    # 2. 解析为sections
    sections = parser.parse(content)
    
    # 3. 分块
    chunks = chunker.chunk(sections)
    
    # 4. 生成embeddings
    texts = [chunk.content for chunk in chunks]
    embeddings = await embedding_provider.generate(texts)
    
    # 5. 存储到DB（包括向量）
    for chunk, embedding in zip(chunks, embeddings):
        await db.execute(
            insert(KtDocumentChunk).values(
                content=chunk.content,
                embedding=json.dumps(embedding.vector),  # 存储为JSON
                embedding_model=embedding.model,
                embedding_dimension=embedding.dimension
            )
        )
```

### 3.2 模块二：三级检索引擎

#### 3.2.1 检索架构

```
用户查询
    │
    ▼
┌─────────────────────────────────────┐
│ Level 1: 精确匹配                    │
│ - 函数名/类名/配置项完全匹配          │
│ - 权重: 1.0 (完全匹配)               │
└─────────────────────────────────────┘
    │ 未命中
    ▼
┌─────────────────────────────────────┐
│ Level 2: 语义搜索                    │
│ - 向量相似度 (cosine)               │
│ - 权重: 0.7 * similarity            │
└─────────────────────────────────────┘
    │ 未命中
    ▼
┌─────────────────────────────────────┐
│ Level 3: 全文搜索                    │
│ - BM25/TF-IDF                       │
│ - 权重: 0.3 * tfidf_score           │
└─────────────────────────────────────┘
```

#### 3.2.2 HyDE检索（Hypothetical Document Embeddings）

**设计思路**：先用LLM生成假设答案，再用假设答案的向量搜索真实文档

```python
async def hyde_search(query: str, project_id: int) -> List[SearchResult]:
    # 1. 生成假设答案
    hypothetical_answer = await llm_client.generate(
        f"""Based on the question: {query}
        
        Provide a detailed answer that would be found in technical documentation.
        Include specific function names, configuration options, and code examples."""
    )
    
    # 2. 对假设答案生成embedding
    hyde_embedding = await embedding_provider.generate([hypothetical_answer])
    
    # 3. 用假设答案的向量搜索真实文档
    results = await vector_search(
        query_embedding=hyde_embedding[0].vector,
        project_id=project_id,
        top_k=10
    )
    
    # 4. 重排序（原始查询 vs 候选文档的相关性）
    reranked = await rerank(query, results)
    
    return reranked
```

#### 3.2.3 搜索结果重排序

```python
async def rerank(query: str, candidates: List[SearchResult]) -> List[SearchResult]:
    """用交叉编码器重排序"""
    
    # 构造(query, document)对
    pairs = [(query, c.content) for c in candidates]
    
    # 用交叉编码器打分
    scores = cross_encoder.predict(pairs)
    
    # 更新分数
    for candidate, score in zip(candidates, scores):
        candidate.rerank_score = float(score)
    
    # 按重排序分数排序
    return sorted(candidates, key=lambda x: x.rerank_score, reverse=True)
```

### 3.3 模块三：知识自动导入

#### 3.3.1 项目文档扫描器

**新增文件：`app/services/project_scanner.py`**
```python
class ProjectKnowledgeScanner:
    """扫描项目目录，自动提取知识文档"""
    
    # 支持的文档路径模式
    DOC_PATTERNS = [
        "README*", "CONTRIBUTING*", "CHANGELOG*",
        "docs/**/*.md", "doc/**/*.md",
        "wiki/**/*.md",
        ".github/**/*.md",
        "api/**/*.md",
        "examples/**/*.md",
    ]
    
    # 支持的配置文件（提取规则）
    CONFIG_PATTERNS = [
        ".eslintrc*", ".prettierrc*", ".pylintrc*",
        "tsconfig.json", "pyproject.toml",
        "package.json", "requirements.txt",
    ]
    
    async def scan_project(self, project_path: str) -> List[KnowledgeDocument]:
        documents = []
        
        # 1. 扫描文档文件
        for pattern in self.DOC_PATTERNS:
            files = glob.glob(os.path.join(project_path, pattern), recursive=True)
            for file in files:
                doc = await self._extract_document(file)
                documents.append(doc)
        
        # 2. 扫描配置文件（提取规则）
        for pattern in self.CONFIG_PATTERNS:
            files = glob.glob(os.path.join(project_path, pattern), recursive=True)
            for file in files:
                rules = await self._extract_rules(file)
                documents.extend(rules)
        
        # 3. 扫描代码注释（提取知识）
        code_docs = await self._extract_code_comments(project_path)
        documents.extend(code_docs)
        
        return documents
    
    async def _extract_document(self, file_path: str) -> KnowledgeDocument:
        """提取文档内容"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return KnowledgeDocument(
            title=os.path.basename(file_path),
            content=content,
            doc_type=self._detect_type(file_path),
            source_uri=file_path,
            tags=self._extract_tags(content)
        )
    
    async def _extract_rules(self, file_path: str) -> List[KnowledgeDocument]:
        """从配置文件提取编码规则"""
        rules = []
        
        if file_path.endswith('.eslintrc*'):
            config = json.load(open(file_path))
            for rule, level in config.get('rules', {}).items():
                if level in ['error', 'warn']:
                    rules.append(KnowledgeDocument(
                        title=f"ESLint Rule: {rule}",
                        content=f"Rule: {rule}\nLevel: {level}\nDescription: {RULE_DESCRIPTIONS.get(rule, '')}",
                        doc_type="coding_rule",
                        tags=["eslint", "javascript", "coding-standard"]
                    ))
        
        return rules
```

#### 3.3.2 自动导入流程

```python
async def auto_import_project(project_id: int, project_path: str):
    """自动导入项目知识"""
    
    scanner = ProjectKnowledgeScanner()
    
    # 1. 扫描项目
    documents = await scanner.scan_project(project_path)
    
    # 2. 创建或获取知识库
    kb = await get_or_create_kb(
        name=f"Project {project_id} Knowledge",
        kb_level="project",
        domains=["code", "documentation"]
    )
    
    # 3. 批量导入文档
    for doc in documents:
        # 创建文档记录
        created_doc = await create_document(
            kb_id=kb.id,
            title=doc.title,
            content=doc.content,
            doc_type=doc.doc_type,
            tags=doc.tags
        )
        
        # 触发索引
        await trigger_index_job(created_doc.id)
    
    return {
        "kb_id": kb.id,
        "documents_imported": len(documents),
        "document_types": Counter(d.doc_type for d in documents)
    }
```

### 3.4 模块四：编码规则提取器

#### 3.4.1 规则来源

| 来源 | 提取方式 | 示例 |
|------|----------|------|
| ESLint配置 | 解析JSON | `no-console: error` |
| PR评论 | LLM提取 | "请使用logger替代print" |
| 代码注释 | 正则匹配 | `# FIXME: 不要硬编码密码` |
| 提交信息 | LLM分析 | `refactor: 统一错误处理` |
| README | LLM提取 | "本项目使用Google Style" |

#### 3.4.2 规则提取器

**新增文件：`app/services/rule_extractor.py`**
```python
class CodingRuleExtractor:
    """从代码库提取编码规则"""
    
    async def extract_from_comments(self, project_path: str) -> List[CodingRule]:
        """从代码注释提取规则"""
        rules = []
        
        # 扫描TODO/FIXME/HACK注释
        patterns = [
            (r'# TODO:?\s*(.+)', 'todo'),
            (r'# FIXME:?\s*(.+)', 'fixme'),
            (r'# HACK:?\s*(.+)', 'hack'),
            (r'// TODO:?\s*(.+)', 'todo'),
            (r'// FIXME:?\s*(.+)', 'fixme'),
        ]
        
        for root, dirs, files in os.walk(project_path):
            for file in files:
                if file.endswith(('.py', '.js', '.ts', '.java')):
                    content = open(os.path.join(root, file)).read()
                    for pattern, rule_type in patterns:
                        matches = re.findall(pattern, content)
                        for match in matches:
                            rules.append(CodingRule(
                                rule=match,
                                source="code_comment",
                                source_file=file,
                                rule_type=rule_type
                            ))
        
        return rules
    
    async def extract_from_pr_comments(self, github_token: str, repo: str) -> List[CodingRule]:
        """从PR评论提取规则"""
        rules = []
        
        # 获取最近的PR评论
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/repos/{repo}/pulls/comments",
                headers={"Authorization": f"token {github_token}"}
            )
            
            for comment in response.json():
                # 用LLM判断是否包含规则
                if await self._is_rule_comment(comment['body']):
                    rule = await self._extract_rule_from_comment(comment['body'])
                    rules.append(rule)
        
        return rules
    
    async def _is_rule_comment(self, comment: str) -> bool:
        """用LLM判断评论是否包含编码规则"""
        prompt = f"""判断以下代码评审评论是否包含编码规则或最佳实践：
        
        评论：{comment}
        
        请回答"是"或"否"，并说明原因。"""
        
        response = await llm_client.generate(prompt)
        return "是" in response
```

---

## 4. API设计

### 4.1 新增/修改的API

#### 语义搜索
```python
@router.post("/api/knowledge/search/semantic")
async def semantic_search(request: SemanticSearchRequest):
    """
    语义搜索知识文档
    
    Request:
    {
        "project_id": "my-project",
        "query": "如何配置数据库连接",
        "top_k": 5,
        "search_mode": "hyde"  # "vector" | "hyde" | "hybrid"
    }
    
    Response:
    {
        "items": [
            {
                "id": "doc-123",
                "title": "数据库配置指南",
                "content": "数据库连接配置...",
                "score": 0.89,
                "score_breakdown": {
                    "vector": 0.85,
                    "text": 0.15
                },
                "chunk_content": "在settings.py中配置 DATABASE_URL = '...'",
                "source": "docs/database.md"
            }
        ],
        "total": 1,
        "search_mode": "hyde",
        "latency_ms": 150
    }
    """
```

#### 项目知识自动导入
```python
@router.post("/api/knowledge/auto-import")
async def auto_import_knowledge(request: AutoImportRequest):
    """
    自动导入项目知识
    
    Request:
    {
        "project_id": "my-project",
        "project_path": "/path/to/project",
        "import_options": {
            "include_docs": true,
            "include_config": true,
            "include_comments": true,
            "include_pr_rules": false
        }
    }
    
    Response:
    {
        "kb_id": "kb-456",
        "documents_imported": 25,
        "document_breakdown": {
            "readme": 3,
            "documentation": 12,
            "coding_rule": 8,
            "config": 2
        },
        "rules_extracted": 8
    }
    """
```

#### 规则查询
```python
@router.get("/api/knowledge/rules")
async def get_coding_rules(
    project_id: str,
    category: Optional[str] = None,
    limit: int = 50
):
    """
    获取项目编码规则
    
    Response:
    {
        "rules": [
            {
                "id": "rule-1",
                "rule": "不要使用print，请使用logging模块",
                "source": "pr_comment",
                "source_file": "api/auth.py",
                "category": "logging",
                "importance": "high"
            }
        ],
        "total": 8,
        "categories": ["logging", "error-handling", "naming"]
    }
    """
```

---

## 5. 任务拆分

### Phase 1：Embedding引擎（2天）
| 任务 | 描述 | 优先级 |
|------|------|--------|
| T1.1 | 实现OpenAI Embedding Provider | P0 |
| T1.2 | 实现Local Embedding Provider | P1 |
| T1.3 | 修改indexing_service集成向量存储 | P0 |
| T1.4 | 添加embedding配置选项 | P1 |

### Phase 2：三级检索（2天）
| 任务 | 描述 | 优先级 |
|------|------|--------|
| T2.1 | 实现Level 1精确匹配 | P0 |
| T2.2 | 实现Level 2向量搜索 | P0 |
| T2.3 | 实现Level 3全文搜索 | P1 |
| T2.4 | 实现融合评分 | P1 |

### Phase 3：HyDE检索（1天）
| 任务 | 描述 | 优先级 |
|------|------|--------|
| T3.1 | 实现假设答案生成 | P1 |
| T3.2 | 实现HyDE搜索流程 | P1 |
| T3.3 | 添加搜索模式选择 | P2 |

### Phase 4：知识自动导入（2天）
| 任务 | 描述 | 优先级 |
|------|------|--------|
| T4.1 | 实现项目文档扫描器 | P0 |
| T4.2 | 实现配置文件规则提取 | P1 |
| T4.3 | 实现`POST /api/knowledge/auto-import` | P1 |

### Phase 5：规则提取（1天）
| 任务 | 描述 | 优先级 |
|------|------|--------|
| T5.1 | 实现代码注释规则提取 | P1 |
| T5.2 | 实现PR评论规则提取 | P2 |
| T5.3 | 实现`GET /api/knowledge/rules` | P2 |

---

## 6. 依赖和风险

### 6.1 技术依赖
| 依赖 | 用途 | 备选方案 |
|------|------|----------|
| openai | Embedding API | sentence-transformers |
| sentence-transformers | 本地embedding | OpenAI API |
| cross-encoder | 结果重排序 | 简单BM25 |
| bm25s | 全文搜索 | TF-IDF |

### 6.2 风险点
| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Embedding API调用成本 | 高频调用费用高 | 缓存+本地模型 |
| 本地模型内存占用 | 服务启动慢 | 模型懒加载 |
| HyDE生成质量差 | 搜索结果不准 | 多轮prompt优化 |

---

## 7. 验收标准

| 验收项 | 标准 |
|--------|------|
| 语义搜索 | 输入"数据库配置"能返回配置文档 |
| HyDE检索 | 输入"怎么登录"能返回认证文档 |
| 自动导入 | 扫描项目后能导入README和配置规则 |
| 规则提取 | 能从ESLint配置提取>5条规则 |
| 搜索延迟 | P95延迟<200ms |
