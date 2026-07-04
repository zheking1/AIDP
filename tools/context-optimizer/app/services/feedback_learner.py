from typing import Dict, List, Optional
from app.services.llm_client import LLMClient


class FeedbackLearner:
    def __init__(self):
        self.learning_log: List[Dict] = []
        self.budget_adjustments: Dict[str, float] = {}

    async def learn_from_feedback(self, task: str, result: Dict, feedback: str) -> Dict:
        self.learning_log.append({
            "task": task,
            "result": result,
            "feedback": feedback,
            "timestamp": "now",
        })
        positive = "good" in feedback.lower() or "correct" in feedback.lower()
        negative = "bad" in feedback.lower() or "wrong" in feedback.lower()

        if negative:
            for tool in result.get("required_tools", []):
                current = self.budget_adjustments.get(tool, 1.0)
                self.budget_adjustments[tool] = max(0.5, current * 0.9)

        if positive:
            for tool in result.get("required_tools", []):
                current = self.budget_adjustments.get(tool, 1.0)
                self.budget_adjustments[tool] = min(2.0, current * 1.05)

        return {"learned": True, "adjustments": dict(self.budget_adjustments)}

    def get_adjusted_priority(self, tool: str) -> float:
        return self.budget_adjustments.get(tool, 1.0)
