# AIDP 全链路测试方案

## 测试环境

| 项目 | 值 |
|------|-----|
| NAS | `192.168.0.100` |
| Controller | `http://localhost:8883` |
| 数据库 | `novel-postgres:5432`, `aidp` |
| 测试用户 | `lwg9264` (admin) |

---

## 一、模型管理测试

### 1.1 模型CRUD API

| # | 测试项 | 验证点 |
|---|--------|--------|
| 1 | `GET /api/models` | 返回8个模型，含api_key/max_tokens/temperature |
| 2 | `GET /api/models/for-task/chat` | 返回优先级最高的chat模型(DeepSeek V3.2) |
| 3 | `GET /api/models/for-task/embedding` | 返回BGE-M3，含api_base和api_key |
| 4 | `GET /api/models/for-task/rerank` | 返回BGE-Reranker V2-M3 |
| 5 | 创建模型 | POST成功，返回新模型 |
| 6 | 编辑模型 | PUT修改temperature，验证生效 |
| 7 | 删除模型 | DELETE成功，for-task返回下一个优先模型 |

### 1.2 模型数据完整性

| # | 测试项 | 验证点 |
|---|--------|--------|
| 8 | chat模型含api_key | api_key不为null |
| 9 | embedding模型api_base正确 | `https://api.siliconflow.cn/v1/embeddings` |
| 10 | rerank模型api_base正确 | `https://api.siliconflow.cn/v1/rerank` |

---

## 二、模型调用链路测试

### 2.1 skill-router — 意图分析（chat模型）

| # | 测试项 | 验证点 |
|---|--------|--------|
| 11 | `analyze_intent` MCP调用 | 返回intent/domains/complexity字段 |
| 12 | 模型来源 | 调用Controller获取DeepSeek V3.2配置 |
| 13 | 正确的API路径 | 请求`https://qianfan.baidubce.com/v2/coding/chat/completions` |
| 14 | 正确的API Key | 使用BaiduBCE的key |
| 15 | 正确的temperature | 0.3 |
| 16 | 降级测试 | 停用所有chat模型，验证降级到settings配置 |

### 2.2 skill-router — 技能重排（rerank模型）

| # | 测试项 | 验证点 |
|---|--------|--------|
| 17 | `skill_run` MCP调用 | 返回匹配的技能列表 |
| 18 | 重排模型来源 | 调用Controller获取BGE-Reranker V2-M3 |
| 19 | 正确的API路径 | 请求`https://api.siliconflow.cn/v1/rerank` |
| 20 | 返回relevance_score | 每个技能有relevance_score(0-1) |
| 21 | 降级测试 | 停用rerank模型，验证降级到LLM prompt重排 |

### 2.3 skill-router — 向量生成（embedding模型）

| # | 测试项 | 验证点 |
|---|--------|--------|
| 22 | 技能注册时生成embedding | 调用Controller获取BGE-M3 |
| 23 | 正确的API路径 | 请求`https://api.siliconflow.cn/v1/embeddings/embeddings` |
| 24 | 返回384维向量 | 向量长度=384 |

### 2.4 knowledge-tool — 文档索引（embedding模型）

| # | 测试项 | 验证点 |
|---|--------|--------|
| 25 | 创建索引任务 | 文档上传后触发索引 |
| 26 | provider选择 | 读取settings.EMBEDDING_PROVIDER |
| 27 | mock模式搜索 | 索引和搜索使用相同provider |
| 28 | 升级为openai模式 | 修改settings为openai，搜索使用OpenAI API |

### 2.5 knowledge-tool — 三级语义搜索

| # | 测试项 | 验证点 |
|---|--------|--------|
| 29 | `semantic_search(mode=hybrid)` | 返回items含score_breakdown(exact/vector/text) |
| 30 | `semantic_search(mode=exact)` | 精确匹配函数名/类名 |
| 31 | `semantic_search(mode=vector)` | 向量相似度搜索 |
| 32 | `semantic_search(mode=bm25)` | BM25文本搜索 |
| 33 | 搜索无数据时 | 返回空items而非报错 |

### 2.6 code-index — 语义搜索（embedding模型）

| # | 测试项 | 验证点 |
|---|--------|--------|
| 34 | 模型降级链 | 本地sentence-transformers → Controller API → mock |
| 35 | 无本地模型时 | 自动从Controller获取embedding模型 |
| 36 | 多维度融合 | score含vector/exact/fuzzy三项 |

---

## 三、各工具功能测试

### 3.1 code-index

| # | 测试项 | 验证点 |
|---|--------|--------|
| 37 | 边类型全部小写 | SELECT DISTINCT edge_type 无大写 |
| 38 | nodes新字段 | signature/docstring/return_type/params_json/file_hash存在 |
| 39 | 新表file_fingerprints | 表存在且可写入 |
| 40 | 新表node_embeddings | 表存在且可写入 |
| 41 | typed搜索 | `GET /api/search/typed?node_type=function`返回结果 |
| 42 | MCP code.search | 返回success:true |
| 43 | MCP code.search.semantic | 返回success:true |
| 44 | MCP code.explore | 9种action均可执行 |
| 45 | MCP code.calls | 调用链追踪正常 |

### 3.2 knowledge-tool

| # | 测试项 | 验证点 |
|---|--------|--------|
| 46 | 文档上传 | 上传markdown文件 |
| 47 | 文档索引 | 触发索引任务，chunk生成 |
| 48 | 基础搜索 | `/api/knowledge/search`返回结果 |
| 49 | 语义搜索 | `/api/knowledge/search/semantic`返回结果 |
| 50 | MCP knowledge.search | 返回success:true |

### 3.3 memory-tool

| # | 测试项 | 验证点 |
|---|--------|--------|
| 51 | 创建记忆 | 返回UUID和完整字段 |
| 52 | 基础搜索 | LIKE搜索返回结果 |
| 53 | 混合搜索 | 返回score_breakdown(bm25/tfidf) |
| 54 | 矛盾检测 | 检测否定模式 |
| 55 | 记忆整理 | 返回total_memories/clusters_found |
| 56 | Context Package | 返回project+memories |
| 57 | 更新/删除 | 操作成功 |

### 3.4 quality-tool

| # | 测试项 | 验证点 |
|---|--------|--------|
| 58 | Python代码检查 | 检测函数长度/复杂度 |
| 59 | JavaScript代码检查 | 多语言支持 |
| 60 | 安全扫描 | 检测os.system/eval等危险调用 |

### 3.5 sandbox-tool

| # | 测试项 | 验证点 |
|---|--------|--------|
| 61 | Python执行 | stdout正确输出 |
| 62 | Bash执行 | bash命令正常执行 |
| 63 | 执行历史 | 返回历史记录 |

---

## 四、Controller流水线测试

### 4.1 上下文缓存

| # | 测试项 | 验证点 |
|---|--------|--------|
| 64 | 首次aidp_context | cache_stats.misses > 0 |
| 65 | 相同查询第二次 | cache_stats.hits > 0 |
| 66 | 不同查询 | 不命中缓存 |

### 4.2 降级策略

| # | 测试项 | 验证点 |
|---|--------|--------|
| 67 | 停用memory-tool | FallbackManager返回降级消息 |
| 68 | 停用knowledge-tool | 流水线不中断，继续执行 |
| 69 | fallback_status | 含failed_tools列表 |

### 4.3 重试机制

| # | 测试项 | 验证点 |
|---|--------|--------|
| 70 | 工具调用失败 | 自动重试3次(指数退避) |
| 71 | 3次均失败 | 返回空结果，不中断流水线 |

### 4.4 MCP工具链

| # | 测试项 | 验证点 |
|---|--------|--------|
| 72 | `list_registered_tools` | 返回所有工具及状态 |
| 73 | `check_tool_health` | 全部healthy |
| 74 | `aidp_context` | 返回system_prompt/metadata |
| 75 | `invoke_tool_mcp` | 跨工具调用成功 |
| 76 | `manage_models` | 列出/添加/删除模型 |

---

## 五、测试执行顺序

```
Phase 1: 基础健康 (5分钟)
├── 所有工具健康检查
├── 模型API (1.1-1.2)
└── 数据库模式验证

Phase 2: 模型调用链路 (15分钟)
├── skill-router chat模型 (2.1)
├── skill-router rerank模型 (2.2)
├── skill-router embedding模型 (2.3)
├── knowledge-tool embedding (2.4)
└── code-index embedding (2.6)

Phase 3: 工具功能 (20分钟)
├── code-index (3.1)
├── knowledge-tool (3.2)
├── memory-tool (3.3)
├── quality-tool (3.4)
└── sandbox-tool (3.5)

Phase 4: 流水线 + MCP (10分钟)
├── 缓存/降级/重试 (4.1-4.3)
└── MCP工具链 (4.4)
```

---

## 六、验收标准

| 维度 | 标准 |
|------|------|
| 模型API | 8个模型CRUD正常，for-task返回正确优先级 |
| 模型调用 | chat成功调BaiduBCE，embedding调SiliconFlow，rerank调SiliconFlow |
| 工具功能 | 所有MCP capability返回success:true |
| 流水线 | cache命中率>0，fallback不中断，retry生效 |
| 数据一致性 | 搜索使用的provider与索引一致 |
| 降级健壮 | 任一工具停用不影响整体流程 |

---

## 七、已知风险点

| 风险 | 说明 |
|------|------|
| BaiduBCE API路径 | `/v2/coding/chat/completions`是否有效，可能需调整 |
| SiliconFlow embedding路径 | `/v1/embeddings/embeddings` 可能应为 `/v1/embeddings` |
| skill-router container | 构建耗时较长(5-10分钟) |
| knowledge-tool mock模式 | 向量无语义意义，搜索结果随机 |