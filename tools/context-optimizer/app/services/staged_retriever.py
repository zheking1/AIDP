import asyncio
import logging
from typing import Dict, List

import httpx

logger = logging.getLogger(__name__)

TOOL_ENDPOINTS = {
    "memory-tool": "http://127.0.0.1:18085",
    "knowledge-tool": "http://127.0.0.1:18081",
    "code-index": "http://127.0.0.1:18086",
    "asset-tool": "http://127.0.0.1:18082",
    "sandbox-tool": "http://127.0.0.1:18083",
    "quality-tool": "http://127.0.0.1:18084",
}

CAPABILITY_MAP = {
    "memory-tool": "memory.search",
    "knowledge-tool": "knowledge.search",
    "code-index": "code.search",
    "asset-tool": "asset.search",
    "sandbox-tool": "sandbox.execute",
    "quality-tool": "quality.check",
}


class StagedRetriever:
    """Stage 2: 根据 Stage 1 的输出并行调用各工具"""

    async def retrieve(
        self,
        required_tools: List[str],
        search_queries: Dict[str, List[str]],
        budget_hints: Dict[str, int],
    ) -> dict:
        results = {}
        tasks = []

        for tool_name in required_tools:
            if tool_name not in TOOL_ENDPOINTS:
                continue
            queries = search_queries.get(tool_name, [])
            budget = budget_hints.get(tool_name, 2000)
            tasks.append(self._retrieve_from_tool(tool_name, queries, budget))

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

    async def _retrieve_from_tool(self, tool_name: str, queries: List[str], budget: int) -> dict:
        endpoint = TOOL_ENDPOINTS[tool_name]
        capability = CAPABILITY_MAP.get(tool_name, f"{tool_name}.search")

        query_text = " ".join(queries[:3]) if queries else ""
        limit = max(5, budget // 300)

        try:
            payload = {
                "trace_id": "",
                "capability": capability,
                "context": {},
                "input": {},
            }

            if tool_name == "memory-tool":
                payload["input"] = {"project": query_text or "default", "query": query_text, "limit": limit}
            elif tool_name == "knowledge-tool":
                payload["input"] = {"query": query_text, "top_k": limit}
            elif tool_name == "code-index":
                payload["input"] = {"symbols": queries, "top_k": limit}
            elif tool_name == "asset-tool":
                payload["input"] = {"query": query_text, "top_k": limit}
            elif tool_name == "sandbox-tool":
                payload["input"] = {"code": query_text or "print('test')", "language": "python"}
            elif tool_name == "quality-tool":
                payload["input"] = {"code": query_text, "filename": "check"}
            else:
                payload["input"] = {"query": query_text, "top_k": limit}

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{endpoint}/tool/invoke",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )

                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("success") and data.get("output"):
                        return data["output"]
                    return data
                return {"error": f"HTTP {resp.status_code}", "items": []}
        except Exception as e:
            logger.warning(f"Retrieve from {tool_name} failed: {e}")
            return {"error": str(e), "items": []}