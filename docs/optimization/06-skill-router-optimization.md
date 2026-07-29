# Skill-Router 工具优化设计文档

## 1. 现状分析

### 1.1 当前架构
```
tools/skill-router/app/
├── api/
│   └── tool.py              # MCP接口
├── services/
│   ├── intent_parser.py     # 意图解析
│   ├── tool_matcher.py      # 工具匹配
│   └── query_optimizer.py   # 查询优化
└── models/
    └── intent.py            # 意图模型
```

### 1.2 现有能力
| 能力 | 实现方式 | 问题 |
|------|----------|------|
| 意图解析 | 关键词匹配 | 无法理解复杂意图 |
| 工具匹配 | 规则匹配 | 规则有限，无法扩展 |
| 查询优化 | 简单改写 | 无语义理解 |
| 预算控制 | 静态配置 | 无法动态调整 |

### 1.3 核心问题
1. **意图解析粗糙**：仅关键词匹配，无法理解上下文
2. **工具匹配静态**：硬编码规则，无法适应新工具
3. **查询优化简单**：无语义理解，无法有效改写
4. **无学习能力**：无法从历史中学习优化
5. **无反馈机制**：无法根据结果调整策略

---

## 2. 优化目标

| 目标 | 指标 | 当前值 | 目标值 |
|------|------|--------|--------|
| 意图识别准确率 | Top-1准确率 | ~50% | >80% |
| 工具匹配准确率 | 匹配正确率 | ~60% | >90% |
| 查询优化效果 | 搜索质量提升 | 0% | >30% |
| 响应延迟 | P95延迟 | ~500ms | <200ms |
| 学习能力 | 从历史学习 | 无 | 有 |

---

## 3. 优化设计

### 3.1 模块一：增强意图解析

#### 3.1.1 多层次意图解析

**新增文件：`app/services/intent_parser_v2.py`**
```python
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum
import re

class IntentLevel(Enum):
    """意图层次"""
    SURFACE = 'surface'      # 表层意图（关键词）
    SEMANTIC = 'semantic'    # 语义意图（含义）
    PRAGMATIC = 'pragmatic'  # 语用意图（目的）

@dataclass
class IntentResult:
    """意图解析结果"""
    original_query: str
    surface_intent: Dict      # 表层意图
    semantic_intent: Dict     # 语义意图
    pragmatic_intent: Dict    # 语用意图
    confidence: float         # 置信度
    suggested_tools: List[str]  # 建议工具
    query_expansion: List[str]  # 查询扩展

class IntentParserV2:
    """增强意图解析器"""
    
    def __init__(self):
        # 意图模式库
        self.intent_patterns = {
            'search': {
                'keywords': ['搜索', '查找', '查找', '查询', 'search', 'find', 'look'],
                'patterns': [
                    r'查找.*代码',
                    r'搜索.*函数',
                    r'查询.*文件'
                ]
            },
            'analyze': {
                'keywords': ['分析', '检查', '审查', 'analyze', 'check', 'review'],
                'patterns': [
                    r'分析.*代码',
                    r'检查.*质量',
                    r'审查.*变更'
                ]
            },
            'fix': {
                'keywords': ['修复', '修改', '修正', 'fix', 'repair', 'resolve'],
                'patterns': [
                    r'修复.*bug',
                    r'修改.*问题',
                    r'修正.*错误'
                ]
            },
            'create': {
                'keywords': ['创建', '生成', '新建', 'create', 'generate', 'new'],
                'patterns': [
                    r'创建.*文件',
                    r'生成.*代码',
                    r'新建.*项目'
                ]
            }
        }
        
        # 工具-意图映射
        self.tool_intent_mapping = {
            'code.search': ['search', 'find', 'look'],
            'code.explore': ['analyze', 'check', 'review'],
            'memory.search': ['search', 'find', 'recall'],
            'memory.create': ['create', 'save', 'store'],
            'knowledge.search': ['search', 'find', 'learn'],
            'quality.check': ['analyze', 'check', 'review']
        }
    
    async def parse(self, query: str) -> IntentResult:
        """解析意图"""
        
        # 1. 表层意图（关键词匹配）
        surface_intent = self._parse_surface(query)
        
        # 2. 语义意图（模式匹配）
        semantic_intent = self._parse_semantic(query)
        
        # 3. 语用意图（上下文推断）
        pragmatic_intent = self._parse_pragmatic(query, surface_intent, semantic_intent)
        
        # 4. 计算置信度
        confidence = self._calculate_confidence(surface_intent, semantic_intent, pragmatic_intent)
        
        # 5. 建议工具
        suggested_tools = self._suggest_tools(surface_intent, semantic_intent)
        
        # 6. 查询扩展
        query_expansion = self._expand_query(query, surface_intent, semantic_intent)
        
        return IntentResult(
            original_query=query,
            surface_intent=surface_intent,
            semantic_intent=semantic_intent,
            pragmatic_intent=pragmatic_intent,
            confidence=confidence,
            suggested_tools=suggested_tools,
            query_expansion=query_expansion
        )
    
    def _parse_surface(self, query: str) -> Dict:
        """解析表层意图"""
        words = query.lower().split()
        
        # 关键词匹配
        matched_intents = []
        for intent, config in self.intent_patterns.items():
            for keyword in config['keywords']:
                if keyword in words:
                    matched_intents.append(intent)
                    break
        
        return {
            'intents': matched_intents,
            'keywords': [w for w in words if len(w) > 2],
            'query_length': len(words)
        }
    
    def _parse_semantic(self, query: str) -> Dict:
        """解析语义意图"""
        matched_patterns = []
        
        for intent, config in self.intent_patterns.items():
            for pattern in config['patterns']:
                if re.search(pattern, query):
                    matched_patterns.append({
                        'intent': intent,
                        'pattern': pattern
                    })
        
        return {
            'patterns': matched_patterns,
            'has_pattern_match': len(matched_patterns) > 0
        }
    
    def _parse_pragmatic(
        self,
        query: str,
        surface: Dict,
        semantic: Dict
    ) -> Dict:
        """解析语用意图"""
        # 基于表层和语义意图推断目的
        
        # 如果有搜索意图，可能是查找信息
        if 'search' in surface.get('intents', []):
            purpose = 'information_retrieval'
        # 如果有分析意图，可能是质量检查
        elif 'analyze' in surface.get('intents', []):
            purpose = 'quality_assurance'
        # 如果有修复意图，可能是问题解决
        elif 'fix' in surface.get('intents', []):
            purpose = 'problem_solving'
        # 如果有创建意图，可能是开发任务
        elif 'create' in surface.get('intents', []):
            purpose = 'development'
        else:
            purpose = 'general'
        
        return {
            'purpose': purpose,
            'urgency': self._estimate_urgency(query),
            'complexity': self._estimate_complexity(query)
        }
    
    def _calculate_confidence(
        self,
        surface: Dict,
        semantic: Dict,
        pragmatic: Dict
    ) -> float:
        """计算置信度"""
        confidence = 0.0
        
        # 表层意图匹配
        if surface.get('intents'):
            confidence += 0.3
        
        # 语义模式匹配
        if semantic.get('has_pattern_match'):
            confidence += 0.4
        
        # 语用意图明确
        if pragmatic.get('purpose') != 'general':
            confidence += 0.3
        
        return min(confidence, 1.0)
    
    def _suggest_tools(
        self,
        surface: Dict,
        semantic: Dict
    ) -> List[str]:
        """建议工具"""
        suggested = set()
        
        # 基于表层意图
        for intent in surface.get('intents', []):
            for tool, intents in self.tool_intent_mapping.items():
                if intent in intents:
                    suggested.add(tool)
        
        # 基于语义模式
        for pattern in semantic.get('patterns', []):
            intent = pattern['intent']
            for tool, intents in self.tool_intent_mapping.items():
                if intent in intents:
                    suggested.add(tool)
        
        return list(suggested)
    
    def _expand_query(
        self,
        query: str,
        surface: Dict,
        semantic: Dict
    ) -> List[str]:
        """查询扩展"""
        expansions = []
        
        # 基于关键词扩展
        for keyword in surface.get('keywords', []):
            if keyword in ['搜索', 'search']:
                expansions.append('查找')
            elif keyword in ['分析', 'analyze']:
                expansions.append('检查')
            elif keyword in ['修复', 'fix']:
                expansions.append('修改')
        
        # 基于模式扩展
        for pattern in semantic.get('patterns', []):
            if pattern['intent'] == 'search':
                expansions.append('代码搜索')
            elif pattern['intent'] == 'analyze':
                expansions.append('代码分析')
        
        return list(set(expansions))
    
    def _estimate_urgency(self, query: str) -> str:
        """估计紧急程度"""
        urgent_keywords = ['紧急', 'urgent', '马上', '立即', 'asap']
        if any(keyword in query.lower() for keyword in urgent_keywords):
            return 'high'
        return 'normal'
    
    def _estimate_complexity(self, query: str) -> str:
        """估计复杂度"""
        complex_keywords = ['复杂', 'complex', '多个', 'multiple', '集成', 'integrate']
        if any(keyword in query.lower() for keyword in complex_keywords):
            return 'high'
        return 'normal'
```

### 3.2 模块二：智能工具匹配

#### 3.2.1 基于学习的工具匹配

**新增文件：`app/services/tool_matcher_v2.py`**
```python
from typing import List, Dict, Optional
from dataclasses import dataclass
import json

@dataclass
class ToolMatchResult:
    """工具匹配结果"""
    tool_name: str
    capability: str
    score: float
    reasons: List[str]
    alternative_tools: List[Dict]

class ToolMatcherV2:
    """智能工具匹配器"""
    
    def __init__(self):
        # 工具能力索引
        self.tool_capabilities = self._load_tool_capabilities()
        
        # 历史匹配记录
        self.match_history = []
        
        # 工具使用统计
        self.usage_stats = {}
    
    def _load_tool_capabilities(self) -> Dict:
        """加载工具能力"""
        return {
            'code.search': {
                'capabilities': ['symbol_search', 'file_search', 'content_search'],
                'languages': ['python', 'javascript', 'typescript', 'go'],
                'complexity': 'medium',
                'latency': 'low'
            },
            'code.explore': {
                'capabilities': ['file_list', 'directory_tree', 'dependency_analysis'],
                'languages': ['python', 'javascript', 'typescript', 'go'],
                'complexity': 'low',
                'latency': 'low'
            },
            'memory.search': {
                'capabilities': ['semantic_search', 'keyword_search', 'time_based'],
                'languages': ['all'],
                'complexity': 'medium',
                'latency': 'medium'
            },
            'memory.create': {
                'capabilities': ['memory_creation', 'memory_update', 'memory_deletion'],
                'languages': ['all'],
                'complexity': 'low',
                'latency': 'low'
            },
            'knowledge.search': {
                'capabilities': ['document_search', 'concept_search', 'relation_search'],
                'languages': ['all'],
                'complexity': 'high',
                'latency': 'high'
            },
            'quality.check': {
                'capabilities': ['code_analysis', 'complexity_check', 'duplication_detection'],
                'languages': ['python', 'javascript', 'typescript'],
                'complexity': 'medium',
                'latency': 'medium'
            }
        }
    
    async def match(
        self,
        intent: IntentResult,
        budget: Dict = None
    ) -> List[ToolMatchResult]:
        """匹配工具"""
        
        # 1. 获取候选工具
        candidates = self._get_candidates(intent)
        
        # 2. 评分
        scored = self._score_candidates(candidates, intent)
        
        # 3. 预算过滤
        if budget:
            scored = self._filter_by_budget(scored, budget)
        
        # 4. 排序
        scored.sort(key=lambda x: x.score, reverse=True)
        
        # 5. 记录匹配
        self._record_match(intent, scored)
        
        return scored
    
    def _get_candidates(self, intent: IntentResult) -> List[str]:
        """获取候选工具"""
        candidates = set()
        
        # 基于意图建议
        candidates.update(intent.suggested_tools)
        
        # 基于能力匹配
        for tool, capabilities in self.tool_capabilities.items():
            for capability in capabilities['capabilities']:
                if any(keyword in capability for keyword in intent.surface_intent.get('keywords', [])):
                    candidates.add(tool)
        
        return list(candidates)
    
    def _score_candidates(
        self,
        candidates: List[str],
        intent: IntentResult
    ) -> List[ToolMatchResult]:
        """给候选工具评分"""
        results = []
        
        for tool in candidates:
            if tool not in self.tool_capabilities:
                continue
            
            capabilities = self.tool_capabilities[tool]
            
            # 计算匹配分数
            score = 0.0
            reasons = []
            
            # 意图匹配
            if tool in intent.suggested_tools:
                score += 0.4
                reasons.append('意图直接匹配')
            
            # 能力匹配
            for capability in capabilities['capabilities']:
                if any(keyword in capability for keyword in intent.surface_intent.get('keywords', [])):
                    score += 0.2
                    reasons.append(f'能力匹配: {capability}')
                    break
            
            # 语言支持
            if 'all' in capabilities['languages'] or 'python' in capabilities['languages']:
                score += 0.1
                reasons.append('语言支持')
            
            # 历史使用
            if tool in self.usage_stats:
                usage_count = self.usage_stats[tool].get('count', 0)
                success_rate = self.usage_stats[tool].get('success_rate', 0)
                score += 0.1 * success_rate
                reasons.append(f'历史成功率: {success_rate:.1%}')
            
            # 复杂度匹配
            if capabilities['complexity'] == 'low':
                score += 0.1
                reasons.append('低复杂度')
            
            # 获取替代工具
            alternatives = self._get_alternatives(tool, intent)
            
            results.append(ToolMatchResult(
                tool_name=tool,
                capability=self._get_best_capability(tool, intent),
                score=min(score, 1.0),
                reasons=reasons,
                alternative_tools=alternatives
            ))
        
        return results
    
    def _get_best_capability(self, tool: str, intent: IntentResult) -> str:
        """获取最佳能力"""
        if tool not in self.tool_capabilities:
            return 'default'
        
        capabilities = self.tool_capabilities[tool]['capabilities']
        
        # 基于意图选择能力
        for keyword in intent.surface_intent.get('keywords', []):
            for capability in capabilities:
                if keyword in capability:
                    return capability
        
        return capabilities[0] if capabilities else 'default'
    
    def _get_alternatives(self, tool: str, intent: IntentResult) -> List[Dict]:
        """获取替代工具"""
        alternatives = []
        
        for other_tool, capabilities in self.tool_capabilities.items():
            if other_tool == tool:
                continue
            
            # 检查能力重叠
            overlap = set(self.tool_capabilities[tool]['capabilities']) & set(capabilities['capabilities'])
            if overlap:
                alternatives.append({
                    'tool': other_tool,
                    'overlap_capabilities': list(overlap),
                    'reason': f'共享能力: {", ".join(overlap)}'
                })
        
        return alternatives[:3]  # 最多3个替代工具
    
    def _filter_by_budget(
        self,
        candidates: List[ToolMatchResult],
        budget: Dict
    ) -> List[ToolMatchResult]:
        """根据预算过滤"""
        max_latency = budget.get('max_latency', 5.0)
        max_cost = budget.get('max_cost', 1.0)
        
        filtered = []
        for candidate in candidates:
            tool_info = self.tool_capabilities.get(candidate.tool_name, {})
            latency = self._estimate_latency(tool_info.get('latency', 'medium'))
            
            if latency <= max_latency:
                filtered.append(candidate)
        
        return filtered
    
    def _estimate_latency(self, latency_level: str) -> float:
        """估计延迟（秒）"""
        latency_map = {
            'low': 0.5,
            'medium': 2.0,
            'high': 5.0
        }
        return latency_map.get(latency_level, 2.0)
    
    def _record_match(self, intent: IntentResult, results: List[ToolMatchResult]):
        """记录匹配"""
        self.match_history.append({
            'intent': intent.original_query,
            'results': [r.tool_name for r in results[:3]],
            'timestamp': datetime.now()
        })
        
        # 更新使用统计
        if results:
            top_tool = results[0].tool_name
            if top_tool not in self.usage_stats:
                self.usage_stats[top_tool] = {'count': 0, 'successes': 0}
            self.usage_stats[top_tool]['count'] += 1
    
    def update_success(self, tool_name: str, success: bool):
        """更新成功状态"""
        if tool_name in self.usage_stats:
            self.usage_stats[tool_name]['count'] += 1
            if success:
                self.usage_stats[tool_name]['successes'] += 1
            
            # 计算成功率
            count = self.usage_stats[tool_name]['count']
            successes = self.usage_stats[tool_name]['successes']
            self.usage_stats[tool_name]['success_rate'] = successes / count if count > 0 else 0
```

### 3.3 模块三：查询优化器

#### 3.3.1 语义查询优化

**新增文件：`app/services/query_optimizer_v2.py`**
```python
from typing import List, Dict, Optional
import re

class QueryOptimizerV2:
    """语义查询优化器"""
    
    def __init__(self):
        # 同义词库
        self.synonyms = {
            '搜索': ['查找', '查询', 'search', 'find'],
            '分析': ['检查', '审查', 'analyze', 'check'],
            '修复': ['修改', '修正', 'fix', 'repair'],
            '创建': ['生成', '新建', 'create', 'generate']
        }
        
        # 领域术语
        self.domain_terms = {
            'cookie': ['会话', 'session', '认证', 'authentication'],
            'api': ['接口', '端点', 'endpoint', '接口'],
            'database': ['数据库', 'db', '存储', 'storage']
        }
    
    async def optimize(
        self,
        query: str,
        intent: IntentResult,
        context: Dict = None
    ) -> Dict:
        """优化查询"""
        
        # 1. 查询清洗
        cleaned = self._clean_query(query)
        
        # 2. 查询扩展
        expanded = self._expand_query(cleaned, intent)
        
        # 3. 查询重构
        restructured = self._restructure_query(expanded, intent)
        
        # 4. 查询增强
        enhanced = self._enhance_query(restructured, context)
        
        # 5. 生成多个查询变体
        variants = self._generate_variants(enhanced)
        
        return {
            'original': query,
            'optimized': enhanced,
            'variants': variants,
            'expansions': expanded.get('expansions', []),
            'restructuring_rules': restructured.get('rules_applied', [])
        }
    
    def _clean_query(self, query: str) -> str:
        """清洗查询"""
        # 移除多余空格
        cleaned = re.sub(r'\s+', ' ', query)
        
        # 移除特殊字符（保留中文和英文）
        cleaned = re.sub(r'[^\w\s\u4e00-\u9fff]', '', cleaned)
        
        return cleaned.strip()
    
    def _expand_query(self, query: str, intent: IntentResult) -> Dict:
        """扩展查询"""
        expansions = []
        
        # 基于同义词扩展
        for word, synonyms in self.synonyms.items():
            if word in query:
                expansions.extend(synonyms[:2])  # 每个词最多2个同义词
        
        # 基于领域术语扩展
        for term, related in self.domain_terms.items():
            if term in query.lower():
                expansions.extend(related[:2])
        
        # 基于意图扩展
        for keyword in intent.surface_intent.get('keywords', []):
            if keyword in self.synonyms:
                expansions.extend(self.synonyms[keyword][:1])
        
        return {
            'expanded_query': query + ' ' + ' '.join(expansions),
            'expansions': expansions
        }
    
    def _restructure_query(self, query: Dict, intent: IntentResult) -> Dict:
        """重构查询"""
        original = query.get('expanded_query', '')
        rules_applied = []
        
        # 规则1：将搜索意图放在前面
        if 'search' in intent.surface_intent.get('intents', []):
            if not original.startswith(('搜索', '查找', 'search', 'find')):
                original = '搜索 ' + original
                rules_applied.append('搜索意图前置')
        
        # 规则2：添加项目上下文
        if 'project' in intent.original_query.lower():
            rules_applied.append('项目上下文已存在')
        else:
            original = original + ' 项目'
            rules_applied.append('添加项目上下文')
        
        # 规则3：简化冗余表达
        original = re.sub(r'查找.*代码', '代码搜索', original)
        original = re.sub(r'分析.*质量', '质量分析', original)
        rules_applied.append('简化冗余表达')
        
        return {
            'restructured_query': original,
            'rules_applied': rules_applied
        }
    
    def _enhance_query(self, query: Dict, context: Dict = None) -> str:
        """增强查询"""
        enhanced = query.get('restructured_query', '')
        
        # 添加上下文信息
        if context:
            if 'project_name' in context:
                enhanced = f"{context['project_name']} {enhanced}"
            if 'file_path' in context:
                enhanced = f"{enhanced} 文件:{context['file_path']}"
        
        return enhanced
    
    def _generate_variants(self, query: str) -> List[str]:
        """生成查询变体"""
        variants = []
        
        # 变体1：简化版
        simple = re.sub(r'\s+', ' ', query)
        variants.append(simple)
        
        # 变体2：详细版
        detailed = query + ' 详细信息'
        variants.append(detailed)
        
        # 变体3：精确版
        exact = query + ' 精确匹配'
        variants.append(exact)
        
        return variants
```

---

## 4. API设计

### 4.1 新增/修改的API

#### 增强意图解析
```python
@router.post("/api/skill-router/parse/enhanced")
async def parse_intent_enhanced(request: EnhancedParseRequest):
    """
    增强意图解析
    
    Request:
    {
        "query": "帮我查找上次修复的cookie问题",
        "context": {
            "project": "aidp",
            "user_id": "user-123"
        }
    }
    
    Response:
    {
        "surface_intent": {
            "intents": ["search"],
            "keywords": ["查找", "cookie", "问题"],
            "query_length": 10
        },
        "semantic_intent": {
            "patterns": [{"intent": "search", "pattern": "查找.*代码"}],
            "has_pattern_match": true
        },
        "pragmatic_intent": {
            "purpose": "information_retrieval",
            "urgency": "normal",
            "complexity": "normal"
        },
        "confidence": 0.8,
        "suggested_tools": ["code.search", "memory.search"],
        "query_expansion": ["搜索", "代码搜索"]
    }
    """
```

#### 智能工具匹配
```python
@router.post("/api/skill-router/match/intelligent")
async def match_tools_intelligent(request: IntelligentMatchRequest):
    """
    智能工具匹配
    
    Request:
    {
        "intent": {
            "original_query": "查找cookie问题",
            "surface_intent": {"intents": ["search"]},
            "suggested_tools": ["code.search"]
        },
        "budget": {
            "max_latency": 2.0,
            "max_cost": 1.0
        }
    }
    
    Response:
    {
        "matches": [
            {
                "tool_name": "code.search",
                "capability": "symbol_search",
                "score": 0.85,
                "reasons": ["意图直接匹配", "能力匹配: symbol_search"],
                "alternative_tools": [
                    {"tool": "memory.search", "overlap_capabilities": ["semantic_search"]}
                ]
            }
        ],
        "total_candidates": 4,
        "filtered_by_budget": 2
    }
    """
```

#### 语义查询优化
```python
@router.post("/api/skill-router/optimize/semantic")
async def optimize_query_semantic(request: SemanticOptimizeRequest):
    """
    语义查询优化
    
    Request:
    {
        "query": "查找cookie问题",
        "intent": {
            "surface_intent": {"intents": ["search"]},
            "keywords": ["查找", "cookie"]
        },
        "context": {
            "project_name": "aidp"
        }
    }
    
    Response:
    {
        "original": "查找cookie问题",
        "optimized": "aidp 搜索 cookie 问题 会话 session",
        "variants": [
            "aidp 搜索 cookie 问题 会话 session",
            "aidp 搜索 cookie 问题 会话 session 详细信息",
            "aidp 搜索 cookie 问题 会话 session 精确匹配"
        ],
        "expansions": ["搜索", "查找", "会话", "session"],
        "restructuring_rules": ["搜索意图前置", "添加项目上下文"]
    }
    """
```

---

## 5. 任务拆分

### Phase 1：增强意图解析（2天）
| 任务 | 描述 | 优先级 |
|------|------|--------|
| T1.1 | 实现IntentParserV2 | P0 |
| T1.2 | 实现多层次意图分析 | P0 |
| T1.3 | 集成到流水线 | P1 |

### Phase 2：智能工具匹配（2天）
| 任务 | 描述 | 优先级 |
|------|------|--------|
| T2.1 | 实现ToolMatcherV2 | P0 |
| T2.2 | 实现学习机制 | P1 |
| T2.3 | 集成到流水线 | P1 |

### Phase 3：查询优化器（1天）
| 任务 | 描述 | 优先级 |
|------|------|--------|
| T3.1 | 实现QueryOptimizerV2 | P1 |
| T3.2 | 实现查询扩展 | P1 |
| T3.3 | 集成到流水线 | P2 |

### Phase 4：反馈机制（1天）
| 任务 | 描述 | 优先级 |
|------|------|--------|
| T4.1 | 实现使用统计 | P2 |
| T4.2 | 实现成功反馈 | P2 |
| T4.3 | 实现学习更新 | P2 |

---

## 6. 依赖和风险

### 6.1 技术依赖
| 依赖 | 用途 | 备选方案 |
|------|------|----------|
| re | 正则表达式 | 字符串匹配 |
| json | 配置加载 | 硬编码 |
| datetime | 时间记录 | 无 |

### 6.2 风险点
| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 同义词库不全 | 查询扩展效果差 | 持续更新同义词库 |
| 学习数据不足 | 匹配效果不佳 | 冷启动+在线学习 |
| 性能问题 | 响应延迟 | 缓存+异步处理 |

---

## 7. 验收标准

| 验收项 | 标准 |
|--------|------|
| 意图识别 | 能识别搜索/分析/修复/创建意图 |
| 工具匹配 | 能根据意图匹配正确的工具 |
| 查询优化 | 优化后搜索质量提升30%+ |
| 响应延迟 | P95延迟<200ms |
| 学习能力 | 能从历史匹配中学习优化 |
