import os
import json
from typing import List, Dict, Optional
import sqlite3
import struct
import mmap
import math


class VectorDB:
    """Simple vector DB using SQLite + cosine similarity"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.join(os.path.dirname(__file__), "..", "data", "vectors.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vectors (
                id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                embedding BLOB NOT NULL,
                dimension INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def upsert(self, doc_id: str, embedding: List[float]):
        dim = len(embedding)
        blob = struct.pack(f'{dim}f', *embedding)
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO vectors (id, doc_id, embedding, dimension)
            VALUES (?, ?, ?, ?)
        """, (doc_id, doc_id, blob, dim))
        conn.commit()
        conn.close()

    def search(self, query_embedding: List[float], top_k: int = 10) -> List[Dict]:
        dim = len(query_embedding)
        query_blob = struct.pack(f'{dim}f', *query_embedding)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT id, doc_id, embedding FROM vectors WHERE dimension = ?",
            (dim,)
        )
        results = []
        for row in cursor:
            vec_blob = row[2]
            vec = list(struct.unpack(f'{dim}f', vec_blob))
            sim = self._cosine_similarity(query_embedding, vec)
            results.append({"id": row[0], "doc_id": row[1], "score": sim})
        conn.close()
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
