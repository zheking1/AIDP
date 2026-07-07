# Evolution Engine 设计文档

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

当前系统缺乏反馈闭环：
- AI 犯错后不知道为什么错
- 下次遇到同样问题还犯同样错误
- 用户纠正后系统不学习
- 成功经验不积累

### 1.2 解决方案

**Evolution Engine** 是 AIDP 系统的**进化中枢**，负责：
- 收集错误、成功、用户反馈事件
- 用小模型分析事件模式
- 将分析结果路由到对应工具
- 更新各工具的经验、规则、文档、模板

### 1.3 设计原则

| 原则 | 描述 |
|------|------|
| **事件驱动** | 被动接收事件，不主动轮询 |
| **小模型分析** | 低成本、低延迟 |
| **精准路由** | 只更新必要的工具 |
| **增量进化** | 每次更新量小，持续改进 |

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         Evolution Engine                                         │
│                         端口: 18089                                              │
│                                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                    Event Collector                                          │ │
│  │                    事件收集                                                  │ │
│  │                                                                             │ │
│  │  输入:                                                                      │ │
│  │  - Quality Tool 发现的错误                                                  │ │
│  │  - Sandbox Tool 执行失败                                                    │ │
│  │  - 用户反馈的问题                                                           │ │
│  │  - Memory Tool 记录的经验                                                   │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                         │                                         │
│                                         ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                    Pattern Analyzer                                         │ │
│  │                    模式分析                                                  │ │
│  │                                                                             │ │
│  │  小模型分析:                                                                 │ │
│  │  - 错误类型: 逻辑错误/性能问题/风格不匹配/...                              │ │
│  │  - 根因分析: 为什么出错                                                     │ │
│  │  - 修复模式: 怎么修                                                         │ │
│  │  - 成功模式: 为什么成功                                                     │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                         │                                         │
│                                         ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                    Evolution Router                                        │ │
│  │                    进化路由                                                  │ │
│  │                                                                             │ │
│  │  错误 → Memory (记录错误经验)                                               │ │
│  │  规则错误 → Skill Router (更新路由规则)                                     │ │
│  │  文档过时 → Knowledge (更新文档)                                            │ │
│  │  成功模式 → Asset (更新模板)                                                │ │
│  │  代码模式 → Code Index (更新代码模式)                                       │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                         │                                         │
│                    ┌────────────────────┼────────────────────┐                   │
│                    ▼                    ▼                    ▼                   │
│              ┌──────────┐        ┌──────────┐        ┌──────────┐              │
│              │  Memory  │        │  Router  │        │ Knowledge│              │
│              │  更新    │        │  更新    │        │  更新    │              │
│              └──────────┘        └──────────┘        └──────────┘              │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 组件交互

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         组件交互图                                               │
│                                                                                   │
│  Quality Tool ──► Event Collector ──► Pattern Analyzer ──► Evolution Router      │
│       │                                      │                    │              │
│       │ 错误事件                              │ 分析结果           │ 路由决策     │
│       │                                      │                    │              │
│  Sandbox Tool ──► Event Collector ──► Pattern Analyzer ──► Evolution Router      │
│       │                                      │                    │              │
│       │ 执行失败                              │ 分析结果           │ 路由决策     │
│       │                                      │                    │              │
│  User Feedback ──► Event Collector ──► Pattern Analyzer ──► Evolution Router     │
│                                              │                    │              │
│                                              │ 分析结果           │ 路由决策     │
│                                              │                    │              │
│                                    ┌─────────┴─────────┐                      │
│                                    ▼                   ▼                      │
│                              ┌──────────┐        ┌──────────┐                 │
│                              │  Memory  │        │  Router  │                 │
│                              │  更新    │        │  更新    │                 │
│                              └──────────┘        └──────────┘                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 核心组件

### 3.1 事件收集器

```python
# app/services/event_collector.py

class EventCollector:
    """事件收集器"""
    
    async def collect_from_quality(self, result: QualityResult, code: str):
        """从 Quality Tool 收集"""
        
        if result.has_errors():
            await self.collect(EvolutionEvent(
                type="error",
                source="quality",
                content=code,
                result=result.errors,
                metadata={"fix_suggestions": result.suggestions}
            ))
    
    async def collect_from_sandbox(self, result: ExecutionResult, code: str):
        """从 Sandbox Tool 收集"""
        
        if result.exit_code != 0:
            await self.collect(EvolutionEvent(
                type="error",
                source="sandbox",
                content=code,
                result=result.stderr,
                metadata={"language": result.language}
            ))
    
    async def collect_from_user(self, feedback: UserFeedback):
        """从用户收集"""
        
        await self.collect(EvolutionEvent(
            type=feedback.type,  # error/success/suggestion
            source="user",
            content=feedback.content,
            result=feedback.result,
            metadata={"user_id": feedback.user_id}
        ))
    
    async def collect_from_memory(self, experience: Experience):
        """从 Memory Tool 收集"""
        
        if experience.type == "error_pattern":
            await self.collect(EvolutionEvent(
                type="error",
                source="memory",
                content=experience.code,
                result=experience.error,
                metadata={"fix": experience.fix}
            ))
    
    async def collect(self, event: EvolutionEvent):
        """收集事件"""
        
        # 存储事件
        await self.store_event(event)
        
        # 触发分析
        await self.trigger_analysis(event)
```

### 3.2 模式分析器

```python
# app/services/pattern_analyzer.py

class PatternAnalyzer:
    """模式分析器 - 小模型分析"""
    
    async def analyze(self, event: EvolutionEvent) -> Analysis:
        """分析事件"""
        
        prompt = f"""
        分析以下编程事件，提取进化信息：
        
        事件类型: {event.type}
        事件来源: {event.source}
        事件内容: {event.content}
        结果: {event.result}
        元数据: {event.metadata}
        
        请返回 JSON:
        {{
            "category": "错误/成功/优化",
            "error_type": "逻辑错误/性能问题/风格不匹配/类型错误/导入错误/...",
            "root_cause": "根本原因分析",
            "fix_pattern": "修复模式（如果失败）",
            "success_pattern": "成功模式（如果成功）",
            "affected_tools": ["tool1", "tool2"],
            "update_type": "经验/规则/文档/模板/模式",
            "priority": "high/medium/low",
            "confidence": 0.85
        }}
        """
        
        result = await self.small_model.call(prompt)
        return Analysis.parse(result)
    
    async def batch_analyze(self, events: List[EvolutionEvent]) -> List[Analysis]:
        """批量分析"""
        
        analyses = []
        for event in events:
            analysis = await self.analyze(event)
            analyses.append(analysis)
        
        return analyses
```

### 3.3 进化路由器

```python
# app/services/evolution_router.py

class EvolutionRouter:
    """进化路由器"""
    
    def route(self, analysis: Analysis) -> List[str]:
        """路由到目标工具"""
        
        targets = []
        
        # 根据分析结果决定更新目标
        if analysis.category == "错误":
            targets.append("memory")  # 记录错误经验
            
            if analysis.error_type == "规则错误":
                targets.append("skill_router")  # 更新路由规则
            elif analysis.error_type == "文档过时":
                targets.append("knowledge")  # 更新文档
            elif analysis.error_type == "风格不匹配":
                targets.append("asset")  # 更新模板
        
        elif analysis.category == "成功":
            targets.append("memory")  # 记录成功经验
            targets.append("asset")  # 更新模板
        
        elif analysis.category == "优化":
            targets.append("knowledge")  # 更新文档
            targets.append("code_index")  # 更新代码模式
        
        return targets
```

### 3.4 工具更新器

```python
# app/services/tool_updater.py

class ToolUpdater:
    """工具更新器"""
    
    async def update_memory(self, analysis: Analysis):
        """更新 Memory Tool"""
        
        if analysis.category == "错误":
            await memory.store({
                "type": "error_pattern",
                "error_type": analysis.error_type,
                "root_cause": analysis.root_cause,
                "fix_pattern": analysis.fix_pattern,
                "priority": analysis.priority
            })
        
        elif analysis.category == "成功":
            await memory.store({
                "type": "success_pattern",
                "success_pattern": analysis.success_pattern,
                "priority": analysis.priority
            })
    
    async def update_skill_router(self, analysis: Analysis):
        """更新 Skill Router"""
        
        # 更新路由规则
        await skill_router.update_rules({
            "error_type": analysis.error_type,
            "affected_tools": analysis.affected_tools,
            "priority": analysis.priority
        })
    
    async def update_knowledge(self, analysis: Analysis):
        """更新 Knowledge Tool"""
        
        # 更新文档
        await knowledge.update_docs({
            "error_type": analysis.error_type,
            "root_cause": analysis.root_cause,
            "fix_pattern": analysis.fix_pattern
        })
    
    async def update_asset(self, analysis: Analysis):
        """更新 Asset Tool"""
        
        # 更新模板
        await asset.update_templates({
            "success_pattern": analysis.success_pattern,
            "priority": analysis.priority
        })
    
    async def update_code_index(self, analysis: Analysis):
        """更新 Code Index"""
        
        # 更新代码模式
        await code_index.update_patterns({
            "success_pattern": analysis.success_pattern,
            "priority": analysis.priority
        })
```

---

## 4. 数据流

### 4.1 错误进化流

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         错误进化流                                               │
│                                                                                   │
│  1. AI Agent 编写代码                                                            │
│     │                                                                            │
│     ▼                                                                            │
│  2. Quality Tool 检查                                                            │
│     │                                                                            │
│     │ 发现错误: "未处理的 NullPointerException"                                  │
│     │                                                                            │
│     ▼                                                                            │
│  3. Event Collector 收集                                                         │
│     │                                                                            │
│     │ 事件: {type: "error", source: "quality", ...}                             │
│     │                                                                            │
│     ▼                                                                            │
│  4. Pattern Analyzer 分析                                                        │
│     │                                                                            │
│     │ 分析: {                                                                   │
│     │   error_type: "空指针异常",                                               │
│     │   root_cause: "未检查 null 值",                                           │
│     │   fix_pattern: "使用 Optional 或 null 检查",                              │
│     │   update_type: "经验"                                                     │
│     │ }                                                                         │
│     │                                                                            │
│     ▼                                                                            │
│  5. Evolution Router 路由                                                        │
│     │                                                                            │
│     │ 路由: → Memory Tool                                                       │
│     │                                                                            │
│     ▼                                                                            │
│  6. Tool Updater 更新                                                            │
│     │                                                                            │
│     │ 更新: Memory Tool 存储错误经验                                            │
│     │                                                                            │
│     ▼                                                                            │
│  7. 下次遇到类似问题                                                             │
│     │                                                                            │
│     │ Memory Tool 返回: "上次遇到空指针异常，使用 Optional 修复"                │
│     │                                                                            │
│     ▼                                                                            │
│  8. AI Agent 避免同样错误                                                        │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 成功进化流

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         成功进化流                                               │
│                                                                                   │
│  1. AI Agent 编写代码                                                            │
│     │                                                                            │
│     ▼                                                                            │
│  2. Quality Tool 检查                                                            │
│     │                                                                            │
│     │ 通过: "代码质量优秀"                                                      │
│     │                                                                            │
│     ▼                                                                            │
│  3. Event Collector 收集                                                         │
│     │                                                                            │
│     │ 事件: {type: "success", source: "quality", ...}                          │
│     │                                                                            │
│     ▼                                                                            │
│  4. Pattern Analyzer 分析                                                        │
│     │                                                                            │
│     │ 分析: {                                                                   │
│     │   success_pattern: "使用 Optional 链式调用避免空指针",                    │
│     │   update_type: "模板"                                                     │
│     │ }                                                                         │
│     │                                                                            │
│     ▼                                                                            │
│  5. Evolution Router 路由                                                        │
│     │                                                                            │
│     │ 路由: → Memory Tool + Asset Tool                                          │
│     │                                                                            │
│     ▼                                                                            │
│  6. Tool Updater 更新                                                            │
│     │                                                                            │
│     │ 更新: Memory Tool 存储成功模式                                           │
│     │       Asset Tool 更新代码模板                                             │
│     │                                                                            │
│     ▼                                                                            │
│  7. 下次遇到类似场景                                                             │
│     │                                                                            │
│     │ Asset Tool 返回: "推荐使用 Optional 链式调用"                             │
│     │                                                                            │
│     ▼                                                                            │
│  8. AI Agent 生成更高质量代码                                                    │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. API 设计

### 5.1 事件收集 API

```
# 收集事件
POST /api/events
{
    "type": "error",
    "source": "quality",
    "content": "代码内容",
    "result": "错误信息",
    "metadata": {
        "fix_suggestions": ["建议1", "建议2"]
    }
}

Response:
{
    "success": true,
    "event_id": 123
}

# 批量收集
POST /api/events/batch
{
    "events": [...]
}

Response:
{
    "success": true,
    "collected": 5
}
```

### 5.2 分析 API

```
# 分析单个事件
POST /api/analyze
{
    "event_id": 123
}

Response:
{
    "analysis": {
        "category": "错误",
        "error_type": "空指针异常",
        "root_cause": "未检查 null 值",
        "fix_pattern": "使用 Optional 或 null 检查",
        "affected_tools": ["memory"],
        "update_type": "经验",
        "priority": "high",
        "confidence": 0.85
    }
}

# 批量分析
POST /api/analyze/batch
{
    "event_ids": [123, 124, 125]
}

Response:
{
    "analyses": [...]
}
```

### 5.3 进化 API

```
# 执行进化
POST /api/evolve
{
    "event_id": 123
}

Response:
{
    "success": true,
    "targets": ["memory"],
    "updates": [
        {
            "tool": "memory",
            "type": "error_pattern",
            "status": "success"
        }
    ]
}

# 批量进化
POST /api/evolve/batch
{
    "event_ids": [123, 124, 125]
}

Response:
{
    "success": true,
    "total_updates": 15
}

# 查看进化历史
GET /api/evolution/history
{
    "limit": 50
}

Response:
{
    "history": [
        {
            "id": 1,
            "event_type": "error",
            "analysis": {...},
            "targets": ["memory"],
            "created_at": "2024-01-01T00:00:00Z"
        }
    ]
}
```

### 5.4 统计 API

```
# 进化统计
GET /api/evolution/stats

Response:
{
    "total_events": 1000,
    "error_events": 300,
    "success_events": 600,
    "optimization_events": 100,
    "total_updates": 800,
    "by_tool": {
        "memory": 400,
        "skill_router": 200,
        "knowledge": 100,
        "asset": 100
    },
    "error_reduction_rate": 0.35
}
```

---

## 6. 与现有工具集成

### 6.1 集成架构

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         集成架构                                                 │
│                                                                                   │
│  Quality Tool ──► Evolution Engine ──► Memory Tool                              │
│       │                                      │                                   │
│       │ 错误事件                              │ 存储经验                          │
│       │                                      │                                   │
│  Sandbox Tool ──► Evolution Engine ──► Skill Router                            │
│       │                                      │                                   │
│       │ 执行失败                              │ 更新规则                          │
│       │                                      │                                   │
│  User Feedback ──► Evolution Engine ──► Knowledge Tool                         │
│       │                                      │                                   │
│       │ 用户纠正                              │ 更新文档                          │
│       │                                      │                                   │
│  Memory Tool ────► Evolution Engine ──► Asset Tool                             │
│                                              │                                   │
│                                              │ 更新模板                          │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 集成方式

**Quality Tool 集成**:
```python
# quality_tool 中的集成代码
class QualityToolIntegrator:
    """Quality Tool 集成 Evolution Engine"""
    
    async def on_quality_check(self, result: QualityResult, code: str):
        """质量检查后触发进化"""
        
        if result.has_errors() or result.passed():
            await self.evolution_engine.collect_from_quality(result, code)
```

**Sandbox Tool 集成**:
```python
# sandbox_tool 中的集成代码
class SandboxToolIntegrator:
    """Sandbox Tool 集成 Evolution Engine"""
    
    async def on_execution(self, result: ExecutionResult, code: str):
        """执行后触发进化"""
        
        await self.evolution_engine.collect_from_sandbox(result, code)
```

**用户反馈集成**:
```python
# 用户反馈 API
@app.post("/api/feedback")
async def submit_feedback(feedback: UserFeedback):
    """提交用户反馈"""
    
    await evolution_engine.collect_from_user(feedback)
    
    return {"success": true}
```

---

## 7. 实施计划

### 7.1 Phase 1: 基础框架（P0）

**周期**: 1 周（5 天）

**任务**:
- 项目结构搭建
- 事件收集器
- 模式分析器（规则部分）
- 基础 API

**验收标准**:
- [ ] 能收集事件
- [ ] 能分析事件（规则）
- [ ] 能路由到目标工具

### 7.2 Phase 2: LLM 集成（P1）

**周期**: 1 周（5 天）

**任务**:
- 小模型集成
- LLM 模式分析
- 工具更新器
- 历史记录

**验收标准**:
- [ ] LLM 能准确分析模式
- [ ] 能更新目标工具
- [ ] 能记录进化历史

### 7.3 Phase 3: 高级能力（P2）

**周期**: 1 周（5 扩展能力

**周期**: 1 周（5 天）

**任务**:
- 批量处理
- 统计分析
- 性能优化
- 与现有工具深度集成

**验收标准**:
- [ ] 批量处理有效
- [ ] 统计分析准确
- [ ] 性能优化有效
- [ ] 与现有工具集成完整

---

## 附录

### A. 配置项

```python
# app/config.py

class EvolutionEngineConfig:
    # LLM 配置
    LLM_BASE_URL: str = "http://192.168.0.100:11434/v1"
    LLM_API_KEY: str = "sk-xxx"
    LLM_MODEL: str = "qwen2.5:7b"  # 小模型
    
    # 分析配置
    BATCH_SIZE: int = 10
    ANALYSIS_TIMEOUT: int = 30
    
    # 路由配置
    ROUTE_RULES: dict = {
        "error": ["memory"],
        "success": ["memory", "asset"],
        "optimization": ["knowledge", "code_index"]
    }
    
    # 更新配置
    UPDATE_RETRY: int = 3
    UPDATE_TIMEOUT: int = 10
```

### B. 数据模型

```sql
-- 事件表
CREATE TABLE evolution_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    source TEXT NOT NULL,
    content TEXT,
    result TEXT,
    metadata TEXT DEFAULT '{}',
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 分析表
CREATE TABLE evolution_analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER REFERENCES evolution_events(id),
    category TEXT,
    error_type TEXT,
    root_cause TEXT,
    fix_pattern TEXT,
    success_pattern TEXT,
    affected_tools TEXT,
    update_type TEXT,
    priority TEXT,
    confidence FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 更新表
CREATE TABLE evolution_updates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER REFERENCES evolution_analyses(id),
    target_tool TEXT NOT NULL,
    update_type TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
