import json
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.tools.importer_tool.config import settings


class RedactionEngine:
    def __init__(self, regex_patterns: list[str] | None = None):
        self._compiled: list[re.Pattern] = []
        if regex_patterns:
            for p in regex_patterns:
                try:
                    self._compiled.append(re.compile(p, re.IGNORECASE))
                except re.error:
                    pass

    def redact(self, text: str) -> str:
        if not self._compiled:
            return text
        result = text
        for i, pattern in enumerate(self._compiled):
            result = pattern.sub(f"[REDACTED_{i}]", result)
        return result

    @staticmethod
    def default_patterns() -> list[str]:
        return [
            r"(?i)(?:sk-[a-zA-Z0-9]{20,})",
            r"(?i)(?:gh[ps]_[a-zA-Z0-9]{36,})",
            r"(?i)(?:AKIA[0-9A-Z]{16})",
            r"(?i)(?:-----BEGIN\s*(?:RSA\s+)?PRIVATE\s+KEY-----)",
            r"(?i)(?:password[=:]\s*\S+)",
            r"(?i)(?:api[_-]?key[=:]\s*\S+)",
            r"(?i)(?:secret[=:]\s*\S+)",
            r"(?i)(?:token[=:]\s*\S+)",
            r"(?:[\w.+-]+@[\w-]+\.[\w.-]+)",
        ]


class AIModelCaller:
    def __init__(self, api_base: str | None = None, api_key: str | None = None):
        self.api_base = (api_base or settings.AI_API_BASE).rstrip("/")
        self.api_key = api_key or settings.AI_API_KEY

    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": model or settings.AI_MODEL,
            "messages": messages,
            "max_tokens": max_tokens or settings.AI_MAX_TOKENS,
            "temperature": temperature if temperature is not None else settings.AI_TEMPERATURE,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{self.api_base}/chat/completions", json=body, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError(f"AI API error {resp.status_code}: {resp.text}")
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    async def review_content(
        self,
        content: str,
        entity_type: str,
        model_config: Optional["PromotionReviewConfig"] = None,
    ) -> dict:
        api_base = model_config.api_base if model_config else self.api_base
        api_key = model_config.api_key if model_config and model_config.api_key else self.api_key
        model = model_config.model_name if model_config else settings.AI_MODEL
        max_tokens = model_config.max_tokens if model_config else settings.AI_MAX_TOKENS
        temperature = model_config.temperature if model_config else settings.AI_TEMPERATURE

        caller = AIModelCaller(api_base=api_base, api_key=api_key)

        prompt = f"""You are a content promotion reviewer. Review the following {entity_type} content for promotion from personal to global scope.

Evaluate these criteria:
1. **Quality** - Is the content complete, well-structured, and professional?
2. **Security** - Does it contain secrets, credentials, or sensitive data?
3. **Generality** - Is it universally applicable (not project-specific)?
4. **Completeness** - Does it have sufficient metadata (tags, category, description)?
5. **Risk** - Are there any risky patterns (eval, exec, dangerous permissions)?

Respond in JSON format:
{{
    "passed": true/false,
    "score": <0-100>,
    "quality_score": <0-100>,
    "security_score": <0-100>,
    "generality_score": <0-100>,
    "completeness_score": <0-100>,
    "risk_score": <0-100>,
    "strengths": ["..."],
    "weaknesses": ["..."],
    "redacted_items": ["..."],
    "recommendation": "promote"|"reject"|"revise",
    "summary": "..."
}}"""

        result = await caller.chat(
            messages=[
                {"role": "system", "content": "You are a content review assistant. Respond only with valid JSON."},
                {"role": "user", "content": f"{prompt}\n\n--- Content ---\n{content}"},
            ],
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        result = re.sub(r"^```(?:json)?\s*", "", result.strip())
        result = re.sub(r"\s*```$", "", result)
        return json.loads(result)


class PromotionReviewService:
    def __init__(self, ai_caller: AIModelCaller | None = None):
        self.ai = ai_caller or AIModelCaller()

    async def submit_for_review(
        self,
        entity_type: str,
        entity_id: str,
        content: str,
        from_scope: str = "personal",
        triggered_by: str = "system",
        config: Optional["PromotionReviewConfig"] = None,
    ) -> dict:
        redactor = RedactionEngine(
            json.loads(config.redact_regexes) if config and config.redact_regexes
            else RedactionEngine.default_patterns()
        )
        redacted_content = redactor.redact(content)

        review = await self.ai.review_content(redacted_content, entity_type, model_config=config)

        action = "reviewed"
        if review.get("passed") and review.get("recommendation") == "promote":
            action = "promoted"
        elif review.get("recommendation") == "reject":
            action = "rejected"

        return {
            "action": action,
            "from_scope": from_scope,
            "to_scope": "global" if action == "promoted" else from_scope,
            "review_report": json.dumps(review, ensure_ascii=False),
            "triggered_by": triggered_by,
        }

    async def execute_promotion(
        self,
        entity_type: str,
        entity_id: str,
        controller_base_url: str,
    ) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.put(
                f"{controller_base_url}/api/{entity_type}s/{entity_id}",
                json={
                    "scope": "global",
                    "promotion_status": "promoted",
                    "promotion_promoted_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        if resp.status_code not in (200, 204):
            raise RuntimeError(f"Controller promotion failed: {resp.status_code} {resp.text}")
        return resp.json() if resp.text else {"status": "promoted"}


# Import at bottom to avoid circular dependency
from app.tools.importer_tool.db.models import PromotionReviewConfig  # noqa: E402, F401
