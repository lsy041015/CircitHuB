"""Ports: abstract interfaces the application layer depends on.

Infrastructure adapters implement these; the DI container wires concrete
implementations at runtime. Domain/application code never imports concrete
adapters or frameworks (Qt, Selenium, SQLAlchemy) directly.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .chat_models import AiChatSession
from .models import ProductResult
from .rag import Answer, RetrievedChunk


@runtime_checkable
class SupplierScraper(Protocol):
    """Fetches a single product for a query from a supplier.

    Implementations manage their own session lifecycle via open()/close().
    Multi-supplier adapters (Mouser, LCSC, ...) land in P1 against this port.
    """

    def open(self) -> None: ...

    def fetch_one(self, query: str, timeout: int) -> ProductResult: ...

    def cancel(self) -> None: ...

    def close(self) -> None: ...


@runtime_checkable
class ProgressSink(Protocol):
    """Receives search progress. Qt adapter emits signals; headless uses no-op."""

    def on_progress(self, index: int, total: int, query: str) -> None: ...

    def on_finished(
        self, results: list[ProductResult], show_browser: bool, cancelled: bool
    ) -> None: ...

    def on_failed(self, error: str) -> None: ...


@runtime_checkable
class ResultRepository(Protocol):
    """Persists search results. JSON adapter is the default; Postgres optional."""

    def save_search(
        self, queries: list[str], results: list[ProductResult], language: str = "ko"
    ) -> int | None: ...

    def recent_searches(self, limit: int = 20) -> list[dict]: ...


@runtime_checkable
class SettingsStore(Protocol):
    """Loads/saves the user settings dict."""

    def load(self) -> dict: ...

    def save(self, data: dict) -> None: ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Maps texts to fixed-dimension vectors. Offline default; LLM-backed later."""

    @property
    def dim(self) -> int: ...

    def embed(self, texts: list[str]) -> list[list[float]]: ...


@runtime_checkable
class VectorStore(Protocol):
    """Stores vectors with payloads and returns nearest neighbours."""

    def add(self, ids: list[str], vectors: list[list[float]], payloads: list[dict]) -> None: ...

    def search(self, vector: list[float], top_k: int) -> list[tuple[str, float, dict]]: ...

    def ids(self) -> set[str]: ...


@runtime_checkable
class Answerer(Protocol):
    """Produces a cited answer from retrieved chunks.

    Offline default is extractive (no LLM); a Gemma/Claude answerer implements
    the same port and must still return citations referencing retrieved chunks.
    """

    def answer(self, question: str, retrieved: list[RetrievedChunk]) -> Answer: ...


@runtime_checkable
class TextGenerator(Protocol):
    """LLM text generation. Concrete adapters wrap Gemma/Claude/local models."""

    def generate(self, prompt: str) -> str: ...


@runtime_checkable
class AiChatRepository(Protocol):
    """Persists AI chat sessions. JSON adapter is the default."""

    def save_session(self, session: AiChatSession) -> None: ...

    def load_sessions(self) -> list[AiChatSession]: ...

    def delete_session(self, session_id: str) -> None: ...
