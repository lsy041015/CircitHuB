"""Resilience decorator for any SupplierScraper.

Adds retry with exponential backoff around ``fetch_one`` — the P1 seed for
WS-1 "adaptive backoff" / WS-6 "retry budget". Transparent to the application
layer: it implements the same SupplierScraper port and delegates lifecycle
(open/close/cancel) and the ``driver`` attribute to the wrapped scraper.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from ...domain.errors import ScrapeBlocked
from ...domain.models import ProductResult
from ...domain.ports import SupplierScraper


class ResilientSupplier:
    def __init__(
        self,
        inner: SupplierScraper,
        retries: int = 2,
        base_delay: float = 0.5,
        max_delay: float = 8.0,
        sleep: Callable[[float], None] = time.sleep,
        should_cancel: Callable[[], bool] | None = None,
    ) -> None:
        if retries < 0:
            raise ValueError("retries must be >= 0")
        self.inner = inner
        self.retries = retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self._sleep = sleep
        self._should_cancel = should_cancel or (lambda: False)
        self.last_attempts = 0

    @property
    def driver(self):
        return getattr(self.inner, "driver", None)

    def open(self) -> None:
        self.inner.open()

    def _backoff_delay(self, attempt: int) -> float:
        # attempt is 0-based for the first retry.
        return min(self.max_delay, self.base_delay * (2**attempt))

    def fetch_one(self, query: str, timeout: int) -> ProductResult:
        attempt = 0
        while True:
            try:
                result = self.inner.fetch_one(query, timeout)
                self.last_attempts = attempt + 1
                return result
            except ScrapeBlocked:
                self.last_attempts = attempt + 1
                raise
            except Exception:
                if attempt >= self.retries or self._should_cancel():
                    self.last_attempts = attempt + 1
                    raise
                self._sleep(self._backoff_delay(attempt))
                attempt += 1

    def cancel(self) -> None:
        self.inner.cancel()

    def close(self) -> None:
        self.inner.close()
