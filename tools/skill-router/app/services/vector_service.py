from typing import Optional

import httpx

from app.config import settings


async def generate_embedding(text: str) -> Optional[list[float]]:
    try:
        async with httpx.AsyncClient(timeout=settings.embedding_timeout) as client:
            resp = await client.post(
                f"{settings.embedding_endpoint}/embeddings",
                json={
                    "model": settings.embedding_model,
                    "input": text,
                },
                headers={"Authorization": f"Bearer {settings.embedding_api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()
            return data["data"][0]["embedding"]
    except Exception:
        return None


async def analyze_intent(task: str, chat_history: Optional[list] = None) -> Optional[dict]:
    try:
        messages = []
        if chat_history:
            for msg in chat_history:
                messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
        messages.append({"role": "user", "content": task})

        system_prompt = (
            "Analyze the following task. Output JSON with keys: "
            "primary_intent (str), secondary_intent (str or null), domain (str), "
            "tags_needed (list of str), secondary_tags (list of str), complexity (low/medium/high), "
            "is_compound (bool). "
            "If the task has multiple distinct goals, set is_compound=true and provide secondary_intent and secondary_tags."
        )

        async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
            resp = await client.post(
                f"{settings.llm_endpoint}/chat/completions",
                json={
                    "model": settings.llm_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        *messages,
                    ],
                    "temperature": 0.3,
                    "max_tokens": 500,
                },
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            import json as _json
            return _json.loads(content)
    except Exception:
        return None


RE_RANK_PROMPT = (
    "Given task, intent analysis, and skill candidates, rate each skill's relevance (0.0-1.0) and identify if it's primary or secondary. "
    "Output JSON: [{\"id\": \"...\", \"relevance\": 0.95, \"reason\": \"...\", \"is_primary\": true/false}]. "
    "Primary skills directly address the primary_intent. Secondary skills support the secondary_intent or complement the primary. "
    "If intent.is_compound=true, allocate ~70% score budget to primary skills, ~30% to secondary. "
    "Return empty list if none relevant."
)


async def rerank_skills(task: str, skills: list[dict], intent: Optional[dict] = None) -> Optional[list[dict]]:
    from app.db.init_db import get_session
    from app.db.models import LLMConfig
    from sqlalchemy import select
    async with get_session() as db:
        result = await db.execute(
            select(LLMConfig).where(LLMConfig.role == "reranker", LLMConfig.is_healthy == True)
        )
        model = result.scalars().first()
    if not model:
        return None
    try:
        skills_input = [{"id": str(s["id"]), "name": s["name"], "tags": s.get("tags", []), "content": s["content"][:500]} for s in skills]
        intent_summary = ""
        if intent:
            primary = intent.get("primary_intent", "")
            secondary = intent.get("secondary_intent")
            compound = intent.get("is_compound", False)
            intent_summary = f"Primary intent: {primary}\n"
            if compound and secondary:
                intent_summary += f"Secondary intent: {secondary} (compound task)\n"
            intent_summary += f"Domain: {intent.get('domain', '')}\n"
            intent_summary += f"Complexity: {intent.get('complexity', 'medium')}\n"
        async with httpx.AsyncClient(timeout=model.timeout_secs or 30) as client:
            resp = await client.post(
                f"{model.endpoint}/chat/completions",
                json={
                    "model": model.model_name,
                    "messages": [
                        {"role": "system", "content": RE_RANK_PROMPT},
                        {"role": "user", "content": f"Task: {task}\n\n{intent_summary}Skills:\n{skills_input}"},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 2000,
                },
                headers={"Authorization": f"Bearer {model.api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            import json as _json
            rerank_result = _json.loads(content)
            if isinstance(rerank_result, list):
                return rerank_result
            return None
    except Exception:
        return None


async def detect_embedding_dim(endpoint: str, api_key: str, model: str) -> Optional[int]:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{endpoint}/embeddings",
                json={"model": model, "input": "test"},
                headers={"Authorization": f"Bearer {api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()
            emb = data["data"][0]["embedding"]
            return len(emb)
    except Exception:
        return None
