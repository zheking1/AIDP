from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LLMConfig


async def add_model(
    session: AsyncSession,
    user_id: UUID,
    name: str,
    endpoint: str,
    api_key: str,
    model_name: str,
    role: str,
    is_default: bool = False,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    timeout_secs: int = 30,
) -> LLMConfig:
    if is_default:
        await session.execute(
            update(LLMConfig).where(
                LLMConfig.role == role, LLMConfig.user_id == user_id
            ).values(is_default=False)
        )

    cfg = LLMConfig(
        name=name,
        endpoint=endpoint,
        api_key=api_key,
        model_name=model_name,
        role=role,
        is_default=is_default,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout_secs=timeout_secs,
        user_id=user_id,
    )
    session.add(cfg)
    await session.commit()
    await session.refresh(cfg)
    return cfg


async def test_model(model: LLMConfig) -> bool:
    try:
        async with httpx.AsyncClient(timeout=model.timeout_secs or 30) as client:
            resp = await client.post(
                f"{model.endpoint}/chat/completions",
                json={
                    "model": model.model_name,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 10,
                },
                headers={"Authorization": f"Bearer {model.api_key}"},
            )
            return resp.is_success
    except Exception:
        return False


async def check_and_update_health(session: AsyncSession, cfg_id: UUID) -> bool:
    cfg = await session.get(LLMConfig, cfg_id)
    if not cfg:
        return False
    healthy = await test_model(cfg)
    cfg.is_healthy = healthy
    await session.commit()
    return healthy


async def list_models(session: AsyncSession, role: str = None, user_id: UUID = None) -> list:
    q = select(LLMConfig)
    if role:
        q = q.where(LLMConfig.role == role)
    if user_id:
        q = q.where(LLMConfig.user_id == user_id)
    result = await session.execute(q.order_by(LLMConfig.role, LLMConfig.name))
    cfgs = result.scalars().all()
    return [{"id": str(c.id), "name": c.name, "role": c.role, "model_name": c.model_name, "is_default": c.is_default, "is_healthy": c.is_healthy} for c in cfgs]
