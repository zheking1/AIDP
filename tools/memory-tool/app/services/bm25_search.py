import math
from collections import Counter
from typing import List, Dict, Tuple


class BM25Search:
    """BM25全文搜索引擎"""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_lengths: List[int] = []
        self.avg_doc_length: float = 0
        self.doc_freqs = Counter()
        self.idf: Dict[str, float] = {}
        self._indexed = False

    def index(self, documents: List[Dict]):
        self.doc_lengths = [len(doc.get("content", "").split()) for doc in documents]
        self.avg_doc_length = sum(self.doc_lengths) / len(self.doc_lengths) if self.doc_lengths else 1

        self.doc_freqs.clear()
        for doc in documents:
            words = set(doc.get("content", "").lower().split())
            for word in words:
                self.doc_freqs[word] += 1

        n_docs = len(documents)
        self.idf.clear()
        for word, freq in self.doc_freqs.items():
            self.idf[word] = math.log((n_docs - freq + 0.5) / (freq + 0.5) + 1)

        self._indexed = True

    def search(self, query: str, documents: List[Dict], top_k: int = 10) -> List[Tuple[int, float]]:
        if not self._indexed:
            return []

        query_words = query.lower().split()
        scores: List[Tuple[int, float]] = []

        for i, doc in enumerate(documents):
            if i >= len(self.doc_lengths):
                break
            doc_words = doc.get("content", "").lower().split()
            doc_len = self.doc_lengths[i]
            score = 0.0

            for word in query_words:
                if word in doc_words:
                    tf = doc_words.count(word)
                    idf = self.idf.get(word, 0)
                    numerator = tf * (self.k1 + 1)
                    denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_length)
                    score += idf * numerator / denominator

            scores.append((i, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]