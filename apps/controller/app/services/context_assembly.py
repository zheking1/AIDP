import hashlib
from typing import Any, Dict, List
from dataclasses import dataclass, field
from enum import Enum


class Priority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class PrioritizedContext:
    content: str
    priority: Priority
    source: str
    relevance_score: float
    metadata: Dict = field(default_factory=dict)


class ContextAssembler:
    """上下文组装器：优先级分配、去重、压缩、排序"""

    def __init__(self, max_tokens: int = 8000):
        self.max_tokens = max_tokens

    def assemble(
        self,
        context_items: List[Dict],
    ) -> Dict:
        prioritized = self._prioritize_items(context_items)
        deduplicated = self._deduplicate(prioritized)
        compressed = self._compress(deduplicated)
        sorted_items = self._sort(compressed)
        final_context = self._build_final_context(sorted_items)

        return {
            "items": sorted_items,
            "total_tokens": self._count_tokens(final_context),
            "compression_ratio": round(len(deduplicated) / len(sorted_items), 2) if sorted_items else 1.0,
            "context": final_context,
        }

    def _prioritize_items(self, items: List[Dict]) -> List[PrioritizedContext]:
        prioritized = []

        for item in items:
            source = item.get("source", "unknown")

            if source == "instructions":
                priority = Priority.CRITICAL
            elif source in ("memory", "knowledge"):
                priority = Priority.HIGH
            elif source == "code_index":
                priority = Priority.MEDIUM
            else:
                priority = Priority.LOW

            prioritized.append(PrioritizedContext(
                content=item.get("content", ""),
                priority=priority,
                source=source,
                relevance_score=item.get("relevance_score", 0.5),
                metadata=item.get("metadata", {}),
            ))

        return prioritized

    def _deduplicate(self, items: List[PrioritizedContext]) -> List[PrioritizedContext]:
        seen = set()
        deduplicated = []

        for item in items:
            content_hash = hashlib.md5(item.content.encode()).hexdigest()
            if content_hash not in seen:
                seen.add(content_hash)
                deduplicated.append(item)

        return deduplicated

    def _compress(self, items: List[PrioritizedContext]) -> List[PrioritizedContext]:
        total_tokens = self._count_tokens(" ".join(item.content for item in items))

        if total_tokens <= self.max_tokens:
            return items

        compressed = []
        current_tokens = 0

        for item in items:
            item_tokens = self._count_tokens(item.content)
            if current_tokens + item_tokens <= self.max_tokens:
                compressed.append(item)
                current_tokens += item_tokens
            else:
                remaining_tokens = self.max_tokens - current_tokens
                if remaining_tokens > 100:
                    truncated_content = self._truncate(item.content, remaining_tokens)
                    compressed.append(PrioritizedContext(
                        content=truncated_content,
                        priority=item.priority,
                        source=item.source,
                        relevance_score=item.relevance_score,
                        metadata=item.metadata,
                    ))
                break

        return compressed

    def _sort(self, items: List[PrioritizedContext]) -> List[PrioritizedContext]:
        return sorted(items, key=lambda x: (x.priority.value, -x.relevance_score))

    def _build_final_context(self, items: List[PrioritizedContext]) -> str:
        sections = []
        for item in items:
            sections.append(f"[{item.source.upper()}] {item.content}")
        return "\n\n".join(sections)

    def _count_tokens(self, text: str) -> int:
        return len(text) // 4

    def _truncate(self, text: str, max_tokens: int) -> str:
        max_chars = max_tokens * 4
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "..."


class ContextCompressor:
    """上下文压缩器"""

    def compress(self, context: str, target_tokens: int) -> str:
        current_tokens = len(context) // 4
        if current_tokens <= target_tokens:
            return context

        compressed = self._remove_redundancy(context)

        if len(compressed) // 4 > target_tokens:
            compressed = self._extract_key_info(compressed)

        if len(compressed) // 4 > target_tokens:
            compressed = self._summarize_paragraphs(compressed)

        return compressed

    def _remove_redundancy(self, context: str) -> str:
        lines = context.split("\n")
        unique_lines = []
        seen = set()

        for line in lines:
            line_hash = hashlib.md5(line.encode()).hexdigest()
            if line_hash not in seen:
                seen.add(line_hash)
                unique_lines.append(line)

        return "\n".join(unique_lines)

    def _extract_key_info(self, context: str) -> str:
        keywords = ["定义", "配置", "规则", "约束", "重要", "核心", "必须"]

        key_lines = []
        for line in context.split("\n"):
            if any(keyword in line for keyword in keywords):
                key_lines.append(line)

        return "\n".join(key_lines) if key_lines else context[:1000]

    def _summarize_paragraphs(self, context: str) -> str:
        paragraphs = context.split("\n\n")
        summarized = []

        for para in paragraphs:
            if len(para) > 200:
                summarized.append(para[:200] + "...")
            else:
                summarized.append(para)

        return "\n\n".join(summarized)