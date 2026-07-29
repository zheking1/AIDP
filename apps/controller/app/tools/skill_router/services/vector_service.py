from typing import Optional
import httpx
from app.tools.skill_router.config import settings


async def _get_chat_config():
    from app.tools.skill_router.model_client import get_chat_model
    model = await get_chat_model()
    if model:
        return {
            "endpoint": model.get("api_base", ""),
            "model": model.get("model_name", ""),
            "api_key": model.get("api_key", ""),
        }
    raise RuntimeError("No chat model configured in Controller")


async def _get_embed_config():
    from app.tools.skill_router.model_client import get_embedding_model
    model = await get_embedding_model()
    if model:
        ep = model.get("api_base") or model.get("endpoint")
        if not ep or ep == "none":
            return None
        return {
            "endpoint": ep,
            "model": model.get("model_name", ""),
            "api_key": model.get("api_key", ""),
        }
    return None


async def generate_embedding(text: str) -> Optional[list[float]]:
    try:
        cfg = await _get_embed_config()
        if not cfg:
            return None
        async with httpx.AsyncClient(timeout=settings.embedding_timeout) as client:
            resp = await client.post(
                f"{cfg['endpoint']}/embeddings",
                json={"model": cfg["model"], "input": text},
                headers={"Authorization": f"Bearer {cfg['api_key']}"},
            )
            resp.raise_for_status()
            return resp.json()["data"][0]["embedding"]
    except Exception:
        return None


async def analyze_intent(task: str, chat_history: Optional[list] = None) -> Optional[dict]:
    try:
        cfg = await _get_chat_config()
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
                f"{cfg['endpoint']}/chat/completions",
                json={
                    "model": cfg["model"],
                    "messages": [{"role": "system", "content": system_prompt}, *messages],
                    "temperature": 0.3,
                    "max_tokens": 500,
                },
                headers={"Authorization": f"Bearer {cfg['api_key']}"},
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
    # 优先使用 Controller 重排模型 API (cross-encoder)
    result = await _rerank_with_api(task, skills, intent)
    if result:
        return result
    # 降级为 LLM prompt 重排
    return await _rerank_with_llm(task, skills, intent)


async def _rerank_with_api(task: str, skills: list[dict], intent: Optional[dict] = None) -> Optional[list[dict]]:
    try:
        from app.tools.skill_router.model_client import get_rerank_model
        model = await get_rerank_model()
        if not model:
            return None
        ep = model.get("api_base", "")
        docs = [f"[{s.get('name','')}] {s.get('content','')[:500]}" for s in skills]
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                ep,
                json={
                    "model": model.get("model_name", ""),
                    "query": task,
                    "documents": docs,
                },
                headers={"Authorization": f"Bearer {model.get('api_key', '')}"},
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            return [
                {"id": str(skills[r["index"]]["id"]),
                 "name": skills[r["index"]]["name"],
                 "relevance": r.get("relevance_score", 0),
                 "is_primary": r.get("relevance_score", 0) > 0.5}
                for r in sorted(results, key=lambda x: x.get("relevance_score", 0), reverse=True)
            ]
    except Exception:
        return None


async def _rerank_with_llm(task: str, skills: list[dict], intent: Optional[dict] = None) -> Optional[list[dict]]:
    from app.tools.skill_router.db.init_db import get_session
    from app.tools.skill_router.db.models import LLMConfig
    from sqlalchemy import select
    async with get_session() as db:
        result = await db.execute(
            select(LLMConfig).where(LLMConfig.role == "ranker", LLMConfig.is_healthy == True)
        )
        model = result.scalars().first()
    if not model:
        cfg = await _get_chat_config()
    else:
        cfg = {"endpoint": model.endpoint, "model": model.model_name, "api_key": model.api_key}
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
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{cfg['endpoint']}/chat/completions",
                json={
                    "model": cfg["model"],
                    "messages": [
                        {"role": "system", "content": RE_RANK_PROMPT},
                        {"role": "user", "content": f"Task: {task}\n\n{intent_summary}Skills:\n{skills_input}"},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 2000,
                },
                headers={"Authorization": f"Bearer {cfg['api_key']}"},
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            import json as _json
            rerank_result = _json.loads(content)
            return rerank_result if isinstance(rerank_result, list) else None
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
            return len(resp.json()["data"][0]["embedding"])
    except Exception:
        return None