import json
import logging
from typing import Optional

import httpx

from app.embedding.base import EmbeddingVector
from app.config import settings

logger = logging.getLogger(__name__)


class OpenAIEmbeddingProvider:
    """OpenAI-compatible embedding provider using httpx for API calls."""

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self._model = model or settings.OPENAI_EMBEDDING_MODEL or "text-embedding-3-small"
        self._api_key = api_key or settings.OPENAI_API_KEY
        self._base_url = base_url or settings.OPENAI_BASE_URL or "https://api.openai.com/v1"
        self._dimension = 1536
        if "large" in self._model:
            self._dimension = 3072
        elif "small" in self._model:
            self._dimension = 1536
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    def embed(self, text: str) -> EmbeddingVector:
        raise NotImplementedError("Use embed_batch for OpenAI provider")

    async def embed_batch(self, texts: list[str]) -> list[EmbeddingVector]:
        client = await self._get_client()
        try:
            response = await client.post(
                "/embeddings",
                json={"model": self._model, "input": texts},
            )
            response.raise_for_status()
            data = response.json()
            return [
                EmbeddingVector(
                    values=item["embedding"],
                    model=self._model,
                    provider="openai",
                    dimension=self._dimension,
                )
                for item in data["data"]
            ]
        except Exception as e:
            logger.error("OpenAI embedding failed: %s", e)
            raise

    def provider_name(self) -> str:
        return "openai"

    def model_name(self) -> str:
        return self._model

    def dimension(self) -> int:
        return self._dimension