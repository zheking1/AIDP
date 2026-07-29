from typing import Dict, List, Optional
import json
from app.tools.evolution_engine.services.llm_client import LLMClient
from app.tools.evolution_engine.services.pattern_analyzer import PatternAnalyzer


class LLMPatternAnalyzer:
    def __init__(self, db=None, llm_client: LLMClient = None):
        self.db = db
        self.llm = llm_client or LLMClient()
        self.rule_analyzer = PatternAnalyzer(db) if db else None

    async def analyze(self, event_type: str, content: str, result: str = None,
                      metadata: Dict = None) -> Dict:
        if self.llm:
            llm_result = await self._llm_analyze(event_type, content, result, metadata)
            if llm_result:
                return llm_result

        if self.rule_analyzer:
            return self.rule_analyzer.analyze(event_type, content, result, metadata)

        return {
            "category": event_type,
            "error_type": "unknown",
            "root_cause": result or "",
            "fix_pattern": "",
            "success_pattern": "",
            "affected_tools": ["memory"],
            "update_type": "经验",
            "priority": "medium",
            "confidence": 0.5,
        }

    async def _llm_analyze(self, event_type: str, content: str, result: str,
                           metadata: Dict) -> Optional[Dict]:
        prompt = f"""Analyze this programming event and return JSON:

Event type: {event_type}
Content: {content[:1000]}
Result: {result[:500] if result else 'N/A'}
Metadata: {json.dumps(metadata or {})}

Return JSON:
{{
    "category": "error/success/optimization",
    "error_type": "specific error type or N/A",
    "root_cause": "brief root cause",
    "fix_pattern": "how to fix or pattern if success",
    "success_pattern": "if success, what worked",
    "affected_tools": ["tool1", "tool2"],
    "update_type": "经验/模板/文档",
    "priority": "high/medium/low",
    "confidence": 0.85
}}
"""
        result_text = await self.llm.call(prompt, max_tokens=512)
        if result_text:
            try:
                return json.loads(result_text)
            except:
                return None
        return None

    async def batch_analyze(self, events: List[Dict]) -> List[Dict]:
        results = []
        for event in events:
            analysis = await self.analyze(
                event_type=event.get("type", "error"),
                content=event.get("content", ""),
                result=event.get("result"),
                metadata=event.get("metadata", {}),
            )
            results.append(analysis)
        return results

    async def save_analysis(self, event_id: int, analysis: Dict):
        if self.rule_analyzer:
            return await self.rule_analyzer.save_analysis(event_id, analysis)
        from app.tools.evolution_engine.db.models import EvolutionAnalysis
        ana = EvolutionAnalysis(event_id=event_id, **analysis)
        self.db.add(ana)
        await self.db.commit()
        await self.db.refresh(ana)
        return ana
