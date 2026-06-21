"""Deterministic text chunker for datasheets.

Splits text into overlapping character windows aligned to whitespace, so a
chunk rarely cuts a word in half. Pure and dependency-free.
"""

from __future__ import annotations

import re

from ...domain.rag import Chunk

_WS = re.compile(r"\s+")


def _normalize(text: str) -> str:
    return _WS.sub(" ", text).strip()


def chunk_text(
    text: str,
    doc_id: str,
    max_chars: int = 500,
    overlap: int = 50,
    page: int | None = None,
) -> list[Chunk]:
    if max_chars <= 0:
        raise ValueError("max_chars must be > 0")
    if not 0 <= overlap < max_chars:
        raise ValueError("overlap must be in [0, max_chars)")
    norm = _normalize(text)
    if not norm:
        return []

    chunks: list[Chunk] = []
    start = 0
    n = len(norm)
    idx = 0
    while start < n:
        end = min(start + max_chars, n)
        # extend to the next whitespace so we don't split a word
        if end < n:
            space = norm.rfind(" ", start, end)
            if space > start:
                end = space
        piece = norm[start:end].strip()
        if piece:
            chunks.append(Chunk(id=f"{doc_id}:{idx}", doc_id=doc_id, text=piece, page=page))
            idx += 1
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return chunks
