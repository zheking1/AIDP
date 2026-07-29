import re
from typing import Dict, List
from dataclasses import dataclass, field


@dataclass
class IntentResult:
    original_query: str
    surface_intent: Dict = field(default_factory=dict)
    semantic_intent: Dict = field(default_factory=dict)
    pragmatic_intent: Dict = field(default_factory=dict)
    confidence: float = 0.0
    suggested_tools: List[str] = field(default_factory=list)
    query_expansion: List[str] = field(default_factory=list)


class IntentParserV2:
    """增强意图解析器 - 3层分析"""

    INTENT_PATTERNS = {
        "search": {"keywords": ["搜索", "查找", "查询", "search", "find", "look", "检索"],
                   "patterns": [r"查找.*代码", r"搜索.*函数", r"查询.*文件"]},
        "analyze": {"keywords": ["分析", "检查", "审查", "analyze", "check", "review", "audit"],
                    "patterns": [r"分析.*代码", r"检查.*质量", r"审查.*变更"]},
        "fix": {"keywords": ["修复", "修改", "修正", "fix", "repair", "resolve", "解决"],
                "patterns": [r"修复.*bug", r"修改.*问题", r"修正.*错误"]},
        "create": {"keywords": ["创建", "生成", "新建", "create", "generate", "new", "开发"],
                   "patterns": [r"创建.*文件", r"生成.*代码", r"新建.*项目"]},
    }

    TOOL_INTENT_MAPPING = {
        "code.search": ["search", "find", "look"],
        "code.explore": ["analyze", "check", "review"],
        "memory.search": ["search", "find", "recall"],
        "memory.create": ["create", "save", "store"],
        "knowledge.search": ["search", "find", "learn"],
        "quality.check": ["analyze", "check", "review"],
    }

    def parse(self, query: str) -> IntentResult:
        surface = self._parse_surface(query)
        semantic = self._parse_semantic(query)
        pragmatic = self._parse_pragmatic(query, surface, semantic)
        confidence = self._calculate_confidence(surface, semantic, pragmatic)
        tools = self._suggest_tools(surface, semantic)
        expansions = self._expand_query(query, surface, semantic)

        return IntentResult(
            original_query=query,
            surface_intent=surface,
            semantic_intent=semantic,
            pragmatic_intent=pragmatic,
            confidence=confidence,
            suggested_tools=tools,
            query_expansion=expansions,
        )

    def _parse_surface(self, query: str) -> Dict:
        words = query.lower().split()
        matched = []
        for intent, config in self.INTENT_PATTERNS.items():
            for kw in config["keywords"]:
                if kw in words:
                    matched.append(intent)
                    break
        return {"intents": matched, "keywords": [w for w in words if len(w) > 2], "query_length": len(words)}

    def _parse_semantic(self, query: str) -> Dict:
        matched = []
        for intent, config in self.INTENT_PATTERNS.items():
            for pattern in config["patterns"]:
                if re.search(pattern, query):
                    matched.append({"intent": intent, "pattern": pattern})
        return {"patterns": matched, "has_pattern_match": len(matched) > 0}

    def _parse_pragmatic(self, query: str, surface: Dict, semantic: Dict) -> Dict:
        intents = surface.get("intents", [])
        if "search" in intents:
            purpose = "information_retrieval"
        elif "analyze" in intents:
            purpose = "quality_assurance"
        elif "fix" in intents:
            purpose = "problem_solving"
        elif "create" in intents:
            purpose = "development"
        else:
            purpose = "general"
        return {"purpose": purpose, "urgency": self._urgency(query), "complexity": self._complexity(query)}

    def _calculate_confidence(self, surface: Dict, semantic: Dict, pragmatic: Dict) -> float:
        c = 0.0
        if surface.get("intents"):
            c += 0.3
        if semantic.get("has_pattern_match"):
            c += 0.4
        if pragmatic.get("purpose") != "general":
            c += 0.3
        return min(c, 1.0)

    def _suggest_tools(self, surface: Dict, semantic: Dict) -> List[str]:
        suggested = set()
        for intent in surface.get("intents", []):
            for tool, intents in self.TOOL_INTENT_MAPPING.items():
                if intent in intents:
                    suggested.add(tool)
        for p in semantic.get("patterns", []):
            for tool, intents in self.TOOL_INTENT_MAPPING.items():
                if p["intent"] in intents:
                    suggested.add(tool)
        return list(suggested)

    def _expand_query(self, query: str, surface: Dict, semantic: Dict) -> List[str]:
        expansions = []
        synonyms = {"搜索": ["查找", "search"], "分析": ["检查", "analyze"], "修复": ["修改", "fix"], "创建": ["生成", "create"]}
        for kw in surface.get("keywords", []):
            if kw in synonyms:
                expansions.extend(synonyms[kw])
        return list(set(expansions))

    def _urgency(self, query: str) -> str:
        urgent = ["紧急", "urgent", "马上", "立即", "asap"]
        return "high" if any(k in query.lower() for k in urgent) else "normal"

    def _complexity(self, query: str) -> str:
        complex_kw = ["复杂", "complex", "多个", "multiple", "集成", "integrate"]
        return "high" if any(k in query.lower() for k in complex_kw) else "normal"


class ToolMatcherV2:
    """智能工具匹配器"""

    TOOL_CAPABILITIES = {
        "code.search": {"capabilities": ["symbol_search", "file_search"], "languages": ["python", "javascript", "typescript", "go"], "latency": "low"},
        "code.explore": {"capabilities": ["file_list", "directory_tree"], "languages": ["python", "javascript"], "latency": "low"},
        "memory.search": {"capabilities": ["semantic_search", "keyword_search"], "languages": ["all"], "latency": "medium"},
        "memory.create": {"capabilities": ["memory_creation", "memory_update"], "languages": ["all"], "latency": "low"},
        "knowledge.search": {"capabilities": ["document_search", "concept_search"], "languages": ["all"], "latency": "high"},
        "quality.check": {"capabilities": ["code_analysis", "complexity_check"], "languages": ["python", "javascript"], "latency": "medium"},
    }

    def __init__(self):
        self.match_history = []
        self.usage_stats = {}

    def match(self, intent: IntentResult, budget: Dict = None) -> List[Dict]:
        candidates = set(intent.suggested_tools)
        for tool, caps in self.TOOL_CAPABILITIES.items():
            for cap in caps["capabilities"]:
                if any(kw in cap for kw in intent.surface_intent.get("keywords", [])):
                    candidates.add(tool)

        results = []
        for tool in candidates:
            if tool not in self.TOOL_CAPABILITIES:
                continue
            caps = self.TOOL_CAPABILITIES[tool]
            score = 0.0
            reasons = []
            if tool in intent.suggested_tools:
                score += 0.4
                reasons.append("意图直接匹配")
            if "python" in caps["languages"] or "all" in caps["languages"]:
                score += 0.1
                reasons.append("语言支持")
            success_rate = self.usage_stats.get(tool, {}).get("success_rate", 0.5)
            score += 0.1 * success_rate
            results.append({"tool_name": tool, "score": min(score, 1.0), "reasons": reasons})

        results.sort(key=lambda x: x["score"], reverse=True)
        self._record(intent, results)
        return results

    def _record(self, intent: IntentResult, results: List[Dict]):
        self.match_history.append({"intent": intent.original_query, "tools": [r["tool_name"] for r in results[:3]]})
        if results:
            t = results[0]["tool_name"]
            self.usage_stats.setdefault(t, {"count": 0, "successes": 0})["count"] += 1

    def update_success(self, tool_name: str, success: bool):
        if tool_name in self.usage_stats:
            self.usage_stats[tool_name]["count"] += 1
            if success:
                self.usage_stats[tool_name]["successes"] += 1
            c = self.usage_stats[tool_name]["count"]
            s = self.usage_stats[tool_name]["successes"]
            self.usage_stats[tool_name]["success_rate"] = s / c if c > 0 else 0.5