import json
import logging
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.code_index.db.models import Node, NodeEmbedding
from app.tools.code_index.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


class NodeEmbeddingStore:
    """节点向量存储和搜索服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = get_embedding_service()

    def _build_embedding_input(self, node: Node) -> str:
        parts = [f"name: {node.name}", f"type: {node.node_type}"]
        if node.signature:
            parts.append(f"signature: {node.signature}")
        if node.docstring:
            parts.append(f"docstring: {node.docstring}")
        if node.return_type:
            parts.append(f"return_type: {node.return_type}")
        if node.file_path:
            parts.append(f"file: {node.file_path}")
        return "\n".join(parts)

    async def compute_embedding(self, node: Node) -> None:
        text = self._build_embedding_input(node)
        content_hash = str(hash(text))
        embedding = self.embedding_service.embed(text)
        store = NodeEmbedding(
            node_id=node.id,
            project_id=node.project_id,
            embedding=json.dumps(embedding),
            embedding_model=self.embedding_service.model_name,
            content_hash=content_hash,
        )
        self.db.add(store)

    async def compute_batch(self, nodes: List[Node]) -> None:
        texts = [self._build_embedding_input(n) for n in nodes]
        embeddings = self.embedding_service.embed_batch(texts)
        for node, emb in zip(nodes, embeddings):
            content_hash = str(hash(self._build_embedding_input(node)))
            store = NodeEmbedding(
                node_id=node.id,
                project_id=node.project_id,
                embedding=json.dumps(emb),
                embedding_model=self.embedding_service.model_name,
                content_hash=content_hash,
            )
            self.db.add(store)

    async def vector_search(self, query: str, project_id: int, top_k: int = 20) -> List[Tuple[int, float]]:
        query_embedding = self.embedding_service.embed(query)
        result = await self.db.execute(
            select(NodeEmbedding).where(NodeEmbedding.project_id == project_id)
        )
        embeddings = result.scalars().all()
        scored = []
        for emb in embeddings:
            try:
                stored = json.loads(emb.embedding) if isinstance(emb.embedding, str) else emb.embedding
                similarity = self._cosine_similarity(query_embedding, stored)
                scored.append((emb.node_id, similarity))
            except Exception:
                pass
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(x * x for x in b) ** 0.5
        return dot / (na * nb + 1e-10)

    async def delete_by_node(self, node_id: int) -> None:
        await self.db.execute(
            delete(NodeEmbedding).where(NodeEmbedding.node_id == node_id)
        )