from typing import Dict, List


class EvolutionRouter:
    RULES = {
        "error": ["memory"],
        "success": ["memory", "asset"],
        "optimization": ["knowledge", "code_index"],
    }

    def route(self, analysis: Dict) -> List[str]:
        category = analysis.get("category", "error")
        targets = list(self.RULES.get(category, ["memory"]))
        error_type = analysis.get("error_type", "")
        if "权限" in error_type or "路由" in error_type:
            if "skill_router" not in targets:
                targets.append("skill_router")
        return targets
