import logging
from typing import Dict, List

import httpx

logger = logging.getLogger(__name__)


class SkillMatcher:
    """Stage 3: 调用 skill-router 进行技能匹配"""

    async def match(self, task: str, domain: str, knowledge_context: dict = None) -> list:
        try:
            payload = {
                "trace_id": "",
                "capability": "resolve_task",
                "context": {},
                "input": {
                    "task": task,
                    "mode": "auto",
                    "top_k": 3,
                    "api_key": "sk-1234567890",
                },
            }

            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(
                    "http://127.0.0.1:8788/tool/invoke",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )

                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("success") and data.get("output"):
                        output = data["output"]
                        if isinstance(output, dict):
                            skills = output.get("data", {}).get("skills", [])
                            return skills[:3]
                    return []
                return []
        except Exception as e:
            logger.warning(f"Skill matching failed: {e}")
            return []