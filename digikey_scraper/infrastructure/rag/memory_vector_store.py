"""In-memory cosine-similarity vector store (offline default).

Implements the VectorStore port. A Qdrant adapter implements the same port for
production later. Vectors are assumed L2-normalized (HashingEmbedder does this),
so cosine similarity reduces to a dot product.
"""

from __future__ import annotations


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=False))


class InMemoryVectorStore:
    def __init__(self) -> None:
        self._ids: list[str] = []
        self._vectors: list[list[float]] = []
        self._payloads: list[dict] = []

    def add(self, ids: list[str], vectors: list[list[float]], payloads: list[dict]) -> None:
        if not (len(ids) == len(vectors) == len(payloads)):
            raise ValueError("ids, vectors, payloads must be the same length")
        for i, v, p in zip(ids, vectors, payloads, strict=True):
            if i in self._ids:  # upsert
                pos = self._ids.index(i)
                self._vectors[pos] = v
                self._payloads[pos] = p
            else:
                self._ids.append(i)
                self._vectors.append(v)
                self._payloads.append(p)

    def search(self, vector: list[float], top_k: int) -> list[tuple[str, float, dict]]:
        scored = [
            (self._ids[i], _dot(vector, self._vectors[i]), self._payloads[i])
            for i in range(len(self._ids))
        ]
        scored.sort(key=lambda t: t[1], reverse=True)
        return scored[: max(top_k, 0)]

    def ids(self) -> set[str]:
        return set(self._ids)
