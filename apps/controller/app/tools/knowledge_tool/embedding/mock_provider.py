import hashlib
import math
from typing import Optional

from app.tools.knowledge_tool.embedding.base import EmbeddingVector


class MockEmbeddingProvider:
    """Deterministic mock embedding provider for development and testing."""

    def __init__(self, dimension: int = 384, model: str = "mock-embedding-v1"):
        self._dimension = dimension
        self._model = model

    def embed(self, text: str) -> EmbeddingVector:
        values = self._generate_deterministic_embedding(text)
        return EmbeddingVector(
            values=values,
            model=self._model,
            provider="mock",
            dimension=self._dimension,
        )

    def embed_batch(self, texts: list[str]) -> list[EmbeddingVector]:
        return [self.embed(text) for text in texts]

    def provider_name(self) -> str:
        return "mock"

    def model_name(self) -> str:
        return self._model

    def dimension(self) -> int:
        return self._dimension

    def _generate_deterministic_embedding(self, text: str) -> list[float]:
        hash_bytes = hashlib.sha512(text.encode("utf-8")).digest()
        values = []
        for i in range(self._dimension):
            byte_val = hash_bytes[i % len(hash_bytes)]
            seed = i * 7 + byte_val
            value = math.sin(seed) * 0.5
            values.append(round(value, 6))
        norm = math.sqrt(sum(v * v for v in values))
        if norm > 0:
            values = [v / norm for v in values]
        return values
