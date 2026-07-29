import math
from collections import Counter
from typing import List, Dict, Tuple


class TFIDFSearch:
    """TF-IDF搜索引擎"""

    def __init__(self):
        self.vocabulary: set = set()
        self.idf: Dict[str, float] = {}
        self._indexed = False

    def index(self, documents: List[Dict]):
        self.vocabulary.clear()
        for doc in documents:
            words = doc.get("content", "").lower().split()
            self.vocabulary.update(words)

        n_docs = len(documents)
        self.idf.clear()
        for word in self.vocabulary:
            doc_count = sum(1 for doc in documents if word in doc.get("content", "").lower())
            self.idf[word] = math.log(n_docs / (doc_count + 1))

        self._indexed = True

    def search(self, query: str, documents: List[Dict], top_k: int = 10) -> List[Tuple[int, float]]:
        if not self._indexed:
            return []

        query_words = query.lower().split()
        scores: List[Tuple[int, float]] = []

        for i, doc in enumerate(documents):
            doc_words = doc.get("content", "").lower().split()
            doc_len = len(doc_words)

            tfidf = Counter()
            for word in doc_words:
                tf = doc_words.count(word) / doc_len if doc_len > 0 else 0
                tfidf[word] = tf * self.idf.get(word, 0)

            query_tfidf = Counter()
            for word in query_words:
                query_tfidf[word] = self.idf.get(word, 0)

            dot_product = sum(tfidf.get(w, 0) * query_tfidf.get(w, 0) for w in query_words)
            norm1 = math.sqrt(sum(v * v for v in tfidf.values()))
            norm2 = math.sqrt(sum(v * v for v in query_tfidf.values()))

            score = dot_product / (norm1 * norm2 + 1e-10)
            scores.append((i, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]