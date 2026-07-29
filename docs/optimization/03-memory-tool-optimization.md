# Memory-Tool 工具优化设计文档

## 1. 现状分析

### 1.1 当前架构
```
memory-tool/
├── app/services/
│   ├── memory_service.py          # 基础CRUD（tool protocol后端）
│   ├── consolidation_service.py   # 记忆整合（隐私/矛盾/衰减）
│   ├── contradiction_detector.py  # 矛盾检测（关键词重叠）
│   ├── decay_scorer.py            # 衰减评分
│   └── privacy_filter.py          # 隐私过滤
├── app/db/models.py               # MemoryEntry, MemoryRelation, ContextPackage
└── app/api/
    ├── memories.py                # V2 UUID接口
    ├── memory.py                  # V1 整数ID接口
    ├── search.py                  # 向量/混合搜索
    └── context.py                 # 上下文包
```

### 1.2 现有能力
| 能力 | 实现方式 | 问题 |
|------|----------|------|
| 记忆CRUD | SQLAlchemy + UUID | V1/V2接口不统一 |
| 向量搜索 | pgvector (PostgreSQL) | SQLite下无向量搜索 |
| 矛盾检测 | 关键词重叠>0.6 | 无语义理解，误报高 |
| 隐私过滤 | 6种正则模式 | 覆盖面有限 |
| 衰减评分 | 时间+访问频率 | 无语义相关性 |

### 1.3 核心问题
1. **SQLite无向量搜索**：当前使用SQLite，pgvector不可用
2. **Embedding是Mock**：生成的向量无语义意义
3. **矛盾检测粗糙**：仅关键词重叠，无法理解否定/反转
4. **V1/V2接口不统一**：两套API并行，行为不一致
5. **无记忆整理**：相似记忆未合并，碎片化严重

---

## 2. 优化目标

| 目标 | 指标 | 当前值 | 目标值 |
|------|------|--------|--------|
| 搜索精准度 | Top-5命中率 | ~25% | >70% |
| 矛盾检测 | 准确率 | ~40% | >80% |
| 记忆整理 | 重复记忆合并 | 0% | >50% |
| 搜索延迟 | P95延迟 | ~100ms | <50ms |
| 记忆质量 | 有效记忆比例 | ~60% | >85% |

---

## 3. 优化设计

### 3.1 模块一：SQLite向量搜索增强

#### 3.1.1 BM25全文搜索

**新增文件：`app/services/bm25_search.py`**
```python
import math
from collections import Counter
from typing import List, Dict, Tuple

class BM25Search:
    """BM25全文搜索引擎"""
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_lengths = []
        self.avg_doc_length = 0
        self.doc_freqs = Counter()
        self.idf = {}
    
    def index(self, documents: List[Dict]):
        """构建索引"""
        # 计算文档长度
        self.doc_lengths = [len(doc['content'].split()) for doc in documents]
        self.avg_doc_length = sum(self.doc_lengths) / len(self.doc_lengths)
        
        # 计算文档频率
        for doc in documents:
            words = set(doc['content'].lower().split())
            for word in words:
                self.doc_freqs[word] += 1
        
        # 计算IDF
        n_docs = len(documents)
        for word, freq in self.doc_freqs.items():
            self.idf[word] = math.log((n_docs - freq + 0.5) / (freq + 0.5) + 1)
    
    def search(self, query: str, documents: List[Dict], top_k: int = 10) -> List[Tuple[int, float]]:
        """BM25搜索"""
        query_words = query.lower().split()
        scores = []
        
        for i, doc in enumerate(documents):
            doc_words = doc['content'].lower().split()
            doc_len = self.doc_lengths[i]
            score = 0.0
            
            for word in query_words:
                if word in doc_words:
                    tf = doc_words.count(word)
                    idf = self.idf.get(word, 0)
                    numerator = tf * (self.k1 + 1)
                    denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_length)
                    score += idf * numerator / denominator
            
            scores.append((i, score))
        
        # 按分数排序
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]
```

#### 3.1.2 TF-IDF搜索

**新增文件：`app/services/tfidf_search.py`**
```python
import math
from collections import Counter
from typing import List, Dict, Tuple

class TFIDFSearch:
    """TF-IDF搜索引擎"""
    
    def __init__(self):
        self.vocabulary = set()
        self.idf = {}
    
    def index(self, documents: List[Dict]):
        """构建索引"""
        # 构建词汇表
        for doc in documents:
            words = doc['content'].lower().split()
            self.vocabulary.update(words)
        
        # 计算IDF
        n_docs = len(documents)
        for word in self.vocabulary:
            doc_count = sum(1 for doc in documents if word in doc['content'].lower())
            self.idf[word] = math.log(n_docs / (doc_count + 1))
    
    def search(self, query: str, documents: List[Dict], top_k: int = 10) -> List[Tuple[int, float]]:
        """TF-IDF搜索"""
        query_words = query.lower().split()
        scores = []
        
        for i, doc in enumerate(documents):
            doc_words = doc['content'].lower().split()
            doc_len = len(doc_words)
            
            # 计算TF-IDF向量
            tfidf = Counter()
            for word in doc_words:
                tf = doc_words.count(word) / doc_len
                tfidf[word] = tf * self.idf.get(word, 0)
            
            # 计算查询向量
            query_tfidf = Counter()
            for word in query_words:
                query_tfidf[word] = self.idf.get(word, 0)
            
            # 余弦相似度
            dot_product = sum(tfidf[w] * query_tfidf[w] for w in query_words if w in tfidf)
            norm1 = math.sqrt(sum(v**2 for v in tfidf.values()))
            norm2 = math.sqrt(sum(v**2 for v in query_tfidf.values()))
            
            score = dot_product / (norm1 * norm2 + 1e-10)
            scores.append((i, score))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]
```

#### 3.1.3 混合搜索融合

**修改：`app/services/search.py`**
```python
async def hybrid_search(
    query: str,
    project: str,
    vector_weight: float = 0.5,
    text_weight: float = 0.3,
    bm25_weight: float = 0.2,
    top_k: int = 10
) -> List[SearchResult]:
    """混合搜索：向量 + TF-IDF + BM25"""
    
    # 1. 获取所有候选记忆
    all_memories = await get_all_memories(project)
    
    # 2. 向量搜索（如果有embedding）
    vector_results = []
    if has_embedding_support():
        vector_results = await vector_search(query, project, top_k=top_k*2)
    
    # 3. TF-IDF搜索
    tfidf_search = TFIDFSearch()
    tfidf_search.index([{'content': m['content']} for m in all_memories])
    tfidf_results = tfidf_search.search(query, [{'content': m['content']} for m in all_memories])
    
    # 4. BM25搜索
    bm25_search = BM25Search()
    bm25_search.index([{'content': m['content']} for m in all_memories])
    bm25_results = bm25_search.search(query, [{'content': m['content']} for m in all_memories])
    
    # 5. 融合分数
    fused_scores = {}
    for idx, score in vector_results:
        fused_scores[idx] = fused_scores.get(idx, 0) + score * vector_weight
    for idx, score in tfidf_results:
        fused_scores[idx] = fused_scores.get(idx, 0) + score * text_weight
    for idx, score in bm25_results:
        fused_scores[idx] = fused_scores.get(idx, 0) + score * bm25_weight
    
    # 6. 排序并返回Top-K
    sorted_results = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
    return [
        SearchResult(
            memory=all_memories[idx],
            score=score,
            score_breakdown={
                'vector': vector_weight * dict(vector_results).get(idx, 0),
                'tfidf': text_weight * dict(tfidf_results).get(idx, 0),
                'bm25': bm25_weight * dict(bm25_results).get(idx, 0)
            }
        )
        for idx, score in sorted_results[:top_k]
    ]
```

### 3.2 模块二：语义矛盾检测

#### 3.2.1 基于Embedding的矛盾检测

**新增文件：`app/services/semantic_contradiction.py`**
```python
from typing import List, Dict, Optional
import numpy as np

class SemanticContradictionDetector:
    """基于语义的矛盾检测器"""
    
    # 矛盾关键词模式
    NEGATION_PATTERNS = [
        r'不要', r'禁止', r'不能', r'不应该', r'避免',
        r'do not', r'don\'t', r'should not', r'avoid', r'never',
        r'不建议', r'不推荐', r'禁止使用'
    ]
    
    # 否定词
    NEGATION_WORDS = {'不', '没', '未', '非', '别', '莫', '勿', 'no', 'not', 'never', 'don\'t'}
    
    def __init__(self, embedding_provider=None):
        self.embedding_provider = embedding_provider
    
    async def detect_contradictions(
        self,
        new_memory: Dict,
        existing_memories: List[Dict]
    ) -> List[Dict]:
        """检测新记忆与现有记忆的矛盾"""
        contradictions = []
        
        # 1. 语义相似度过滤（只检查高相似度的记忆）
        similar_memories = await self._find_similar(new_memory, existing_memories, threshold=0.7)
        
        for existing in similar_memories:
            # 2. 检查否定模式
            has_negation = self._check_negation_pattern(new_memory['content'], existing['content'])
            
            # 3. 检查语义反转
            has_semantic_reversal = await self._check_semantic_reversal(new_memory, existing)
            
            # 4. 判断是否矛盾
            if has_negation or has_semantic_reversal:
                contradictions.append({
                    'existing_memory': existing,
                    'contradiction_type': 'negation' if has_negation else 'semantic_reversal',
                    'confidence': 0.8 if has_negation and has_semantic_reversal else 0.6,
                    'evidence': self._generate_evidence(new_memory, existing)
                })
        
        return contradictions
    
    def _check_negation_pattern(self, text1: str, text2: str) -> bool:
        """检查否定模式"""
        for pattern in self.NEGATION_PATTERNS:
            if (re.search(pattern, text1) and not re.search(pattern, text2)) or \
               (not re.search(pattern, text1) and re.search(pattern, text2)):
                return True
        return False
    
    async def _check_semantic_reversal(self, memory1: Dict, memory2: Dict) -> bool:
        """检查语义反转"""
        if not self.embedding_provider:
            return False
        
        # 生成embedding
        emb1 = await self.embedding_provider.generate([memory1['content']])
        emb2 = await self.embedding_provider.generate([memory2['content']])
        
        # 计算相似度
        similarity = cosine_similarity(emb1[0].vector, emb2[0].vector)
        
        # 如果语义相似但包含否定词，可能是矛盾
        if similarity > 0.7:
            words1 = set(memory1['content'].lower().split())
            words2 = set(memory2['content'].lower().split())
            
            # 检查是否有否定词差异
            neg1 = words1 & self.NEGATION_WORDS
            neg2 = words2 & self.NEGATION_WORDS
            
            if bool(neg1) != bool(neg2):
                return True
        
        return False
    
    def _generate_evidence(self, memory1: Dict, memory2: Dict) -> str:
        """生成矛盾证据"""
        return f"""新记忆: {memory1['title']} - {memory1['content'][:100]}
现有记忆: {memory2['title']} - {memory2['content'][:100]}
矛盾类型: 否定模式检测"""
```

#### 3.2.2 矛盾处理策略

```python
class ContradictionHandler:
    """矛盾处理策略"""
    
    async def handle_contradiction(
        self,
        new_memory: Dict,
        existing_memory: Dict,
        contradiction_type: str,
        confidence: float
    ) -> Dict:
        """处理矛盾"""
        
        if confidence > 0.8:
            # 高置信度：标记为待审核
            return {
                'action': 'flag_for_review',
                'reason': '高置信度矛盾，需要人工审核',
                'suggested_action': '保留现有记忆，标记新记忆为待审核'
            }
        elif confidence > 0.6:
            # 中置信度：检查时间戳
            if new_memory['created_at'] > existing_memory['created_at']:
                return {
                    'action': 'update_existing',
                    'reason': '新记忆更新，可能是最新实践',
                    'suggested_action': '更新现有记忆内容'
                }
            else:
                return {
                    'action': 'keep_both',
                    'reason': '时间相近，保留两者供后续参考',
                    'suggested_action': '添加关联关系标记矛盾'
                }
        else:
            # 低置信度：保留两者
            return {
                'action': 'keep_both',
                'reason': '低置信度，可能是不同场景',
                'suggested_action': '添加标签区分场景'
            }
```

### 3.3 模块三：记忆整理器

#### 3.3.1 相似记忆合并

**新增文件：`app/services/memory_consolidation.py`**
```python
from typing import List, Dict
import numpy as np

class MemoryConsolidator:
    """记忆整理器：合并相似记忆，清理碎片"""
    
    async def consolidate(
        self,
        project: str,
        similarity_threshold: float = 0.85
    ) -> ConsolidationResult:
        """整理项目记忆"""
        
        # 1. 获取所有记忆
        memories = await get_all_memories(project)
        
        # 2. 计算相似度矩阵
        similarity_matrix = await self._compute_similarity_matrix(memories)
        
        # 3. 聚类相似记忆
        clusters = self._cluster_memories(memories, similarity_matrix, threshold=similarity_threshold)
        
        # 4. 合并每个集群
        merged_count = 0
        for cluster in clusters:
            if len(cluster) > 1:
                await self._merge_cluster(cluster)
                merged_count += len(cluster) - 1
        
        return ConsolidationResult(
            total_memories=len(memories),
            clusters_found=len(clusters),
            memories_merged=merged_count
        )
    
    async def _compute_similarity_matrix(self, memories: List[Dict]) -> np.ndarray:
        """计算相似度矩阵"""
        n = len(memories)
        matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(i+1, n):
                similarity = await self._compute_similarity(memories[i], memories[j])
                matrix[i][j] = similarity
                matrix[j][i] = similarity
        
        return matrix
    
    def _cluster_memories(
        self,
        memories: List[Dict],
        similarity_matrix: np.ndarray,
        threshold: float
    ) -> List[List[int]]:
        """聚类相似记忆（简单层次聚类）"""
        n = len(memories)
        visited = set()
        clusters = []
        
        for i in range(n):
            if i in visited:
                continue
            
            cluster = [i]
            visited.add(i)
            
            for j in range(i+1, n):
                if j in visited:
                    continue
                
                if similarity_matrix[i][j] >= threshold:
                    cluster.append(j)
                    visited.add(j)
            
            clusters.append(cluster)
        
        return clusters
    
    async def _merge_cluster(self, cluster_indices: List[int]):
        """合并一个集群的记忆"""
        memories = [await get_memory(idx) for idx in cluster_indices]
        
        # 按重要性排序
        memories.sort(key=lambda m: m.get('confidence_score', 1.0), reverse=True)
        
        # 保留最重要的记忆，合并内容
        primary = memories[0]
        merged_content = primary['content']
        
        for secondary in memories[1:]:
            merged_content += f"\n\n---\n补充信息: {secondary['content']}"
        
        # 更新主要记忆
        await update_memory(
            primary['id'],
            content=merged_content,
            merged_from=[m['id'] for m in memories[1:]]
        )
        
        # 软删除其他记忆
        for secondary in memories[1:]:
            await soft_delete_memory(secondary['id'])
```

#### 3.3.2 记忆热度追踪

```python
class MemoryHeatTracker:
    """记忆热度追踪"""
    
    async def track_access(self, memory_id: str):
        """追踪记忆访问"""
        memory = await get_memory(memory_id)
        
        # 更新访问计数
        new_access_count = memory.get('access_count', 0) + 1
        
        # 计算热度分数
        heat_score = self._calculate_heat(
            access_count=new_access_count,
            last_accessed=memory.get('last_accessed_at'),
            created_at=memory.get('created_at')
        )
        
        # 更新记忆
        await update_memory(
            memory_id,
            access_count=new_access_count,
            last_accessed_at=datetime.now(timezone.utc),
            heat_score=heat_score
        )
    
    def _calculate_heat(
        self,
        access_count: int,
        last_accessed: datetime,
        created_at: datetime
    ) -> float:
        """计算热度分数"""
        # 时间衰减
        days_since_access = (datetime.now(timezone.utc) - last_accessed).days
        time_decay = max(0.1, 1.0 - days_since_access / 30)
        
        # 访问频率
        access_boost = min(1.0, access_count / 10)
        
        # 综合热度
        heat = time_decay * 0.6 + access_boost * 0.4
        
        return round(heat, 2)
```

### 3.4 模块四：API统一

#### 3.4.1 V1/V2接口合并

**修改：`app/api/memories.py`**
```python
# 统一接口，支持两种ID格式
@router.get("/api/memories/{memory_id}")
async def get_memory(
    memory_id: str,  # 支持UUID和整数ID
    include_relations: bool = True
):
    """获取单个记忆"""
    
    # 判断ID格式
    if memory_id.isdigit():
        # 整数ID（V1兼容）
        memory = await get_memory_by_integer_id(int(memory_id))
    else:
        # UUID（V2）
        memory = await get_memory_by_uuid(memory_id)
    
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    # 包含关系
    if include_relations:
        memory['relations'] = await get_memory_relations(memory['id'])
    
    return {"data": memory}
```

---

## 4. API设计

### 4.1 新增/修改的API

#### 混合搜索
```python
@router.post("/api/memories/search/hybrid")
async def hybrid_search(request: HybridSearchRequest):
    """
    混合搜索：向量 + TF-IDF + BM25
    
    Request:
    {
        "query": "上次修复的cookie问题",
        "project": "aidp",
        "weights": {
            "vector": 0.5,
            "tfidf": 0.3,
            "bm25": 0.2
        },
        "top_k": 10
    }
    
    Response:
    {
        "results": [
            {
                "memory": {...},
                "score": 0.87,
                "score_breakdown": {
                    "vector": 0.42,
                    "tfidf": 0.25,
                    "bm25": 0.20
                }
            }
        ],
        "total": 1,
        "search_type": "hybrid"
    }
    """
```

#### 记忆整理
```python
@router.post("/api/memories/consolidate")
async def consolidate_memories(request: ConsolidateRequest):
    """
    整理记忆：合并相似记忆，清理碎片
    
    Request:
    {
        "project": "aidp",
        "similarity_threshold": 0.85,
        "dry_run": false
    }
    
    Response:
    {
        "total_memories": 100,
        "clusters_found": 15,
        "memories_merged": 30,
        "clusters": [
            {
                "primary": "cookie修复方案",
                "merged": ["cookie问题", "登录cookie"],
                "similarity": 0.92
            }
        ]
    }
    """
```

#### 矛盾检测
```python
@router.post("/api/memories/check-contradictions")
async def check_contradictions(request: ContradictionCheckRequest):
    """
    检测新记忆与现有记忆的矛盾
    
    Request:
    {
        "project": "aidp",
        "new_memory": {
            "title": "cookie配置",
            "content": "不要使用localStorage存储cookie"
        }
    }
    
    Response:
    {
        "contradictions": [
            {
                "existing_memory": {
                    "id": "mem-123",
                    "title": "cookie安全配置",
                    "content": "使用localStorage存储敏感cookie"
                },
                "contradiction_type": "negation",
                "confidence": 0.8,
                "evidence": "新记忆说'不要使用'，现有记忆说'使用'"
            }
        ],
        "has_contradictions": true
    }
    """
```

---

## 5. 任务拆分

### Phase 1：搜索增强（2天）
| 任务 | 描述 | 优先级 |
|------|------|--------|
| T1.1 | 实现BM25搜索引擎 | P0 |
| T1.2 | 实现TF-IDF搜索引擎 | P0 |
| T1.3 | 实现混合搜索融合 | P0 |
| T1.4 | 添加混合搜索API | P1 |

### Phase 2：矛盾检测增强（1天）
| 任务 | 描述 | 优先级 |
|------|------|--------|
| T2.1 | 实现语义矛盾检测器 | P1 |
| T2.2 | 实现矛盾处理策略 | P1 |
| T2.3 | 添加矛盾检测API | P2 |

### Phase 3：记忆整理（2天）
| 任务 | 描述 | 优先级 |
|------|------|--------|
| T3.1 | 实现相似度计算 | P1 |
| T3.2 | 实现记忆聚类 | P1 |
| T3.3 | 实现记忆合并 | P1 |
| T3.4 | 添加整理API | P2 |

### Phase 4：热度追踪（1天）
| 任务 | 描述 | 优先级 |
|------|------|--------|
| T4.1 | 实现热度计算 | P2 |
| T4.2 | 实现访问追踪 | P2 |
| T4.3 | 添加热度排序 | P2 |

### Phase 5：API统一（1天）
| 任务 | 描述 | 优先级 |
|------|------|--------|
| T5.1 | 统一V1/V2接口 | P1 |
| T5.2 | 添加ID格式兼容 | P1 |
| T5.3 | 更新Tool Capabilities | P2 |

---

## 6. 依赖和风险

### 6.1 技术依赖
| 依赖 | 用途 | 备选方案 |
|------|------|----------|
| numpy | 向量计算 | 纯Python |
| sentence-transformers | 本地embedding | OpenAI API |
| scikit-learn | 聚类算法 | 自定义算法 |

### 6.2 风险点
| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 合并后信息丢失 | 重要细节被删除 | 保留原始记忆备份 |
| 矛盾检测误报 | 合法记忆被标记 | 置信度阈值+人工审核 |
| 热度计算偏差 | 新记忆被埋没 | 时间衰减参数可调 |

---

## 7. 验收标准

| 验收项 | 标准 |
|--------|------|
| 混合搜索 | 输入"cookie问题"能返回相关修复记录 |
| 矛盾检测 | 输入与现有矛盾的记忆能被识别 |
| 记忆整理 | 相似度>0.85的记忆能被合并 |
| 热度追踪 | 高频访问的记忆排序靠前 |
| API统一 | V1/V2接口行为一致 |
