from typing import List, Dict
from sqlalchemy import select
from app.db.models import MemoryEntry


def _get_session():
    from app.db.models import async_session
    return async_session()


class MemoryConsolidator:
    """记忆整理器：合并相似记忆"""

    async def consolidate(self, project: str, similarity_threshold: float = 0.85) -> Dict:
        async with _get_session() as session:
            result = await session.execute(
                select(MemoryEntry).where(MemoryEntry.project == project)
            )
            memories = result.scalars().all()

        if len(memories) < 2:
            return {"total_memories": len(memories), "clusters_found": 0, "memories_merged": 0}

        memory_dicts = [{  "id": m.id, "title": m.title or "", "content": m.content or "",
            "category": m.category, "created_at": m.created_at,
        } for m in memories]

        clusters = self._cluster_similar(memory_dicts, similarity_threshold)
        merged_count = sum(len(c) - 1 for c in clusters)

        cluster_details = []
        for cluster in clusters:
            if len(cluster) > 1:
                cluster_details.append({
                    "primary": cluster[0]["title"],
                    "similarity": round(self._cluster_similarity(cluster), 2),
                    "merged": [m["title"] for m in cluster[1:]],
                })

        return {
            "total_memories": len(memories),
            "clusters_found": len(cluster_details),
            "memories_merged": merged_count,
            "clusters": cluster_details,
        }

    def _cluster_similar(self, memories: List[Dict], threshold: float) -> List[List[Dict]]:
        n = len(memories)
        visited = set()
        clusters = []

        for i in range(n):
            if i in visited:
                continue
            cluster = [memories[i]]
            visited.add(i)
            for j in range(i + 1, n):
                if j in visited:
                    continue
                sim = self._compute_similarity(memories[i], memories[j])
                if sim >= threshold:
                    cluster.append(memories[j])
                    visited.add(j)
            clusters.append(cluster)

        return clusters

    def _compute_similarity(self, a: Dict, b: Dict) -> float:
        words_a = set((a.get("title", "") + " " + a.get("content", "")).lower().split())
        words_b = set((b.get("title", "") + " " + b.get("content", "")).lower().split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union) if union else 0.0

    def _cluster_similarity(self, cluster: List[Dict]) -> float:
        if len(cluster) < 2:
            return 0.0
        first = cluster[0]
        sims = []
        for other in cluster[1:]:
            sims.append(self._compute_similarity(first, other))
        return sum(sims) / len(sims) if sims else 0.0