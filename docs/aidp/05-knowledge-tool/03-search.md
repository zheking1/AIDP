# Search - Hybrid Keyword + Vector Search

## 架构

`SearchService` (`search_service.py`) 实现了**两层检索架构** + **多路混合评分**：

```
Layer 1: 摘要级搜索 (_search_summary_level)
    ↓ 过滤文档候选 (top ~30)
Layer 2: Chunk级搜索 (_search_chunk_level)
    ↓ 精确评分
Dedup: 跨层去重 (_deduplicate_by_topic)
    ↓
Final Results (top_k)
```

## 知识库解析 (`_resolve_kb_ids`)

搜索范围可通过三种方式指定，按优先级：

1. **直接指定** `knowledge_base_ids`
2. **通过 project_id**: 查询 `ProjectKnowledgeBinding` 获取关联知识库，并递归爬取父级知识库（`_collect_ancestor_ids`）
3. **通过 workspace_id**: 查询所有未删除的知识库

## 领域过滤 (`_match_domains`)

支持按 `task_domains` 过滤知识库：
- 大小写不敏感匹配
- KB 的 `domains` 集合与请求的 `task_domains` 有交集即通过

---

## 核心搜索方法

### `search()` — 传统摘要+Chunk双级搜索

```python
async def search(query, workspace_id, project_id, knowledge_base_ids,
                 task_domains, top_k=8, min_score=0.15)
```

流程：
1. 解析知识库 ID → 加载 KB 信息映射 → 领域过滤
2. `_search_summary_level`: 按标题/摘要/标签评分，取前 15~30 个文档
3. `_search_chunk_level`: 对候选文档的所有 chunks 做文本匹配评分
4. 去重、排序、截取 `top_k`，生成 `citation_id`

### `semantic_search()` — 混合搜索（Exact + Vector + BM25）

```python
async def semantic_search(query, workspace_id, project_id, knowledge_base_ids,
                          task_domains, top_k=8, search_mode="hybrid")
```

支持 **4 种模式**（通过 `search_mode` 参数）：
- `"hybrid"` — 全部三路融合
- `"exact"` — 仅精确匹配
- `"vector"` — 仅向量相似度
- `"bm25"` — 仅 BM25 文本检索

**融合权重**：
```
score = exact_score × 0.35 + vector_score × 0.40 + text_score × 0.25
```

返回结果包含 `score_breakdown` 字段展示各项权重。

---

## 评分算法

### 1. Exact Match (`_score_exact`)

采用三级匹配策略：

| 匹配类型 | 权重 | 说明 |
|----------|------|------|
| 词边界全文匹配 | 1.0 | 查询词在标题中作为独立词出现 |
| 子串匹配 | 0.9 | 查询词在标题中出现 |
| 代码定义匹配 | 0.8 | `def/class/function/const/var/let + 查询词` 在标题中 |
| 以上在 content 中 | ×0.8 | 在内容中而非标题中匹配，折扣 20% |
| 多词部分匹配 | 0.5~0.6 | 80%+ 的查询单词在标题/内容中 |

### 2. Vector Similarity (`_score_vector`)

- 从 chunk 的 `_embedding` 字段读取预存储向量
- 使用相同嵌入提供者生成查询向量
- 计算 **余弦相似度**: `cosine_similarity(query_emb, chunk_emb)`

### 3. BM25 (`_score_bm25`)

经典 BM25 实现：
- `k1 = 1.5`（词频饱和参数）
- `b = 0.75`（长度归一化）
- `avg_doc_length = 200`（固定平均文档长度）
- 结果归一化到 `[0, 1]`

### 4. Summary Level 评分 (`_compute_text_score`)

用于文档级别的粗筛：
```python
score = title_score × 0.5 + summary_score × 0.3 + min(tag_score, 0.2)
```
- 标题权重最高
- 摘要辅助
- 标签加分上限 0.2

其中 `title_score`/`summary_score` 基于：
- 子串包含: `0.6 + 0.3 × min(1.0, len(query)/len(text))`
- Jaccard 词重叠: `0.3 × Jaccard + 0.7 × 覆盖率`

---

## 去重策略 (`_deduplicate_by_topic`)

**跨层去重**: 同主题内容保留最高层级的知识库

层级优先级：
```
project (3) > template (2) > framework (1)
```

主题提取 (`_extract_topic`):
- 取标题 + 前 200 字符内容
- 去除中英文停用词
- 取前 5 个长度 > 2 的核心词拼接

---

## 输出格式

```json
{
    "items": [
        {
            "chunk_id": "...",
            "document_id": "...",
            "title": "...",
            "content": "...",
            "score": 0.85,
            "citation_id": "doc123:chunk5",
            "heading_path": ["## Introduction", "### Setup"],
            "source_start_line": 42,
            "source_end_line": 120,
            "knowledge_base_id": "...",
            "kb_name": "...",
            "kb_level": "project"
        }
    ],
    "total": 8,
    "matched_kb_ids": [...],
    "search_mode": "hybrid",
    "reranked": false
}
```

---

## 向后兼容

文件中还包含两个遗留搜索类：
- **FTS5SearchService**: 基于 `title ILIKE` 的简单全文搜索
- **SemanticSearchService**: 基于 Jaccard 词的文档级搜索

这些通过 `/api/documents/search/fts` 和 `/api/documents/search/semantic` 端点暴露，主要用于向后兼容。