from dataclasses import dataclass
from typing import Protocol


@dataclass
class EmbeddingVector:
    values: list[float]
    model: str
    provider: str
    dimension: int


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> EmbeddingVector: ...
    def embed_batch(self, texts: list[str]) -> list[EmbeddingVector]: ...
    def provider_name(self) -> str: ...
    def model_name(self) -> str: ...
    def dimension(self) -> int: ...
