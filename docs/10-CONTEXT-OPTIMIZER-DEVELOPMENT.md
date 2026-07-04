# Context Optimizer 开发计划

---

## 目录

1. [项目概述](#1-项目概述)
2. [技术选型](#2-技术选型)
3. [Phase 1: 基础框架](#3-phase-1-基础框架)
4. [Phase 2: LLM 集成](#4-phase-2-llm-集成)
5. [Phase 3: 工具层优化](#5-phase-3-工具层优化)
6. [Phase 4: 高级能力](#6-phase-4-高级能力)
7. [风险评估](#7-风险评估)
8. [资源需求](#8-资源需求)

---

## 1. 项目概述

### 1.1 项目范围

为 AIDP 系统构建 Context Optimizer，提供上下文优化能力。

### 1.2 项目目标

- 分析任务需求，确定需要什么信息
- 分配 token 预算，控制各工具返回量
- 精简工具输出，只保留关键信息
- 避免重复获取，跟踪已有信息

### 1.3 项目周期

- Phase 1: 1 周（基础框架）
- Phase 2: 1 周（LLM 集成）
- Phase 3: 1 周（工具层优化）
- Phase 4: 1 周（高级能力）
- **总计: 4 周**

---

## 2. 技术选型

| 组件 | 技术 | 理由 |
|------|------|------|
| **语言** | Python 3.13 | 统一技术栈 |
| **Web 框架** | FastAPI | 异步、高性能 |
| **LLM** | OpenAI 兼容 API | 灵活性 |
| **缓存** | Redis | 高性能 |
| **向量存储** | LanceDB | 嵌入式 |

---

## 3. Phase 1: 基础框架（P0）

**周期**: 1 周（5 天）

### 3.1 目标

能分析任务需求并分配 token 预算。

### 3.2 任务清单

| 任务 | 估时 | 依赖 |
|------|------|------|
| 项目结构搭建 | 0.5 天 | 无 |
| 需求分析器（规则部分） | 1.5 天 | 无 |
| 预算分配器 | 1 天 | 需求分析器 |
| 基础 API | 1 天 | 预算分配器 |
| 单元测试 | 1 天 | 全部 |

### 3.3 技术实现

**需求分析器**:
```python
# app/services/requirement_analyzer.py
class RequirementAnalyzer:
    """需求分析器 - 规则部分"""
    
    # 意图关键词
    INTENT_KEYWORDS = {
        "understand": ["怎么", "是什么", "为什么", "如何", "how", "what", "why"],
        "write": ["增加", "实现", "创建", "添加", "add", "implement", "create"],
        "debug": ["报错", "异常", "失败", "error", "exception", "fail"],
        "optimize": ["性能", "优化", "重构", "performance", "optimize", "refactor"]
    }
    
    # 工具映射
    TOOL_MAPPING = {
        "understand": ["knowledge", "code-index", "memory"],
        "write": ["asset", "knowledge", "code-index"],
        "debug": ["code-index", "knowledge", "memory"],
        "optimize": ["code-index", "quality", "memory"]
    }
    
    def rule_analysis(self, task: str) -> RuleResult:
        """规则预分析"""
        
        # 意图识别
        intent = self.detect_intent(task)
        
        # 实体提取
        entities = self.extract_entities(task)
        
        # 工具推荐
        tools = self.recommend_tools(intent, entities)
        
        return RuleResult(
            intent=intent,
            entities=entities,
            tools=tools
        )
    
    def detect_intent(self, task: str) -> str:
        """意图识别"""
        for intent, keywords in self.INTENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in task:
                    return intent
        return "understand"  # 默认
    
    def extract_entities(self, task: str) -> List[str]:
        """实体提取"""
        entities = []
        
        # 类名（大驼峰）
        import re
        class_names = re.findall(r'\b[A-Z][a-zA-Z]+(?:Controller|Service|Repository|Config)\b', task)
        entities.extend(class_names)
        
        # 函数名
        func_names = re.findall(r'\b[a-z][a-zA-Z]+(?:\(\))\b', task)
        entities.extend(func_names)
        
        # 概念
        concepts = ["JWT", "OAuth", "Spring Security", "FastAPI", "Django"]
        for concept in concepts:
            if concept.lower() in task.lower():
                entities.append(concept)
        
        return entities
    
    def recommend_tools(self, intent: str, entities: List[str]) -> List[str]:
        """工具推荐"""
        tools = self.TOOL_MAPPING.get(intent, ["knowledge"])
        
        # 根据实体调整
        for entity in entities:
            if "Controller" in entity or "Service" in entity:
                if "code-index" not in tools:
                    tools.append("code-index")
            if entity in ["JWT", "OAuth", "Spring Security"]:
                if "knowledge" not in tools:
                    tools.append("knowledge")
        
        return tools
```

**预算分配器**:
```python
# app/services/budget_allocator.py
class BudgetAllocator:
    """预算分配器"""
    
    DEFAULT_BUDGET = 8000
    
    TOOL_PRIORITY = {
        "code-index": 1.5,
        "knowledge": 1.2,
        "memory": 1.0,
        "asset": 0.8,
        "quality": 0.5,
        "sandbox": 0.3
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
                query_factor = len(queries) / 2
                allocation[tool] = int(allocation[tool] * query_factor)
        
        # 确保不超总预算
        total = sum(allocation.values())
        if total > budget:
            scale = budget / total
            for tool in allocation:
                allocation[tool] = int(allocation[tool] * scale)
        
        return allocation
```

### 3.4 验收标准

- [ ] 能分析任务意图
- [ ] 能提取关键实体
- [ ] 能分配 token 预算
- [ ] 能返回检索计划

---

## 4. Phase 2: LLM 集成（P1）

**周期**: 1 周（5 天）

### 4.1 目标

LLM 能准确分析需求，结果精简有效。

### 4.2 任务清单

| 任务 | 估时 | 依赖 |
|------|------|------|
| 小模型集成 | 1 天 | Phase 1 |
| LLM 需求分析 | 1.5 天 | 小模型集成 |
| 结果精简器 | 1.5 天 | Phase 1 |
| 上下文跟踪器 | 1 天 | 结果精简器 |

### 4.3 技术实现

**LLM 需求分析**:
```python
# app/services/llm_analyzer.py
class LLMAnalyzer:
    """LLM 需求分析器"""
    
    async def analyze(self, task: str, context: AgentContext) -> LLMResult:
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
        
        result = await self.llm.call(prompt)
        return LLMResult.parse(result)
```

**结果精简器**:
```python
# app/services/result_refiner.py
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
```

**上下文跟踪器**:
```python
# app/services/context_tracker.py
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
    
    def is_duplicated(self, content: str) -> bool:
        """检查内容是否已存在"""
        for existing in self.existing_content:
            if self.similarity(content, existing) > 0.8:
                return True
        return False
```

### 4.4 验收标准

- [ ] LLM 能准确分析需求
- [ ] 结果精简有效
- [ ] 能跟踪已有信息
- [ ] 能避免重复获取

---

## 5. Phase 3: 工具层优化（P2）

**周期**: 1 周（5 天）

### 5.1 目标

工具层能有效优化输出。

### 5.2 任务清单

| 任务 | 估时 | 依赖 |
|------|------|------|
| 语义预过滤 | 1.5 天 | Phase 2 |
| 分层返回 | 1 天 | 语义预过滤 |
| 缓存系统 | 1.5 天 | Phase 2 |
| 格式优化 | 1 天 | 缓存系统 |

### 5.3 技术实现

**语义预过滤**:
```python
# app/services/semantic_filter.py
class SemanticFilter:
    """语义预过滤器"""
    
    async def filter(self, query: str, candidates: List, threshold: float = 0.7) -> List:
        """语义过滤"""
        
        # 计算查询向量
        query_embedding = await self.embed(query)
        
        # 计算相似度
        filtered = []
        for candidate in candidates:
            candidate_embedding = await self.embed(candidate.content)
            similarity = self.cosine_similarity(query_embedding, candidate_embedding)
            
            if similarity >= threshold:
                filtered.append(candidate)
        
        return filtered
```

**缓存系统**:
```python
# app/services/cache_service.py
class CacheService:
    """缓存服务"""
    
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        self.default_ttl = 3600  # 1 小时
    
    async def get(self, key: str):
        """获取缓存"""
        cached = await self.redis.get(key)
        if cached:
            return json.loads(cached)
        return None
    
    async def set(self, key: str, value: any, ttl: int = None):
        """设置缓存"""
        ttl = ttl or self.default_ttl
        await self.redis.setex(key, ttl, json.dumps(value))
    
    def generate_key(self, tool: str, params: dict) -> str:
        """生成缓存键"""
        params_str = json.dumps(params, sort_keys=True)
        return f"{tool}:{hashlib.md5(params_str.encode()).hexdigest()}"
```

### 5.4 验收标准

- [ ] 语义预过滤有效
- [ ] 分层返回减少 token
- [ ] 缓存命中率 > 50%
- [ ] 格式优化有效

---

## 6. Phase 4: 高级能力（P3）

**周期**: 1 周（5 天）

### 6.1 目标

能从反馈中学习，自适应调整预算。

### 6.2 任务清单

| 任务 | 估时 | 依赖 |
|------|------|------|
| 反馈学习 | 1.5 天 | Phase 3 |
| 自适应预算 | 1 天 | 反馈学习 |
| 多轮优化 | 1.5 天 | Phase 3 |
| 性能优化 | 1 天 | 全部 |

### 6.3 技术实现

**反馈学习**:
```python
# app/services/feedback_learner.py
class FeedbackLearner:
    """反馈学习器"""
    
    async def learn(self, feedback: Feedback):
        """从反馈中学习"""
        
        # 记录反馈
        await self.record_feedback(feedback)
        
        # 分析反馈模式
        patterns = await self.analyze_patterns()
        
        # 更新策略
        await self.update_strategy(patterns)
    
    async def analyze_patterns(self) -> List[Pattern]:
        """分析反馈模式"""
        
        # 获取所有反馈
        feedbacks = await self.get_all_feedbacks()
        
        # 分析模式
        patterns = []
        
        # 1. 工具使用模式
        tool_usage = self.analyze_tool_usage(feedbacks)
        patterns.extend(tool_usage)
        
        # 2. 预算分配模式
        budget_patterns = self.analyze_budget_patterns(feedbacks)
        patterns.extend(budget_patterns)
        
        # 3. 结果质量模式
        quality_patterns = self.analyze_quality_patterns(feedbacks)
        patterns.extend(quality_patterns)
        
        return patterns
```

**自适应预算**:
```python
# app/services/adaptive_budget.py
class AdaptiveBudget:
    """自适应预算"""
    
    async def adjust_budget(self, plan: RetrievalPlan, feedback: Feedback) -> Dict[str, int]:
        """根据反馈调整预算"""
        
        # 1. 分析反馈
        if feedback.quality == "high":
            # 质量高，保持当前策略
            return plan.budget
        elif feedback.quality == "low":
            # 质量低，调整策略
            return self.reallocate_budget(plan, feedback)
        else:
            # 中等质量，微调
            return self.fine_tune_budget(plan, feedback)
    
    def reallocate_budget(self, plan: RetrievalPlan, feedback: Feedback) -> Dict[str, int]:
        """重新分配预算"""
        
        new_budget = plan.budget.copy()
        
        # 根据反馈调整
        for tool, score in feedback.tool_scores.items():
            if score < 0.5:
                # 工具效果差，减少预算
                new_budget[tool] = int(new_budget[tool] * 0.8)
            elif score > 0.8:
                # 工具效果好，增加预算
                new_budget[tool] = int(new_budget[tool] * 1.2)
        
        return new_budget
```

### 6.4 验收标准

- [ ] 能从反馈中学习
- [ ] 能自适应调整预算
- [ ] 多轮优化有效
- [ ] 性能优化有效

---

## 7. 风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| **LLM 分析不准确** | 中 | 高 | 使用规则分析 fallback |
| **缓存失效** | 中 | 中 | 重新计算 + 缓存预热 |
| **性能瓶颈** | 低 | 中 | 异步处理 + 缓存 |

---

## 8. 资源需求

### 8.1 开发资源

| 资源 | 数量 | 说明 |
|------|------|------|
| **开发人员** | 1 人 | Python + FastAPI |
| **开发环境** | 1 套 | 本地开发 |
| **测试环境** | 1 套 | NAS 部署 |

### 8.2 基础设施

| 资源 | 规格 | 说明 |
|------|------|------|
| **NAS** | 192.168.0.100 | 部署环境 |
| **Redis** | 192.168.0.100:6379 | 缓存 |
| **LLM** | OpenAI 兼容 | 需求分析 |

### 8.3 依赖关系

| 依赖 | 版本 | 说明 |
|------|------|------|
| **Python** | 3.13 | 运行环境 |
| **FastAPI** | latest | Web 框架 |
| **Redis** | latest | 缓存 |
| **LanceDB** | latest | 向量存储 |
