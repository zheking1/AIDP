# Context Optimizer 设计文档

---

## 目录

1. [定位与目标](#1-定位与目标)
2. [架构设计](#2-架构设计)
3. [核心组件](#3-核心组件)
4. [数据流](#4-数据流)
5. [API 设计](#5-api-设计)
6. [与现有工具集成](#6-与现有工具集成)
7. [实施计划](#7-实施计划)

---

## 1. 定位与目标

### 1.1 核心问题

AI Agent 在编程时面临上下文溢出风险：
- 多个工具并行返回大量数据
- Agent 上下文窗口有限（4k-128k tokens）
- 过多上下文导致幻觉、丢失关键信息

### 1.2 解决方案

**Context Optimizer** 是 AIDP 系统的**上下文优化器**，负责：
- 分析任务需求，确定需要什么信息
- 分配 token 预算，控制各工具返回量
- 精简工具输出，只保留关键信息
- 避免重复获取，跟踪已有信息

### 1.3 设计原则

| 原则 | 描述 |
|------|------|
| **先分析后获取** | 不盲目获取所有信息 |
| **按需分配** | 根据任务复杂度分配预算 |
| **渐进披露** | 先返回摘要，详情按需 |
| **避免重复** | 跟踪已有信息，不重复获取 |

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         Context Optimizer                                       │
│                         端口: 18088                                              │
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
│  │  {                                                                         │ │
│  │    "tools": ["knowledge", "code-index"],                                   │ │
│  │    "queries": {                                                            │ │
│  │      "knowledge": ["JWT认证流程", "Spring Security配置"],                  │ │
│  │      "code-index": ["AuthController", "SecurityConfig"]                    │ │
│  │    },                                                                      │ │
│  │    "budget": {                                                             │ │
│  │      "knowledge": 2000,                                                    │ │
│  │      "code-index": 3000                                                    │ │
│  │    },                                                                      │ │
│  │    "existing": ["已了解JWT基本概念"]                                        │ │
│  │  }                                                                         │ │
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

### 2.2 组件交互

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         组件交互图                                               │
│                                                                                   │
│  AI Agent                                                                        │
│     │                                                                            │
│     │  1. 提交任务                                                               │
│     ▼                                                                            │
│  Context Optimizer                                                               │
│     │                                                                            │
│     │  2. 需求分析                                                               │
│     ├──────────────────────────────────────────────────────────────►            │
│     │                                                                             │
│     │  3. 返回检索计划                                                           │
│     │◄──────────────────────────────────────────────────────────────            │
│     │                                                                             │
│     │  4. 按需获取                                                               │
│     ├──────────────────────────────────────────────────────────────►            │
│     │                                                                             │
│     │  5. 返回精简结果                                                           │
│     │◄──────────────────────────────────────────────────────────────            │
│     │                                                                             │
│     │  6. 返回给 Agent                                                          │
│     ▼                                                                            │
│  AI Agent                                                                        │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 核心组件

### 3.1 需求分析器

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
        
        # 实体提取（正则匹配）
        entities = self.extract_entities(task)
        
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

### 3.2 预算分配器

```python
class BudgetAllocator:
    """预算分配器"""
    
    # 默认预算分配
    DEFAULT_BUDGET = 8000  # 总预算
    
    # 工具优先级
    TOOL_PRIORITY = {
        "code-index": 1.5,      # 代码理解最重要
        "knowledge": 1.2,       # 文档理解次之
        "memory": 1.0,          # 经验参考
        "asset": 0.8,           # 代码片段
        "quality": 0.5,         # 质量检查
        "sandbox": 0.3          # 执行结果
    }
    
    def allocate(self, plan: RetrievalPlan, total_budget: int = None) -> Dict[str, int]:
        """分配预算"""
        
        budget = total_budget or self.DEFAULT_BUDGET
        allocation = {}
        
        # 计算每个工具的基础预算
        for tool in plan.tools:
            priority = self.TOOL_PRIORITY.get(tool, 1.0)
            base_budget = budget * (priority / sum(self.TOOL_PRIORITY.values()))
            allocation[tool] = int(base_budget)
        
        # 根据查询数量调整
        for tool, queries in plan.queries.items():
            if tool in allocation:
                query_factor = len(queries) / 2  # 每个查询约 2000 tokens
                allocation[tool] = int(allocation[tool] * query_factor)
        
        # 确保不超总预算
        total = sum(allocation.values())
        if total > budget:
            scale = budget / total
            for tool in allocation:
                allocation[tool] = int(allocation[tool] * scale)
        
        return allocation
```

### 3.3 结果精简器

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
                result["description"] = result["description"][:100]
            
            compressed.append(result)
        
        return compressed
```

### 3.4 上下文跟踪器

```python
class ContextTracker:
    """上下文跟踪器"""
    
    def __init__(self):
        self.existing_content: List[str] = []
        self.token_usage: int = 0
        self.tool_results: Dict[str, List] = {}
    
    def add_existing(self, content: str):
        """添加已有内容"""
        self.existing_content.append(content)
        self.token_usage += self.count_tokens(content)
    
    def add_tool_result(self, tool: str, result: List):
        """添加工具结果"""
        if tool not in self.tool_results:
            self.tool_results[tool] = []
        self.tool_results[tool].extend(result)
        self.token_usage += self.count_tokens(result)
    
    def get_existing_for_tool(self, tool: str) -> List[str]:
        """获取工具的已有内容"""
        # 避免重复获取
        return [c for c in self.existing_content if not self.is_duplicated(c, tool)]
    
    def is_duplicated(self, content: str, tool: str) -> bool:
        """检查内容是否已存在"""
        for existing in self.existing_content:
            if self.similarity(content, existing) > 0.8:
                return True
        return False
    
    def count_tokens(self, content) -> int:
        """计算 token 数"""
        # 简化实现，实际应使用 tiktoken
        if isinstance(content, str):
            return len(content) // 4
        elif isinstance(content, list):
            return sum(self.count_tokens(c) for c in content)
        return 0
```

---

## 4. 数据流

### 4.1 请求流

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         请求流                                                   │
│                                                                                   │
│  1. AI Agent 提交任务                                                            │
│     "用户要求增加 JWT 认证"                                                       │
│                                         │                                         │
│                                         ▼                                         │
│  2. Context Optimizer 需求分析                                                    │
│     ├─ 意图: 编写                                                                 │
│     ├─ 实体: JWT, 认证, Spring Security                                          │
│     ├─ 工具: knowledge, code-index, asset                                        │
│     └─ 预算: knowledge 2000, code-index 3000, asset 1000                        │
│                                         │                                         │
│                                         ▼                                         │
│  3. 按需获取                                                                      │
│     ├─ Knowledge Tool: "JWT认证流程" → 摘要 800tok                              │
│     ├─ Code Index: "AuthController" → 摘要 1200tok                              │
│     └─ Asset Tool: "JWT代码模板" → 摘要 400tok                                  │
│                                         │                                         │
│                                         ▼                                         │
│  4. 结果精简                                                                      │
│     ├─ 去重: 合并重复内容                                                         │
│     ├─ 过滤: 删除低相关度内容                                                    │
│     └─ 压缩: 精简格式                                                             │
│                                         │                                         │
│                                         ▼                                         │
│  5. 返回给 Agent                                                                  │
│     总计: 2400tok (在 Agent 限制内)                                              │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 工具层优化

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         工具层优化                                               │
│                                                                                   │
│  Knowledge Tool                                                                  │
│     │                                                                            │
│     │  1. 语义预过滤                                                             │
│     ├──────────────────────────────────────────────────────────────►            │
│     │  向量相似度 > 0.7 才保留                                                   │
│     │                                                                             │
│     │  2. 分层返回                                                               │
│     ├──────────────────────────────────────────────────────────────►            │
│     │  先返回摘要，详情按需                                                       │
│     │                                                                             │
│     │  3. 缓存                                                                   │
│     ├──────────────────────────────────────────────────────────────►            │
│     │  相同查询直接返回                                                           │
│     │                                                                             │
│     │  4. 格式优化                                                               │
│     ├──────────────────────────────────────────────────────────────►            │
│     │  精简代码块、列表                                                          │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. API 设计

### 5.1 核心 API

```
# 需求分析
POST /api/analyze
{
    "task": "用户要求增加 JWT 认证",
    "context": {
        "existing_content": ["已了解JWT基本概念"],
        "token_budget": 8000
    }
}

Response:
{
    "intent": "编写",
    "key_entities": ["JWT", "认证", "Spring Security"],
    "required_tools": ["knowledge", "code-index", "asset"],
    "search_queries": {
        "knowledge": ["JWT认证流程", "Spring Security配置"],
        "code-index": ["AuthController", "SecurityConfig"],
        "asset": ["JWT代码模板"]
    },
    "budget": {
        "knowledge": 2000,
        "code-index": 3000,
        "asset": 1000
    },
    "existing": ["已了解JWT基本概念"]
}

# 预算分配
POST /api/budget
{
    "plan": {...},
    "total_budget": 8000
}

Response:
{
    "knowledge": 2000,
    "code-index": 3000,
    "asset": 1000,
    "remaining": 2000
}

# 结果精简
POST /api/refine
{
    "results": {
        "knowledge": [...],
        "code-index": [...],
        "asset": [...]
    },
    "budget": 8000
}

Response:
{
    "refined": {
        "knowledge": [...],
        "code-index": [...],
        "asset": [...]
    },
    "total_tokens": 2400
}

# 上下文跟踪
POST /api/track
{
    "action": "add_existing",
    "content": "已了解JWT基本概念"
}

Response:
{
    "token_usage": 200,
    "existing_count": 1
}
```

### 5.2 内部 API

```
# 工具调用
POST /api/tools/{tool_name}/invoke
{
    "params": {...},
    "budget": 2000,
    "existing": [...]
}

Response:
{
    "results": [...],
    "tokens_used": 800
}
```

---

## 6. 与现有工具集成

### 6.1 集成架构

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         集成架构                                                 │
│                                                                                   │
│  AI Agent                                                                        │
│     │                                                                            │
│     │  1. 提交任务                                                               │
│     ▼                                                                            │
│  Context Optimizer                                                               │
│     │                                                                            │
│     │  2. 需求分析                                                               │
│     ├──────────────────────────────────────────────────────────────►            │
│     │                                                                             │
│     │  3. 返回检索计划                                                           │
│     │◄──────────────────────────────────────────────────────────────            │
│     │                                                                             │
│     │  4. 按需获取                                                               │
│     ├──────────────────────────────────────────────────────────────►            │
│     │                                                                             │
│     │  5. 返回精简结果                                                           │
│     │◄──────────────────────────────────────────────────────────────            │
│     │                                                                             │
│     │  6. 返回给 Agent                                                          │
│     ▼                                                                            │
│  AI Agent                                                                        │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 集成方式

**方式 1: 作为中间层**
```python
# AI Agent 调用 Context Optimizer
@app.post("/api/chat")
async def chat(task: str):
    # 1. 需求分析
    plan = await context_optimizer.analyze(task)
    
    # 2. 按需获取
    results = {}
    for tool in plan.tools:
        budget = plan.budget[tool]
        results[tool] = await invoke_tool(tool, plan.queries[tool], budget)
    
    # 3. 结果精简
    refined = await context_optimizer.refine(results)
    
    # 4. 返回给 Agent
    return refined
```

**方式 2: 作为工具层装饰器**
```python
# 工具层自动优化
@app.post("/api/tools/{tool_name}/invoke")
async def invoke_tool(tool_name: str, params: dict, budget: int):
    # 1. 语义预过滤
    pre_filtered = await semantic_pre_filter(params)
    
    # 2. 执行查询
    raw_results = await tool.invoke(pre_filtered)
    
    # 3. 分层返回
    summarized = await summarize_results(raw_results, budget)
    
    # 4. 格式优化
    optimized = await format_optimize(summarized, budget)
    
    return optimized
```

---

## 7. 实施计划

### 7.1 Phase 1: 基础框架（P0）

**周期**: 1 周（5 天）

**任务**:
- 项目结构搭建
- 需求分析器（规则部分）
- 预算分配器
- 基础 API

**验收标准**:
- [ ] 能分析任务意图
- [ ] 能提取关键实体
- [ ] 能分配 token 预算

### 7.2 Phase 2: LLM 集成（P1）

**周期**: 1 周（5 天）

**任务**:
- 小模型集成
- LLM 需求分析
- 结果精简器
- 上下文跟踪器

**验收标准**:
- [ ] LLM 能准确分析需求
- [ ] 结果精简有效
- [ ] 能跟踪已有信息

### 7.3 Phase 3: 工具层优化（P2）

**周期**: 1 周（5 天）

**任务**:
- 语义预过滤
- 分层返回
- 缓存系统
- 格式优化

**验收标准**:
- [ ] 语义预过滤有效
- [ ] 分层返回减少 token
- [ ] 缓存命中率 > 50%

### 7.4 Phase 4: 高级能力（P3）

**周期**: 1 周（5 天）

**任务**:
- 反馈学习
- 自适应预算
- 多轮优化
- 性能优化

**验收标准**:
- [ ] 能从反馈中学习
- [ ] 能自适应调整预算
- [ ] 性能优化有效

---

## 附录

### A. 配置项

```python
# app/config.py

class ContextOptimizerConfig:
    # LLM 配置
    LLM_BASE_URL: str = "http://192.168.0.100:11434/v1"
    LLM_API_KEY: str = "sk-xxx"
    LLM_MODEL: str = "qwen2.5:7b"  # 小模型
    
    # 预算配置
    DEFAULT_BUDGET: int = 8000
    MIN_BUDGET: int = 1000
    MAX_BUDGET: int = 32000
    
    # 工具优先级
    TOOL_PRIORITY: dict = {
        "code-index": 1.5,
        "knowledge": 1.2,
        "memory": 1.0,
        "asset": 0.8,
        "quality": 0.5,
        "sandbox": 0.3
    }
    
    # 精简配置
    SIMILARITY_THRESHOLD: float = 0.7
    MAX_RESULTS_PER_TOOL: int = 10
    SUMMARY_RATIO: float = 0.3  # 摘要比例
    
    # 缓存配置
    CACHE_ENABLED: bool = True
    CACHE_TTL: int = 3600  # 1 小时
    CACHE_MAX_SIZE: int = 1000
```

### B. 性能指标

| 指标 | 目标 | 说明 |
|------|------|------|
| **需求分析延迟** | < 500ms | 规则分析 |
| **LLM 分析延迟** | < 2s | 小模型调用 |
| **结果精简延迟** | < 1s | LLM 摘要 |
| **总延迟** | < 3s | 端到端 |
| **Token 节省率** | > 50% | 相比无优化 |
| **缓存命中率** | > 50% | 相同查询 |
