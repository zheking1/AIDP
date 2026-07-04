import os
import httpx
import json
from typing import Dict, Optional


class LLMClient:
    def __init__(self, base_url: str = None, api_key: str = None, model: str = None):
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "http://127.0.0.1:11434/v1")
        self.api_key = api_key or os.getenv("LLM_API_KEY", "sk-xxx")
        self.model = model or os.getenv("LLM_MODEL", "qwen2.5:7b")

    async def call(self, prompt: str, max_tokens: int = 1024) -> Optional[str]:
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
            except Exception as e:
                return None

    async def summarize(self, content: str, max_tokens: int = 256) -> Optional[str]:
        prompt = f"Summarize the following content concisely (max {max_tokens} tokens):\n\n{content[:4000]}"
        return await self.call(prompt, max_tokens)

    async def extract_entities(self, text: str) -> Optional[str]:
        prompt = f"Extract key entities (class names, function names, concepts) from:\n\n{text[:2000]}\n\nReturn as JSON array."
        return await self.call(prompt, max_tokens=512)
