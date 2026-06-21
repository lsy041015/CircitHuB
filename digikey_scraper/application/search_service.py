"""Headless search orchestration.

Extracted from the Qt ``SearchWorker`` so the search loop can run and be tested
without a GUI. The Qt worker is now a thin adapter (see
``digikey_scraper.workers``) that injects a Qt-signal-backed ProgressSink.
"""

from __future__ import annotations

import threading
import time

from ..domain.errors import ScrapeBlocked, ScrapeTimeout

_BLOCK_RETRY_DELAY = 8
from ..domain.models import ProductResult
from ..domain.ports import ProgressSink, SupplierScraper


def _timeout_message(language: str) -> str:
    return "Page load timed out." if language == "en" else "페이지 로딩 시간이 초과되었습니다."


def _blocked_message(language: str, exc: Exception) -> str:
    if language == "en":
        return f"Supplier blocked automated access: {exc}"
    return f"공급사가 자동화 접근을 차단했습니다: {exc}"


def _error_message(language: str, exc: Exception) -> str:
    if language == "en":
        return f"Error occurred while processing: {exc}"
    return f"처리 중 오류가 발생했습니다: {exc}"


class NullProgressSink:
    """No-op sink for headless/programmatic runs. Captures the final results."""

    def __init__(self) -> None:
        self.results: list[ProductResult] = []
        self.cancelled = False
        self.error: str | None = None

    def on_progress(self, index: int, total: int, query: str) -> None:  # noqa: D401
        pass

    def on_finished(
        self, results: list[ProductResult], show_browser: bool, cancelled: bool
    ) -> None:
        self.results = results
        self.cancelled = cancelled

    def on_failed(self, error: str) -> None:
        self.error = error


class SearchService:
    """Runs a batch of part-number queries against a SupplierScraper."""

    def __init__(self, scraper: SupplierScraper, language: str = "ko") -> None:
        self.scraper = scraper
        self.language = language

    def run(
        self,
        queries: list[str],
        timeout: int,
        show_browser: bool,
        sink: ProgressSink,
        cancel_event: threading.Event | None = None,
    ) -> None:
        cancel_event = cancel_event or threading.Event()
        results: list[ProductResult] = []
        cancelled = False
        try:
            self.scraper.open()
            total = len(queries)
            for index, query in enumerate(queries, start=1):
                if cancel_event.is_set():
                    cancelled = True
                    break
                sink.on_progress(index, total, query)
                try:
                    result = self.scraper.fetch_one(query, timeout)
                except ScrapeTimeout:
                    result = ProductResult(query=query, error=_timeout_message(self.language))
                except ScrapeBlocked as exc:
                    if cancel_event.is_set():
                        cancelled = True
                        break
                    time.sleep(_BLOCK_RETRY_DELAY)
                    try:
                        result = self.scraper.fetch_one(query, timeout)
                    except Exception as retry_exc:
                        result = ProductResult(query=query, error=_blocked_message(self.language, retry_exc))
                except Exception as exc:
                    if cancel_event.is_set():
                        cancelled = True
                        break
                    result = ProductResult(query=query, error=_error_message(self.language, exc))
                results.append(result)
            sink.on_finished(results, show_browser, cancelled)
        except Exception as exc:
            if cancel_event.is_set():
                sink.on_finished(results, show_browser, True)
            else:
                sink.on_failed(str(exc))
        finally:
            if not show_browser:
                self.scraper.close()
