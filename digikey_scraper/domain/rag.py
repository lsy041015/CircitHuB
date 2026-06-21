"""RAG domain types. Pure data, no framework/IO deps."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Chunk:
    id: str
    doc_id: str
    text: str
    page: int | None = None


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: Chunk
    score: float


@dataclass(frozen=True)
class Answer:
    text: str
    citations: list[str] = field(default_factory=list)  # cited chunk ids
    retrieved: list[RetrievedChunk] = field(default_factory=list)
