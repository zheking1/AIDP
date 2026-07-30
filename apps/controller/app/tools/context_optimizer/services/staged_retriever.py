import asyncio
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class StagedRetriever:
    """Stage 2: 根据 Stage 1 的输出并行调用各工具"""

    async def retrieve(
        self,
        required_tools: List[str],
        search_queries: Dict[str, List[str]],
        budget_hints: Dict[str, int],
        task_context: dict = None,
    ) -> dict:
        results = {}
        tasks = []

        for tool_name in required_tools:
            queries = search_queries.get(tool_name, [])
            budget = budget_hints.get(tool_name, 2000)
            tasks.append(self._retrieve_from_tool(tool_name, queries, budget, task_context or {}))

        gathered = await asyncio.gather(*tasks, return_exceptions=True)

        for i, tool_name in enumerate(required_tools):
            if i < len(gathered):
                r = gathered[i]
                if isinstance(r, Exception):
                    results[tool_name] = {"error": str(r), "items": []}
                else:
                    results[tool_name] = r
            else:
                results[tool_name] = {"items": []}

        return results

    async def _retrieve_from_tool(self, tool_name: str, queries: List[str], budget: int, task_context: dict = None) -> dict:
        query_text = " ".join(queries[:3]) if queries else ""
        limit = max(5, budget // 300)

        try:
            if tool_name == "memory-tool":
                from app.tools.memory_tool.services.memory_service import search_memory
                results = await search_memory(
                    project=task_context.get("project", "") if task_context else "",
                    query=query_text,
                    limit=limit,
                )
                return {"items": results}

            elif tool_name == "knowledge-tool":
                from app.services.tool_invoker import invoke_tool
                result = await invoke_tool("knowledge-tool", "knowledge.search", {
                    "query": query_text,
                    "top_k": limit,
                    "search_mode": "hybrid",
                    **(task_context or {}),
                })
                return result.get("output", {"items": []})

            elif tool_name == "code-index":
                from app.services.tool_invoker import invoke_tool
                result = await invoke_tool("code-index", "code.search", {
                    "symbols": queries,
                    "top_k": limit,
                })
                return result.get("output", {"items": []})

            elif tool_name == "asset-tool":
                from app.services.tool_invoker import invoke_tool
                result = await invoke_tool("asset-tool", "asset.search", {
                    "query": query_text,
                    "top_k": limit,
                })
                return result.get("output", {"items": []})

            elif tool_name == "sandbox-tool":
                from app.services.tool_invoker import invoke_tool
                result = await invoke_tool("sandbox-tool", "sandbox.execute", {
                    "code": query_text or "print('test')",
                    "language": "python",
                })
                return result.get("output", {"items": []})

            elif tool_name == "quality-tool":
                from app.services.tool_invoker import invoke_tool
                result = await invoke_tool("quality-tool", "quality.check", {
                    "code": query_text,
                    "filename": "check",
                })
                return result.get("output", {"items": []})

            else:
                return {"items": []}

        except Exception as e:
            logger.warning(f"Retrieve from {tool_name} failed: {e}")
            return {"error": str(e), "items": []}
