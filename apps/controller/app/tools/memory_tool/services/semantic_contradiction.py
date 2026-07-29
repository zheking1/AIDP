import re
from typing import Dict, List


class SemanticContradictionDetector:
    """基于语义的矛盾检测器"""

    NEGATION_PATTERNS = [
        r'不要', r'禁止', r'不能', r'不应该', r'避免',
        r'do not', r"don't", r'should not', r'avoid', r'never',
        r'不建议', r'不推荐', r'禁止使用',
    ]

    NEGATION_WORDS = {"不", "没", "未", "非", "别", "莫", "勿", "no", "not", "never", "don't"}

    def detect(self, new_memory: Dict, existing_memories: List[Dict]) -> List[Dict]:
        contradictions = []
        new_content = new_memory.get("content", "")

        for existing in existing_memories:
            existing_content = existing.get("content", "")
            if not existing_content:
                continue

            has_negation = self._check_negation_pattern(new_content, existing_content)
            has_semantic_reversal = self._check_semantic_reversal(new_content, existing_content)

            if has_negation or has_semantic_reversal:
                contradictions.append({
                    "existing_memory": existing,
                    "contradiction_type": "negation" if has_negation else "semantic_reversal",
                    "confidence": 0.8 if has_negation and has_semantic_reversal else 0.6,
                    "evidence": self._generate_evidence(new_memory, existing),
                })

        return contradictions

    def _check_negation_pattern(self, text1: str, text2: str) -> bool:
        for pattern in self.NEGATION_PATTERNS:
            t1_has = bool(re.search(pattern, text1))
            t2_has = bool(re.search(pattern, text2))
            if t1_has != t2_has:
                text1_words = set(text1.lower().split())
                text2_words = set(text2.lower().split())
                overlap = text1_words & text2_words
                if len(overlap) > 3:
                    return True
        return False

    def _check_semantic_reversal(self, text1: str, text2: str) -> bool:
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        overlap = words1 & words2
        if len(overlap) < 3:
            return False
        neg1 = words1 & self.NEGATION_WORDS
        neg2 = words2 & self.NEGATION_WORDS
        return bool(neg1) != bool(neg2)

    def _generate_evidence(self, mem1: Dict, mem2: Dict) -> str:
        return f"新记忆: {mem1.get('title', '')[:100]} 现有记忆: {mem2.get('title', '')[:100]}"


class ContradictionHandler:
    """矛盾处理策略"""

    def handle(self, new_memory: Dict, existing_memory: Dict,
               contradiction_type: str, confidence: float) -> Dict:
        if confidence > 0.8:
            return {"action": "flag_for_review", "reason": "高置信度矛盾，需要人工审核"}
        elif confidence > 0.6:
            new_time = new_memory.get("createdAt", "")
            old_time = existing_memory.get("createdAt", "")
            if new_time > old_time:
                return {"action": "update_existing", "reason": "新记忆更新，可能是最新实践"}
            return {"action": "keep_both", "reason": "保留两者供后续参考"}
        return {"action": "keep_both", "reason": "低置信度，可能是不同场景"}