from typing import Dict, Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import EvolutionAnalysis


class PatternAnalyzer:
    def __init__(self, db: AsyncSession):
        self.db = db

    def analyze(self, event_type: str, content: str, result: str = None, metadata: Dict = None) -> Dict:
        category = "error"
        error_type = "unknown"
        fix_pattern = ""
        success_pattern = ""
        priority = "medium"
        confidence = 0.7

        if event_type == "success":
            category = "success"
            success_pattern = content[:200]
            priority = "low"
            confidence = 0.8
        elif event_type == "optimization":
            category = "optimization"
            fix_pattern = content[:200]
            priority = "medium"
            confidence = 0.6
        elif event_type == "error":
            category = "error"
            if result:
                if "null" in result.lower() or "none" in result.lower() or "undefined" in result.lower():
                    error_type = "空指针异常"
                    fix_pattern = "添加 null/None/undefined 检查"
                elif "type" in result.lower() or "syntax" in result.lower():
                    error_type = "类型/语法错误"
                    fix_pattern = "检查变量类型和语法"
                elif "import" in result.lower() or "module" in result.lower():
                    error_type = "导入错误"
                    fix_pattern = "检查模块路径和依赖"
                elif "permission" in result.lower() or "access" in result.lower():
                    error_type = "权限错误"
                    fix_pattern = "检查权限配置"
                elif "timeout" in result.lower() or "slow" in result.lower():
                    error_type = "性能问题"
                    fix_pattern = "优化查询或添加缓存"
                else:
                    error_type = "未知错误"
                    fix_pattern = result[:100] if result else ""

            if metadata:
                if metadata.get("priority") == "critical":
                    priority = "high"
                    confidence = 0.9
                elif metadata.get("severity") == "high":
                    priority = "high"
                    confidence = 0.85

        affected_tools = self._infer_tools(event_type, error_type)
        update_type = self._infer_update_type(category)

        return {
            "category": category,
            "error_type": error_type,
            "root_cause": result[:200] if result else "",
            "fix_pattern": fix_pattern,
            "success_pattern": success_pattern,
            "affected_tools": affected_tools,
            "update_type": update_type,
            "priority": priority,
            "confidence": confidence,
        }

    def _infer_tools(self, event_type: str, error_type: str) -> List[str]:
        tools = []
        if event_type == "error":
            tools.append("memory")
            if "权限" in error_type or "路由" in error_type:
                tools.append("skill_router")
        elif event_type == "success":
            tools = ["memory", "asset"]
        elif event_type == "optimization":
            tools = ["knowledge", "code_index"]
        return tools

    def _infer_update_type(self, category: str) -> str:
        if category == "error":
            return "经验"
        elif category == "success":
            return "模板"
        return "文档"

    async def save_analysis(self, event_id: int, analysis: Dict) -> EvolutionAnalysis:
        ana = EvolutionAnalysis(
            event_id=event_id,
            category=analysis.get("category"),
            error_type=analysis.get("error_type"),
            root_cause=analysis.get("root_cause"),
            fix_pattern=analysis.get("fix_pattern"),
            success_pattern=analysis.get("success_pattern"),
            affected_tools=analysis.get("affected_tools", []),
            update_type=analysis.get("update_type"),
            priority=analysis.get("priority"),
            confidence=analysis.get("confidence"),
        )
        self.db.add(ana)
        await self.db.commit()
        await self.db.refresh(ana)
        return ana

    async def get_analyses(self, limit: int = 50) -> list:
        result = await self.db.execute(
            select(EvolutionAnalysis).order_by(EvolutionAnalysis.id.desc()).limit(limit)
        )
        return result.scalars().all()
