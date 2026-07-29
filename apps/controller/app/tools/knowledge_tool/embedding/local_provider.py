import logging
from typing import Optional

from app.tools.knowledge_tool.embedding.base import EmbeddingVector
from app.tools.knowledge_tool.config import settings

logger = logging.getLogger(__name__)


class LocalEmbeddingProvider:
    """Local sentence-transformers embedding provider with lazy loading."""

    _model_instance = None

    def __init__(
        self,
        model_name: Optional[str] = None,
    ):
        self._model_name = model_name or settings.LOCAL_EMBEDDING_MODEL or "all-MiniLM-L6-v2"
        self._dimension = 384

    def _load_model(self):
        if LocalEmbeddingProvider._model_instance is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info("Loading local embedding model: %s", self._model_name)
                LocalEmbeddingProvider._model_instance = SentenceTransformer(self._model_name)
                self._dimension = LocalEmbeddingProvider._model_instance.get_sentence_embedding_dimension()
            except ImportError:
                logger.error(
                    "sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers"
                )
                raise

    def embed(self, text: str) -> EmbeddingVector:
        self._load_model()
        embedding = LocalEmbeddingProvider._model_instance.encode(
            text, show_progress_bar=False
        )
        return EmbeddingVector(
            values=embedding.tolist(),
            model=self._model_name,
            provider="local",
            dimension=self._dimension,
        )

    def embed_batch(self, texts: list[str]) -> list[EmbeddingVector]:
        self._load_model()
        embeddings = LocalEmbeddingProvider._model_instance.encode(
            texts, show_progress_bar=False
        )
        return [
            EmbeddingVector(
                values=emb.tolist(),
                model=self._model_name,
                provider="local",
                dimension=self._dimension,
            )
            for emb in embeddings
        ]

    def provider_name(self) -> str:
        return "local"

    def model_name(self) -> str:
        return self._model_name

    def dimension(self) -> int:
        if LocalEmbeddingProvider._model_instance is not None:
            self._dimension = LocalEmbeddingProvider._model_instance.get_sentence_embedding_dimension()
        return self._dimension