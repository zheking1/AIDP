from typing import Dict, List, Optional
from app.tools.context_optimizer.config import settings


DEFAULT_BUDGET = settings.DEFAULT_BUDGET

TOOL_PRIORITY = {
    "code-index": settings.TOOL_PRIORITY_CODE_INDEX,
    "knowledge": settings.TOOL_PRIORITY_KNOWLEDGE,
    "memory": settings.TOOL_PRIORITY_MEMORY,
    "asset": settings.TOOL_PRIORITY_ASSET,
    "quality": settings.TOOL_PRIORITY_QUALITY,
    "sandbox": settings.TOOL_PRIORITY_SANDBOX,
}


class BudgetAllocator:
    def allocate(self, plan: Dict, total_budget: Optional[int] = None) -> Dict[str, int]:
        budget = total_budget or DEFAULT_BUDGET
        tools = plan.get("required_tools", [])
        queries = plan.get("search_queries", {})
        if not tools:
            return {}
        total_priority = sum(TOOL_PRIORITY.get(t, 1.0) for t in tools)
        allocation = {}
        for tool in tools:
            priority = TOOL_PRIORITY.get(tool, 1.0)
            base = int(budget * (priority / total_priority))
            query_count = len(queries.get(tool, []))
            query_factor = max(0.5, min(query_count / 2.0, 2.0))
            allocation[tool] = int(base * query_factor)
        total = sum(allocation.values())
        if total > budget:
            scale = budget / total
            for tool in allocation:
                allocation[tool] = max(100, int(allocation[tool] * scale))
        remaining = budget - sum(allocation.values())
        return {
            "allocation": allocation,
            "total_budget": budget,
            "used": budget - remaining,
            "remaining": remaining,
        }
