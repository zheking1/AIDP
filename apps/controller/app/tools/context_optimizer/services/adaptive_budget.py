import json
from typing import Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.tools.context_optimizer.services.llm_client import LLMClient
from app.tools.context_optimizer.services.requirement_analyzer import RequirementAnalyzer
from app.tools.context_optimizer.services.feedback_learner import FeedbackLearner


class AdaptiveBudgetAllocator:
    def __init__(self, db: AsyncSession, llm_client: LLMClient = None):
        self.db = db
        self.llm = llm_client or LLMClient()
        self.analyzer = RequirementAnalyzer()
        self.learner = FeedbackLearner()

    async def allocate(self, task: str, existing_content: List[str] = None,
                       total_budget: int = 8000) -> Dict:
        plan = self.analyzer.analyze(task, existing_content)

        if self.llm:
            llm_enhanced = await self._llm_enhance(task, plan)
            if llm_enhanced:
                plan = llm_enhanced

        allocation = {}
        for tool in plan.get("required_tools", []):
            base = int(total_budget * 0.3)
            adjusted = int(base * self.learner.get_adjusted_priority(tool))
            allocation[tool] = max(100, adjusted)

        remaining = total_budget - sum(allocation.values())
        return {
            "plan": plan,
            "allocation": allocation,
            "total_budget": total_budget,
            "remaining": remaining,
        }

    async def _llm_enhance(self, task: str, plan: Dict) -> Optional[Dict]:
        prompt = f"""Analyze this task and return a retrieval plan as JSON:

Task: {task}
Existing plan: {str(plan)[:500]}

Return JSON with: intent, key_entities, required_tools, search_queries, priority
"""
        result = await self.llm.call(prompt, max_tokens=512)
        if result:
            try:
                return json.loads(result)
            except:
                return None
        return None

    async def record_feedback(self, task: str, result: Dict, feedback: str) -> Dict:
        return await self.learner.learn_from_feedback(task, result, feedback)
