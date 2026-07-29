import os
import httpx
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, base_url: str = None, api_key: str = None, model: str = None):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self._initialized = bool(base_url)

    async def _ensure_config(self):
        if self._initialized and self.base_url:
            return
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get("http://localhost:8883/api/models/for-task/chat")
            if resp.status_code == 200:
                cfg = resp.json().get("model", {})
                if cfg:
                    self.base_url = cfg.get("api_base")
                    self.api_key = cfg.get("api_key")
                    self.model = cfg.get("model_name")
                    self._initialized = True
                    logger.info("LLM config from Controller: %s @ %s", self.model, self.base_url)
                    return
        raise RuntimeError("Failed to load model config from Controller")

    async def call(self, prompt: str, max_tokens: int = 1024) -> Optional[str]:
        await self._ensure_config()
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens,
                        "temperature": 0.3,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            except Exception:
                return None
