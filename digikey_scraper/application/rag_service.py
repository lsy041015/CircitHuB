"""RAG retrieval pipeline: index → embed → store → retrieve → cited answer.

Hexagonal: depends only on domain types + ports (EmbeddingProvider, VectorStore,
Answerer). Concrete adapters (hashing embedder, in-memory store, Qdrant/LLM
later) are injected.

Hallucination guard: the service drops any citation that does not reference a
chunk that was actually retrieved, so an answer can never cite something the
store did not return.
"""

from __future__ import annotations

from collections.abc import Callable

from ..domain.ports import Answerer, EmbeddingProvider, VectorStore
from ..domain.rag import Answer, Chunk, RetrievedChunk
from ..infrastructure.rag.chunker import chunk_text


class ExtractiveAnswerer:
    """Offline, citation-safe answerer.

    Builds the answer purely from retrieved chunk text (extractive => cannot
    hallucinate) and cites exactly the chunks it used.
    """

    def __init__(self, max_chunks: int = 3) -> None:
        self.max_chunks = max_chunks

    def answer(self, question: str, retrieved: list[RetrievedChunk]) -> Answer:
        used = [r for r in retrieved[: self.max_chunks] if r.score > 0]
        if not used:
            return Answer(text="No relevant information found.", citations=[], retrieved=retrieved)
        text = "\n".join(f"[{r.chunk.id}] {r.chunk.text}" for r in used)
        return Answer(
            text=text,
            citations=[r.chunk.id for r in used],
            retrieved=retrieved,
        )


class RagService:
    def __init__(
        self,
        embedder: EmbeddingProvider,
        store: VectorStore,
        answerer: Answerer | None = None,
        chunker: Callable[..., list[Chunk]] = chunk_text,
        max_chars: int = 500,
        overlap: int = 50,
    ) -> None:
        self.embedder = embedder
        self.store = store
        self.answerer = answerer or ExtractiveAnswerer()
        self.chunker = chunker
        self.max_chars = max_chars
        self.overlap = overlap

    def index(self, doc_id: str, text: str, page: int | None = None) -> int:
        chunks = self.chunker(
            text, doc_id, max_chars=self.max_chars, overlap=self.overlap, page=page
        )
        if not chunks:
            return 0
        vectors = self.embedder.embed([c.text for c in chunks])
        payloads = [{"text": c.text, "doc_id": c.doc_id, "page": c.page} for c in chunks]
        self.store.add([c.id for c in chunks], vectors, payloads)
        return len(chunks)

    def retrieve(self, question: str, top_k: int = 3) -> list[RetrievedChunk]:
        qvec = self.embedder.embed([question])[0]
        hits = self.store.search(qvec, top_k)
        out: list[RetrievedChunk] = []
        for cid, score, payload in hits:
            out.append(
                RetrievedChunk(
                    chunk=Chunk(
                        id=cid,
                        doc_id=payload.get("doc_id", ""),
                        text=payload.get("text", ""),
                        page=payload.get("page"),
                    ),
                    score=score,
                )
            )
        return out

    def query(self, question: str, top_k: int = 3) -> Answer:
        retrieved = self.retrieve(question, top_k)
        retrieved_ids = {r.chunk.id for r in retrieved}
        answer = self.answerer.answer(question, retrieved)
        # Hallucination guard: keep only citations grounded in retrieved chunks.
        grounded = [c for c in answer.citations if c in retrieved_ids]
        if grounded == answer.citations:
            return answer
        return Answer(text=answer.text, citations=grounded, retrieved=retrieved)
