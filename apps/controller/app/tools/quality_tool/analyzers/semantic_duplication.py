from typing import Dict, List
import math


class SemanticDuplicationDetector:
    """语义重复检测器"""

    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold

    def detect(self, code_blocks: List[Dict]) -> List[Dict]:
        if len(code_blocks) < 2:
            return []

        vectors = [self._text_to_vector(block.get("content", "")) for block in code_blocks]

        clusters = []
        n = len(code_blocks)
        visited = set()

        for i in range(n):
            if i in visited:
                continue
            cluster = [i]
            visited.add(i)
            for j in range(i + 1, n):
                if j in visited:
                    continue
                sim = self._cosine_similarity(vectors[i], vectors[j])
                if sim >= self.similarity_threshold:
                    cluster.append(j)
                    visited.add(j)

            if len(cluster) > 1:
                sims = [self._cosine_similarity(vectors[cluster[0]], vectors[j]) for j in cluster[1:]]
                avg_sim = sum(sims) / len(sims)
                clusters.append({
                    "blocks": [code_blocks[idx] for idx in cluster],
                    "similarity": round(avg_sim, 2),
                    "count": len(cluster),
                    "suggestion": "考虑将重复代码提取为公共函数",
                })

        return clusters

    def _text_to_vector(self, text: str) -> Dict[str, int]:
        words = text.lower().split()
        return {w: words.count(w) for w in set(words)}

    def _cosine_similarity(self, vec1: Dict[str, int], vec2: Dict[str, int]) -> float:
        all_keys = set(vec1.keys()) | set(vec2.keys())
        dot = sum(vec1.get(k, 0) * vec2.get(k, 0) for k in all_keys)
        n1 = math.sqrt(sum(v * v for v in vec1.values()))
        n2 = math.sqrt(sum(v * v for v in vec2.values()))
        return dot / (n1 * n2 + 1e-10)