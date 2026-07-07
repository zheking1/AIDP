# Evolution Engine 开发计划

---

## 目录

1. [项目概述](#1-项目概述)
2. [技术选型](#2-技术选型)
3. [Phase 1: 基础框架](#3-phase-1-基础框架)
4. [Phase 2: LLM 集成](#4-phase-2-llm-集成)
5. [Phase 3: 高级能力](#5-phase-3-高级能力)
6. [风险评估](#6-风险评估)
7. [资源需求](#7-资源需求)

---

## 1. 项目概述

### 1.1 项目范围

为 AIDP 系统构建 Evolution Engine，提供系统进化能力。

### 1.2 项目目标

- 收集错误、成功、用户反馈事件
- 用小模型分析事件模式
- 将分析结果路由到对应工具
- 更新各工具的经验、规则、文档、模板

### 1.3 项目周期

- Phase 1: 1 周（基础框架）
- Phase 2: 1 周（LLM 集成）
- Phase 3: 1 周（高级能力）
- **总计: 3 周**

---

## 2. 技术选型

| 组件 | 技术 | 理由 |
|------|------|------|
| **语言** | Python 3.13 | 统一技术栈 |
| **Web 框架** | FastAPI | 异步、高性能 |
| **LLM** | OpenAI 兼容 API | 灵活性 |
| **存储** | SQLite | 零依赖 |

---

## 3. Phase 1: 基础框架（P0）

**周期**: 1 周（5 天）

### 3.1 目标

能收集事件、分析事件、路由到目标工具。

### 3.2 任务清单

| 任务 | 估时 | 依赖 |
|------|------|------|
| 项目结构搭建 | 0.5 天 | 无 |
| 事件收集器 | 1.5 天 | 无 |
| 模式分析器（规则部分） | 1.5 天 | 无 |
| 进化路由器 | 1 天 | 分析器 |
| 基础 API | 0.5 天 | 路由器 |

### 3.3 技术实现

**事件收集器**:
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
            type=feedback.type,
            source="user",
            content=feedback.content,
            result=feedback.result,
            metadata={"user_id": feedback.user_id}
        ))
    
    async def collect(self, event: EvolutionEvent):
        """收集事件"""
        
        # 存储事件
        await self.store_event(event)
        
        # 触发分析
        await self.trigger_analysis(event)
```

**模式分析器（规则部分）**:
```python
# app/services/pattern_analyzer.py

class PatternAnalyzer:
    """模式分析器 - 规则部分"""
    
    # 错误类型关键词
    ERROR_KEYWORDS = {
        "null_pointer": ["null", "None", "undefined", "NullPointerException"],
        "type_error": ["type", "Type", "TypeError", "类型"],
        "import_error": ["import", "Import", "ModuleNotFoundError"],
        "syntax_error": ["syntax", "Syntax", "SyntaxError"]
    }
    
    def rule_analysis(self, event: EvolutionEvent) -> Analysis:
        """规则分析"""
        
        # 识别错误类型
        error_type = self.identify_error_type(event.result)
        
        # 提取修复模式
        fix_pattern = self.extract_fix_pattern(event)
        
        # 路由到目标工具
        targets = self.route_targets(error_type)
        
        return Analysis(
            category="错误",
            error_type=error_type,
            fix_pattern=fix_pattern,
            affected_tools=targets,
            update_type="经验",
            priority="high"
        )
    
    def identify_error_type(self, error_message: str) -> str:
        """识别错误类型"""
        
        for error_type, keywords in self.ERROR_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in error_message.lower():
                    return error_type
        
        return "unknown"
```

**进化路由器**:
```python
# app/services/evolution_router.py

class EvolutionRouter:
    """进化路由器"""
    
    def route(self, analysis: Analysis) -> List[str]:
        """路由到目标工具"""
        
        targets = []
        
        if analysis.category == "错误":
            targets.append("memory")
            
            if analysis.error_type == "规则错误":
                targets.append("skill_router")
            elif analysis.error_type == "文档过时":
                targets.append("knowledge")
            elif analysis.error_type == "风格不匹配":
                targets.append("asset")
        
        elif analysis.category == "成功":
            targets.append("memory")
            targets.append("asset")
        
        elif analysis.category == "优化":
            targets.append("knowledge")
            targets.append("code_index")
        
        return targets
```

### 3.4 验收标准

- [ ] 能收集事件
- [ ] 能分析事件（规则）
- [ ] 能路由到目标工具
- [ ] 能更新 Memory Tool

---

## 4. Phase 2: LLM 集成（P1）

**周期**: 1 周（5 天）

### 4.1 目标

LLM 能准确分析模式，能更新所有目标工具。

### 4.2 任务清单

| 任务 | 估时 | 依赖 |
|------|------|------|
| 小模型集成 | 1 天 | Phase 1 |
| LLM 模式分析 | 1.5 天 | 小模型集成 |
| 工具更新器 | 1.5 天 | Phase 1 |
| 历史记录 | 1 天 | 更新器 |

### 4.3 技术实现

**LLM 模式分析**:
```python
# app/services/llm_analyzer.py

class LLMAnalyzer:
    """LLM 模式分析器"""
    
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
```

**工具更新器**:
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
        
        await skill_router.update_rules({
            "error_type": analysis.error_type,
            "affected_tools": analysis.affected_tools,
            "priority": analysis.priority
        })
    
    async def update_knowledge(self, analysis: Analysis):
        """更新 Knowledge Tool"""
        
        await knowledge.update_docs({
            "error_type": analysis.error_type,
            "root_cause": analysis.root_cause,
            "fix_pattern": analysis.fix_pattern
        })
    
    async def update_asset(self, analysis: Analysis):
        """更新 Asset Tool"""
        
        await asset.update_templates({
            "success_pattern": analysis.success_pattern,
            "priority": analysis.priority
        })
```

### 4.4 验收标准

- [ ] LLM 能准确分析模式
- [ ] 能更新所有目标工具
- [ ] 能记录进化历史
- [ ] 能查看进化统计

---

## 5. Phase 3: 高级能力（P2）

**周期**: 1 周（5 天）

### 5.1 目标

批量处理、统计分析、性能优化。

### 5.2 任务清单

| 任务 | 估时 | 依赖 |
|------|------|------|
| 批量处理 | 1.5 天 | Phase 2 |
| 统计分析 | 1.5 天 | Phase 2 |
| 性能优化 | 1 天 | Phase 2 |
| 与现有工具深度集成 | 1 天 | 全部 |

### 5.3 技术实现

**批量处理**:
```python
# app/services/batch_processor.py

class BatchProcessor:
    """批量处理器"""
    
    async def process_batch(self, events: List[EvolutionEvent]):
        """批量处理事件"""
        
        # 1. 批量分析
        analyses = await self.analyzer.batch_analyze(events)
        
        # 2. 批量路由
        routes = []
        for analysis in analyses:
            targets = self.router.route(analysis)
            routes.append((analysis, targets))
        
        # 3. 批量更新
        for analysis, targets in routes:
            for target in targets:
                await self.updater.update(target, analysis)
        
        return len(analyses)
```

**统计分析**:
```python
# app/services/stats_analyzer.py

class StatsAnalyzer:
    """统计分析器"""
    
    async def get_stats(self) -> EvolutionStats:
        """获取进化统计"""
        
        total_events = await self.count_events()
        error_events = await self.count_events_by_type("error")
        success_events = await self.count_events_by_type("success")
        
        updates_by_tool = await self.count_updates_by_tool()
        
        error_reduction = await self.calculate_error_reduction()
        
        return EvolutionStats(
            total_events=total_events,
            error_events=error_events,
            success_events=success_events,
            updates_by_tool=updates_by_tool,
            error_reduction_rate=error_reduction
        )
```

### 5.4 验收标准

- [ ] 批量处理有效
- [ ] 统计分析准确
- [ ] 性能优化有效
- [ ] 与现有工具集成完整

---

## 6. 风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| **LLM 分析不准确** | 中 | 中 | 使用规则分析 fallback |
| **更新失败** | 中 | 中 | 重试 + 事务保证 |
| **性能瓶颈** | 低 | 中 | 异步处理 + 缓存 |

---

## 7. 资源需求

### 7.1 开发资源

| 资源 | 数量 | 说明 |
|------|------|------|
| **开发人员** | 1 人 | Python + FastAPI |
| **开发环境** | 1 套 | 本地开发 |
| **测试环境** | 1 套 | NAS 部署 |

### 7.2 基础设施

| 资源 | 规格 | 说明 |
|------|------|------|
| **NAS** | 192.168.0.100 | 部署环境 |
| **LLM** | OpenAI 兼容 | 模式分析 |

### 7.3 依赖关系

| 依赖 | 版本 | 说明 |
|------|------|------|
| **Python** | 3.13 | 运行环境 |
| **FastAPI** | latest | Web 框架 |
| **SQLite** | 3.x | 存储 |
