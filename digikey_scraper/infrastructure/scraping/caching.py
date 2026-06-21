"""Caching decorator for any SupplierScraper.

Caches successful fetch_one results with a TTL to avoid redundant scrapes
(WS-1 "cached parts" / WS-5 "response cache"). Composable like the resilient
and aggregating decorators — e.g. Caching(Resilient(Aggregating([...]))).

In-memory by default; an optional disk directory persists the cache across
runs (one JSON file per query). Errors are never cached.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path

from ...domain.models import ProductResult
from ...domain.ports import SupplierScraper
from ..persistence.serialization import result_from_dict, result_to_dict


def _key(query: str) -> str:
    return query.strip().upper()


class CachingSupplier:
    def __init__(
        self,
        inner: SupplierScraper,
        ttl_seconds: float = 86400.0,
        cache_dir: str | Path | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.inner = inner
        self.ttl_seconds = ttl_seconds
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self._clock = clock
        self._mem: dict[str, tuple[float, ProductResult]] = {}
        self.hits = 0
        self.misses = 0

    @property
    def driver(self):
        return getattr(self.inner, "driver", None)

    def open(self) -> None:
        self.inner.open()

    def _disk_path(self, key: str) -> Path | None:
        if self.cache_dir is None:
            return None
        safe = "".join(c if c.isalnum() else "_" for c in key) or "_"
        return self.cache_dir / f"{safe}.json"

    def _read(self, key: str) -> ProductResult | None:
        now = self._clock()
        entry = self._mem.get(key)
        if entry and now - entry[0] < self.ttl_seconds:
            return entry[1]
        path = self._disk_path(key)
        if path and path.exists():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                if now - raw["ts"] < self.ttl_seconds:
                    result = result_from_dict(raw["result"])
                    self._mem[key] = (raw["ts"], result)
                    return result
            except Exception:
                return None
        return None

    def _write(self, key: str, result: ProductResult) -> None:
        ts = self._clock()
        self._mem[key] = (ts, result)
        path = self._disk_path(key)
        if path is not None:
            try:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    json.dumps({"ts": ts, "result": result_to_dict(result)}, ensure_ascii=False),
                    encoding="utf-8",
                )
            except Exception:
                pass

    def fetch_one(self, query: str, timeout: int) -> ProductResult:
        key = _key(query)
        cached = self._read(key)
        if cached is not None:
            self.hits += 1
            return cached
        self.misses += 1
        result = self.inner.fetch_one(query, timeout)
        if not result.error:  # never cache failures
            self._write(key, result)
        return result

    def cancel(self) -> None:
        self.inner.cancel()

    def close(self) -> None:
        self.inner.close()
