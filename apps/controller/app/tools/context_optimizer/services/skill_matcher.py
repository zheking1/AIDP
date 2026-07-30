import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class SkillMatcher:
    """Stage 3: 调用 skill-router 进行技能匹配"""

    async def match(self, task: str, domain: str, knowledge_context: dict = None) -> list:
        try:
            from app.tools.skill_router.services.resolve_service import resolve_task

            result = await resolve_task(
                task=task,
                mode="auto",
                hint_tags=[],
            )

            if result and isinstance(result, dict):
                skills = result.get("skills", [])
                return skills[:3]
            return []
        except Exception as e:
            logger.warning(f"Skill matching failed: {e}")
            return []
