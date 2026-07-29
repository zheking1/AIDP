# Code-Index 工具优化设计文档

## 1. 现状分析

### 1.1 当前架构
```
code-index/
├── app/services/
│   ├── scanner.py           # 文件系统扫描
│   ├── indexer.py           # 全量索引（正则提取）
│   ├── incremental_indexer.py # 增量索引
│   ├── search_service.py    # 符号搜索（ILIKE）
│   ├── code_explore.py      # 代码探索（9种action）
│   ├── call_tracer.py       # 调用链追踪
│   ├── lsp_client.py        # 伪LSP（DB查询）
│   └── tree_sitter_parser.py # AST解析（正则fallback）
└── app/db/models.py         # Project, Node, Edge
```

### 1.2 现有能力
| 能力 | 实现方式 | 问题 |
|------|----------|------|
| 符号搜索 | `ILIKE` 匹配 `Node.name` | 无语义理解，仅字符串匹配 |
| 代码探索 | 9种action通过DB查询 | 依赖正则提取的符号，精度低 |
| 调用链追踪 | 递归遍历CALLS边 | 正则提取的调用关系不准确 |
| 增量索引 | 删除旧节点+重新插入 | 无文件指纹，全量重建开销大 |

### 1.3 核心问题
1. **正则解析不可靠**：无法处理复杂语法（嵌套类、装饰器、async函数等）
2. **无向量搜索**：只能按名称匹配，无法理解"登录验证函数"语义
3. **边类型不一致**：写入用`CALLS`（大写），查询用`calls`（小写），导致查询失败
4. **无增量更新**：每次索引删除重建，大项目性能差
5. **无类型信息**：无法按返回类型、参数类型过滤

---

## 2. 优化目标

| 目标 | 指标 | 当前值 | 目标值 |
|------|------|--------|--------|
| 搜索精准度 | Top-5命中率 | ~30% | >80% |
| 语义理解 | 支持自然语言查询 | 不支持 | 支持 |
| 索引速度 | 万行项目索引时间 | ~30s | <5s |
| 增量更新 | 单文件更新时间 | ~1s | <200ms |
| 类型过滤 | 按类型/返回值搜索 | 不支持 | 支持 |

---

## 3. 优化设计

### 3.1 模块一：AST向量化引擎

#### 3.1.1 设计思路
将代码符号（函数、类、方法）转换为语义向量，支持向量相似度搜索。

#### 3.1.2 数据模型扩展

**新增表：`node_embeddings`**
```sql
CREATE TABLE node_embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    embedding TEXT NOT NULL,          -- JSON格式的float数组
    embedding_model VARCHAR(64) NOT NULL,
    content_hash VARCHAR(64) NOT NULL, -- 内容指纹，避免重复计算
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(node_id, embedding_model)
);
```

**新增字段：`nodes`表扩展**
```sql
ALTER TABLE nodes ADD COLUMN signature TEXT;      -- 函数签名
ALTER TABLE nodes ADD COLUMN docstring TEXT;       -- 文档字符串
ALTER TABLE nodes ADD COLUMN return_type VARCHAR(256); -- 返回类型
ALTER TABLE nodes ADD COLUMN params_json TEXT;     -- 参数列表JSON
ALTER TABLE nodes ADD COLUMN file_hash VARCHAR(64); -- 文件指纹
```

#### 3.1.3 Embedding生成策略

**向量化输入构造**：
```
function_name: verify_password
signature: def verify_password(password: str, salt: str) -> bool
docstring: Verify password against salt using bcrypt
context: This function is used in auth.py for login validation
```

**向量化公式**：
```python
embedding_input = f"""
name: {node.name}
type: {node.node_type}
signature: {node.signature}
docstring: {node.docstring or ''}
file: {node.file_path}
"""
```

#### 3.1.4 搜索算法

**多维度评分**：
```python
def search_with_score(query: str, project_id: int) -> List[SearchResult]:
    # 1. 向量搜索（语义相似度）
    vector_results = vector_search(query, project_id, top_k=20)
    
    # 2. 精确匹配（名称完全匹配）
    exact_results = name_match(query, project_id)
    
    # 3. 模糊匹配（ILIKE）
    fuzzy_results = ilike_search(query, project_id)
    
    # 4. 融合评分
    final_results = fuse_results(
        vector_results, exact_results, fuzzy_results,
        weights={'vector': 0.5, 'exact': 0.3, 'fuzzy': 0.2}
    )
    
    return final_results[:10]
```

### 3.2 模块二：增量索引系统

#### 3.2.1 文件指纹机制

**新增表：`file_fingerprints`**
```sql
CREATE TABLE file_fingerprints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    file_path VARCHAR(1024) NOT NULL,
    file_hash VARCHAR(64) NOT NULL,    -- SHA256
    last_indexed_at TIMESTAMP NOT NULL,
    node_count INTEGER DEFAULT 0,
    UNIQUE(project_id, file_path)
);
```

**增量更新流程**：
```
1. 扫描文件 → 计算SHA256
2. 对比file_fingerprints表
3. 仅处理hash变化的文件
4. 删除旧节点 → 插入新节点 → 更新指纹
```

#### 3.2.2 批量索引优化

```python
async def batch_index(project_id: int, files: List[FileInfo]):
    # 1. 批量计算指纹
    fingerprints = await compute_fingerprints(files)
    
    # 2. 识别变更文件
    changed = await detect_changes(project_id, fingerprints)
    
    # 3. 并发索引
    async with asyncio.Pool(4) as pool:
        tasks = [pool.submit(index_file, project_id, f) for f in changed]
        await asyncio.gather(*tasks)
    
    # 4. 批量写入DB
    await batch_insert_nodes(all_nodes)
    await batch_insert_edges(all_edges)
```

### 3.3 模块三：边类型统一

#### 3.3.1 问题修复

**当前问题**：
- 写入：`CONTAINS`, `CALLS`, `IMPORTS`（大写）
- 查询：`calls`, `extends`, `implements`（小写）

**解决方案**：
```python
# 统一为小写
EDGE_TYPE_MAPPING = {
    'CONTAINS': 'contains',
    'CALLS': 'calls',
    'IMPORTS': 'imports',
    'extends': 'extends',
    'implements': 'implements',
    'references': 'references',
}
```

**数据迁移**：
```sql
UPDATE edges SET edge_type = LOWER(edge_type);
```

### 3.4 模块四：类型信息提取

#### 3.4.1 Tree-sitter解析增强

**Python类型提取**：
```python
# 输入
def verify_password(password: str, salt: str) -> bool:
    """Verify password against salt."""
    pass

# 提取结果
{
    "name": "verify_password",
    "params": [
        {"name": "password", "type": "str"},
        {"name": "salt", "type": "str"}
    ],
    "return_type": "bool",
    "docstring": "Verify password against salt."
}
```

**Java类型提取**：
```java
// 输入
public User findByUsername(String username) throws UserNotFoundException {
    // ...
}

// 提取结果
{
    "name": "findByUsername",
    "params": [{"name": "username", "type": "String"}],
    "return_type": "User",
    "exceptions": ["UserNotFoundException"],
    "access_modifier": "public"
}
```

#### 3.4.2 类型搜索接口

```python
@router.get("/api/search/typed")
async def search_by_type(
    project_id: int,
    node_type: Optional[str] = None,      # function, class, method
    return_type: Optional[str] = None,     # bool, User, List[str]
    param_type: Optional[str] = None,      # str, int, Request
    access_modifier: Optional[str] = None, # public, private, protected
    limit: int = 20
):
    """
    按类型过滤搜索
    示例：找所有返回bool的函数
    GET /api/search/typed?project_id=1&node_type=function&return_type=bool
    """
```

---

## 4. API设计

### 4.1 新增/修改的API

#### 语义搜索
```python
@router.post("/api/search/semantic")
async def semantic_search(request: SemanticSearchRequest):
    """
    语义搜索代码符号
    
    Request:
    {
        "project_id": 1,
        "query": "登录验证函数",
        "top_k": 10,
        "filters": {
            "node_type": "function",
            "return_type": "bool"
        }
    }
    
    Response:
    {
        "results": [
            {
                "id": 123,
                "name": "verify_password",
                "node_type": "function",
                "file_path": "auth.py",
                "line_start": 45,
                "score": 0.92,
                "score_breakdown": {
                    "vector": 0.85,
                    "exact": 0.10,
                    "fuzzy": 0.05
                },
                "signature": "def verify_password(password: str, salt: str) -> bool",
                "docstring": "Verify password against salt using bcrypt"
            }
        ],
        "total": 1
    }
    """
```

#### 增量索引
```python
@router.post("/api/index/incremental")
async def incremental_index(request: IncrementalIndexRequest):
    """
    增量索引指定文件或目录
    
    Request:
    {
        "project_id": 1,
        "paths": ["src/auth.py", "src/models/"],
        "force": false  # 强制重新索引
    }
    
    Response:
    {
        "files_scanned": 5,
        "files_changed": 2,
        "nodes_updated": 15,
        "edges_updated": 23,
        "duration_ms": 450
    }
    """
```

#### 影响分析增强
```python
@router.post("/api/analyze/impact")
async def analyze_impact(request: ImpactAnalysisRequest):
    """
    分析修改某函数的影响范围
    
    Request:
    {
        "project_id": 1,
        "node_id": 123,
        "depth": 3
    }
    
    Response:
    {
        "node": {"name": "verify_password", "file": "auth.py"},
        "callers": [
            {"name": "login", "file": "api/auth.py", "line": 23},
            {"name": "register", "file": "api/auth.py", "line": 45}
        ],
        "callees": [
            {"name": "hash_password", "file": "utils/crypto.py", "line": 12}
        ],
        "risk_level": "medium",
        "affected_files": ["api/auth.py", "utils/crypto.py"],
        "suggestion": "修改此函数可能影响2个调用者，请确保向后兼容"
    }
    """
```

### 4.2 修改的Tool Capabilities

```yaml
capabilities:
  - name: code.search
    description: "语义+精确+模糊混合搜索代码符号"
    endpoint: "POST /api/search/semantic"
    input_schema:
      type: object
      properties:
        project_id: {type: integer}
        query: {type: string, description: "自然语言查询"}
        top_k: {type: integer, default: 10}
        filters:
          type: object
          properties:
            node_type: {type: string, enum: [function, class, method, file]}
            return_type: {type: string}
            param_type: {type: string}
    
  - name: code.explore
    description: "代码结构探索（9种action）"
    endpoint: "POST /api/explore"
    
  - name: code.calls
    description: "调用链追踪"
    endpoint: "POST /api/calls"
    
  - name: code.impact
    description: "修改影响分析"
    endpoint: "POST /api/analyze/impact"
```

---

## 5. 任务拆分

### Phase 1：基础修复（1天）
| 任务 | 描述 | 优先级 |
|------|------|--------|
| T1.1 | 修复边类型不一致（统一小写） | P0 |
| T1.2 | 添加`nodes`表新字段（signature, docstring, return_type） | P0 |
| T1.3 | 添加`file_fingerprints`表 | P1 |
| T1.4 | 添加`node_embeddings`表 | P1 |

### Phase 2：增量索引（2天）
| 任务 | 描述 | 优先级 |
|------|------|--------|
| T2.1 | 实现文件指纹计算（SHA256） | P0 |
| T2.2 | 实现变更检测逻辑 | P0 |
| T2.3 | 重构IncrementalIndexer支持增量 | P0 |
| T2.4 | 添加`POST /api/index/incremental`接口 | P1 |

### Phase 3：类型信息提取（2天）
| 任务 | 描述 | 优先级 |
|------|------|--------|
| T3.1 | 增强tree-sitter提取签名/参数/返回类型 | P1 |
| T3.2 | 增强正则fallback提取类型信息 | P1 |
| T3.3 | 添加`GET /api/search/typed`接口 | P2 |

### Phase 4：语义搜索（3天）
| 任务 | 描述 | 优先级 |
|------|------|--------|
| T4.1 | 集成embedding模型（sentence-transformers或API） | P0 |
| T4.2 | 实现向量生成服务 | P0 |
| T4.3 | 实现向量存储和搜索 | P0 |
| T4.4 | 实现多维度融合评分 | P1 |
| T4.5 | 添加`POST /api/search/semantic`接口 | P1 |

### Phase 5：影响分析增强（1天）
| 任务 | 描述 | 优先级 |
|------|------|--------|
| T5.1 | 重构ImpactAnalyzer支持深度分析 | P2 |
| T5.2 | 添加修改建议生成 | P2 |
| T5.3 | 添加`POST /api/analyze/impact`接口 | P2 |

---

## 6. 依赖和风险

### 6.1 技术依赖
| 依赖 | 用途 | 备选方案 |
|------|------|----------|
| tree-sitter | AST解析 | 正则fallback |
| sentence-transformers | 本地embedding | OpenAI API |
| numpy | 向量计算 | 纯Python |

### 6.2 风险点
| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| embedding模型加载慢 | 首次启动延迟 | 模型缓存+异步加载 |
| 大项目索引内存溢出 | OOM | 分批索引+流式处理 |
| 向量搜索性能差 | 查询慢 | HNSW索引+缓存 |

---

## 7. 验收标准

| 验收项 | 标准 |
|--------|------|
| 语义搜索 | 输入"登录验证函数"能返回`verify_password` |
| 增量索引 | 修改单文件后重新索引<200ms |
| 类型过滤 | 能按返回类型`bool`过滤函数 |
| 影响分析 | 能列出所有调用者和被调用者 |
| 边类型 | 所有查询使用统一的小写类型 |
