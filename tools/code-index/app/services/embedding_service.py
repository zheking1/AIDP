"""代码符号向量化服务 — Controller模型 → 本地 → mock"""

import json
import logging
import os
from typing import List, Optional
import httpx

logger = logging.getLogger(__name__)

CONTROLLER_URL = os.getenv("CONTROLLER_URL", "http://localhost:8883")


class EmbeddingService:
    _model = None
    _controller_model = None

    def __init__(self, model_name: str = None):
        self.model_name = model_name or "BAAI/bge-m3"
        self._dimension = 1024

    def _load_controller(self):
        if EmbeddingService._controller_model is None:
            try:
                resp = httpx.get(f"{CONTROLLER_URL}/api/models/for-task/embedding", timeout=5.0)
                if resp.status_code == 200:
                    model = resp.json().get("model")
                    if model and model.get("api_base") and model["api_base"] != "none":
                        EmbeddingService._controller_model = model
                        self.model_name = model.get("model_name", self.model_name)
                        logger.info("Using controller embedding model: %s", self.model_name)
                    else:
                        EmbeddingService._controller_model = "unavailable"
                else:
                    EmbeddingService._controller_model = "unavailable"
            except Exception as e:
                logger.warning("Failed to fetch embedding model from controller: %s", e)
                EmbeddingService._controller_model = "unavailable"

    def _load_local_model(self):
        if EmbeddingService._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                model_name = "all-MiniLM-L6-v2"
                logger.info("Loading local model: %s", model_name)
                EmbeddingService._model = SentenceTransformer(model_name)
                self._dimension = EmbeddingService._model.get_sentence_embedding_dimension()
                self.model_name = model_name
            except (ImportError, Exception) as e:
                logger.info("Local model not available: %s", e)
                EmbeddingService._model = "unavailable"

    def embed(self, text: str) -> List[float]:
        # Priority 1: Controller API (BGE-M3)
        self._load_controller()
        ctrl = EmbeddingService._controller_model
        if ctrl and ctrl != "unavailable":
            try:
                ep = ctrl.get("api_base")
                api_key = ctrl.get("api_key", "")
                resp = httpx.post(
                    f"{ep}/embeddings",
                    json={"model": ctrl.get("model_name", ""), "input": text},
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=15.0,
                )
                if resp.status_code == 200:
                    return resp.json()["data"][0]["embedding"]
                else:
                    logger.warning("Controller embedding API returned %d", resp.status_code)
            except Exception as e:
                logger.warning("Controller embedding failed: %s", e)

        # Priority 2: Local sentence-transformers
        self._load_local_model()
        if self._model and self._model != "unavailable":
            try:
                return self._model.encode(text, show_progress_bar=False).tolist()
            except Exception as e:
                logger.warning("Local embedding failed: %s", e)

        # Priority 3: Mock
        return self._mock_embed(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed(t) for t in texts]

    def _mock_embed(self, text: str) -> List[float]:
        import hashlib, math
        b = hashlib.sha256(text.encode()).digest()
        return [math.sin(i * 7 + x) * 0.5 for i, x in enumerate(b[:self._dimension])]

    def dimension(self) -> int:
        return self._dimension


_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service