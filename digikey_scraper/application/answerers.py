"""Answerers for the RAG pipeline (WS-3 hallucination defense).

- LLMAnswerer: model-abstracted (via the TextGenerator port). Builds a prompt
  with numbered context chunks, asks the model to cite with [n], and maps those
  back to chunk ids. Gemma/Claude/local models plug in through the port.

- CitationEnforcingAnswerer: wraps any answerer and cross-verifies that the
  answer text is actually grounded in the cited chunks (token-overlap support).
  Unsupported citations are dropped; if grounding is too weak the answer is
  replaced with a safe refusal. This catches a model that cites a chunk but
  states something the chunk does not support.
"""

from __future__ import annotations

import re

from ..domain.ports import Answerer, TextGenerator
from ..domain.rag import Answer, RetrievedChunk

_TOKEN = re.compile(r"[a-z0-9]+")
_CITE = re.compile(r"\[(\d+)\]")


def _tokens(text: str) -> set[str]:
    return set(_TOKEN.findall(text.lower()))


def groundedness(answer_text: str, supporting_text: str) -> float:
    """Fraction of answer content tokens that appear in the supporting text."""
    ans = _tokens(answer_text)
    if not ans:
        return 1.0
    support = _tokens(supporting_text)
    return len(ans & support) / len(ans)


class LLMAnswerer:
    def __init__(self, generator: TextGenerator, max_chunks: int = 4) -> None:
        self.generator = generator
        self.max_chunks = max_chunks

    def _build_prompt(self, question: str, used: list[RetrievedChunk]) -> str:
        ctx = "\n".join(f"[{i + 1}] {r.chunk.text}" for i, r in enumerate(used))
        return (
            "Answer the question using ONLY the context below. "
            "Cite every claim with [n] referring to the context number. "
            "If the context is insufficient, say so.\n\n"
            f"Context:\n{ctx}\n\nQuestion: {question}\nAnswer:"
        )

    def answer(self, question: str, retrieved: list[RetrievedChunk]) -> Answer:
        used = [r for r in retrieved[: self.max_chunks] if r.score > 0]
        if not used:
            return Answer(text="No relevant information found.", citations=[], retrieved=retrieved)
        text = self.generator.generate(self._build_prompt(question, used))
        # Map [n] markers in the output back to chunk ids.
        cited_ids: list[str] = []
        for m in _CITE.findall(text):
            idx = int(m) - 1
            if 0 <= idx < len(used):
                cid = used[idx].chunk.id
                if cid not in cited_ids:
                    cited_ids.append(cid)
        return Answer(text=text.strip(), citations=cited_ids, retrieved=retrieved)


class CitationEnforcingAnswerer:
    def __init__(self, inner: Answerer, min_groundedness: float = 0.5) -> None:
        self.inner = inner
        self.min_groundedness = min_groundedness

    def answer(self, question: str, retrieved: list[RetrievedChunk]) -> Answer:
        ans = self.inner.answer(question, retrieved)
        by_id = {r.chunk.id: r.chunk.text for r in retrieved}
        # Keep only citations that exist among retrieved chunks.
        valid = [c for c in ans.citations if c in by_id]
        if not valid:
            return Answer(
                text="Insufficient grounded evidence to answer.",
                citations=[],
                retrieved=retrieved,
            )
        support = " ".join(by_id[c] for c in valid)
        if groundedness(ans.text, support) < self.min_groundedness:
            return Answer(
                text="Answer rejected: not sufficiently supported by sources.",
                citations=[],
                retrieved=retrieved,
            )
        return Answer(text=ans.text, citations=valid, retrieved=retrieved)
