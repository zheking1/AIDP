import re
from typing import Dict, List, Optional


INTENT_KEYWORDS = {
    "understand": ["explain", "理解", "是什么", "如何工作", "含义", "concept", "how does"],
    "write": ["create", "编写", "实现", "add", "new", "生成", "implement", "build"],
    "debug": ["fix", "调试", "错误", "bug", "error", "crash", "problem", "issue", "为什么失败"],
    "optimize": ["optimize", "优化", "性能", "speed", "fast", "improve", "加速"],
    "refactor": ["refactor", "重构", "restructure", "clean", "重构代码"],
}

TOOLS_FOR_INTENT = {
    "understand": ["knowledge", "memory"],
    "write": ["knowledge", "code-index", "asset", "memory"],
    "debug": ["code-index", "sandbox", "memory"],
    "optimize": ["code-index", "quality", "memory"],
    "refactor": ["code-index", "quality", "memory"],
}


class RequirementAnalyzer:
    def detect_intent(self, task: str) -> str:
        task_lower = task.lower()
        for intent, keywords in INTENT_KEYWORDS.items():
            for kw in keywords:
                if kw in task_lower:
                    return intent
        return "understand"

    def extract_entities(self, task: str) -> List[str]:
        entities = []
        camel_case = re.findall(r'[A-Z][a-z]+(?:[A-Z][a-z]+)*', task)
        if camel_case:
            entities.extend(camel_case)
        uppercase_words = re.findall(r'\b[A-Z]{2,}\b', task)
        if uppercase_words:
            entities.extend(uppercase_words)
        chinese_terms = re.findall(r'[\u4e00-\u9fff]{2,}', task)
        if chinese_terms:
            entities.extend(chinese_terms)
        return list(set(entities))[:20]

    def recommend_tools(self, intent: str) -> List[str]:
        return TOOLS_FOR_INTENT.get(intent, ["knowledge"])

    def build_queries(self, task: str, entities: List[str], intent: str) -> Dict[str, List[str]]:
        queries = {}
        tools = self.recommend_tools(intent)
        for tool in tools:
            if entities:
                queries[tool] = entities[:3]
            else:
                queries[tool] = [task[:100]]
        return queries

    def analyze(self, task: str, existing_content: Optional[List[str]] = None) -> Dict:
        intent = self.detect_intent(task)
        entities = self.extract_entities(task)
        tools = self.recommend_tools(intent)
        queries = self.build_queries(task, entities, intent)
        skip_topics = existing_content or []
        return {
            "intent": intent,
            "key_entities": entities,
            "required_tools": tools,
            "search_queries": queries,
            "skip_topics": skip_topics,
            "priority": "high" if intent in ("write", "debug") else "medium",
        }
