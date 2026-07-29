import re
from typing import Dict, List, Optional


class ResultRefiner:
    def refine(self, raw_results: Dict[str, List], budget: int) -> Dict:
        refined = {}
        remaining = budget
        for tool_name, results in raw_results.items():
            if not results:
                refined[tool_name] = []
                continue
            deduped = self.deduplicate(results)
            compressed = self.compress(deduped)
            tokens = self.estimate_tokens(compressed)
            if tokens > remaining:
                compressed = compressed[:max(1, len(compressed) // 2)]
                tokens = self.estimate_tokens(compressed)
            refined[tool_name] = compressed
            remaining -= tokens
        total_tokens = budget - remaining
        return {
            "refined": refined,
            "total_tokens": total_tokens,
            "remaining_budget": remaining,
        }

    def deduplicate(self, results: List) -> List:
        seen = set()
        unique = []
        for r in results:
            key = str(r.get("content", r.get("title", "")))[:100]
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return unique

    def compress(self, results: List) -> List:
        compressed = []
        for r in results:
            item = dict(r)
            desc = item.get("description", "")
            if desc and len(desc) > 200:
                item["description"] = desc[:200] + "..."
            code = item.get("code", "")
            if code:
                lines = code.split("\n")
                if len(lines) > 20:
                    item["code"] = "\n".join(lines[:10]) + "\n...\n" + "\n".join(lines[-5:])
            item["items"] = item.get("items", [])[:5]
            compressed.append(item)
        return compressed

    def estimate_tokens(self, data) -> int:
        if isinstance(data, str):
            return max(1, len(data) // 4)
        if isinstance(data, list):
            return sum(self.estimate_tokens(i) for i in data)
        if isinstance(data, dict):
            return sum(self.estimate_tokens(v) for v in data.values())
        return max(1, len(str(data)) // 4)
