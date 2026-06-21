import threading
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal
from selenium import webdriver

if TYPE_CHECKING:
    from .application.ai_chat_service import AiChatService
    from .domain.chat_models import AiChatSession

from .application.search_service import SearchService
from .domain.models import ProductResult
from .infrastructure.scraping.category_scraper import CategoryScraper
from .infrastructure.scraping.registry import default_registry
from .infrastructure.scraping.resilient import ResilientSupplier


class SearchSignals(QObject):
    progress = Signal(int, int, str)
    finished = Signal(list, bool, bool)
    failed = Signal(str)


class UiSignals(QObject):
    status = Signal(str, object)
    status_key = Signal(str, object)
    received_share = Signal(str, str, str)


class _QtProgressSink:
    """ProgressSink adapter that forwards search progress to Qt signals."""

    def __init__(self, signals: "SearchSignals") -> None:
        self._signals = signals

    def on_progress(self, index: int, total: int, query: str) -> None:
        self._signals.progress.emit(index, total, query)

    def on_finished(
        self, results: list[ProductResult], show_browser: bool, cancelled: bool
    ) -> None:
        self._signals.finished.emit(results, show_browser, cancelled)

    def on_failed(self, error: str) -> None:
        self._signals.failed.emit(error)


class SearchWorker:
    """Thin Qt adapter around the headless SearchService.

    Public surface (queries/timeout/show_browser/signals/language, .driver,
    cancel(), run()) is preserved for MainWindow compatibility.
    """

    def __init__(
        self,
        queries: list[str],
        timeout: int,
        show_browser: bool,
        signals: SearchSignals,
        language: str = "ko",
    ) -> None:
        self.queries = queries
        self.timeout = timeout
        self.show_browser = show_browser
        self.signals = signals
        self.language = language
        self._cancel_event = threading.Event()
        base = default_registry().create("digikey", show_browser=show_browser)
        # Wrap with retry/backoff; stop retrying as soon as the search is cancelled.
        self._scraper = ResilientSupplier(base, should_cancel=self._cancel_event.is_set)
        self._service = SearchService(self._scraper, language=language)

    @property
    def driver(self) -> webdriver.Chrome | None:
        return self._scraper.driver

    def cancel(self) -> None:
        self._cancel_event.set()
        self._scraper.cancel()

    def run(self) -> None:
        sink = _QtProgressSink(self.signals)
        self._service.run(
            self.queries,
            self.timeout,
            self.show_browser,
            sink,
            self._cancel_event,
        )


class CategorySignals(QObject):
    started = Signal(str)
    finished = Signal(list)
    failed = Signal(str)


class CategoryWorker:
    """Fetches one DigiKey category listing page in a background thread."""

    def __init__(
        self,
        category: dict,
        show_browser: bool,
        signals: "CategorySignals",
        limit: int = 25,
        timeout: int = 30,
    ) -> None:
        self._category = category
        self._limit = limit
        self._timeout = timeout
        self.signals = signals
        self._scraper = CategoryScraper(show_browser=show_browser)

    @property
    def driver(self) -> webdriver.Chrome | None:
        return self._scraper.driver

    def cancel(self) -> None:
        self._scraper.cancel()

    def run(self) -> None:
        label = self._category["label_ko"]
        url = self._category["url"]
        self.signals.started.emit(label)
        try:
            results = self._scraper.fetch(
                url,
                category_label=label,
                limit=self._limit,
                timeout=self._timeout,
            )
            self.signals.finished.emit(results)
        except Exception as exc:
            self.signals.failed.emit(str(exc))
        finally:
            self._scraper.close()


class AiChatSignals(QObject):
    chunk = Signal(str)
    finished = Signal(str)
    failed = Signal(str)


class AiChatWorker:
    """Qt thread adapter for AiChatService.send_message."""

    def __init__(
        self,
        service: "AiChatService",
        session: "AiChatSession",
        text: str,
        parts_context: list[dict] | None = None,
    ) -> None:
        self._service = service
        self._session = session
        self._text = text
        self._parts_context = parts_context
        self.signals = AiChatSignals()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            result = self._service.send_message(
                session=self._session,
                text=self._text,
                on_chunk=self.signals.chunk.emit,
                parts_context=self._parts_context,
            )
            self.signals.finished.emit(result)
        except Exception as exc:
            self.signals.failed.emit(str(exc))
