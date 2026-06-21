"""Offline catalog supplier.

Reads parts from a local JSON catalog instead of the web — useful for offline
mode, cached parts, and as a verifiable second supplier in the multi-supplier
aggregation (WS-1). Implements the SupplierScraper port.

Catalog format (JSON):
    {
      "LM358P": {
        "title": "...", "part_number": "...", "product_url": "...",
        "datasheet_url": "...", "price_rows": ["1|$0.40|$0.40"],
        "specs": {"Mounting Type": "Through Hole"}
      }
    }
Keys are matched case-insensitively against the query.
"""

from __future__ import annotations

import json
from pathlib import Path

from ...domain.models import ProductResult


class LocalCatalogSupplier:
    def __init__(self, catalog_path: str | Path, source: str = "local") -> None:
        self.catalog_path = Path(catalog_path)
        self.source = source
        self._catalog: dict[str, dict] = {}

    def open(self) -> None:
        try:
            raw = json.loads(self.catalog_path.read_text(encoding="utf-8"))
            self._catalog = {str(k).upper(): v for k, v in raw.items()}
        except Exception:
            self._catalog = {}

    def fetch_one(self, query: str, timeout: int) -> ProductResult:
        entry = self._catalog.get(query.strip().upper())
        if not entry:
            return ProductResult(query=query, error=f"not in {self.source} catalog")
        return ProductResult(
            query=query,
            title=entry.get("title", ""),
            product_url=entry.get("product_url", ""),
            datasheet_url=entry.get("datasheet_url", ""),
            part_number=entry.get("part_number"),
            price_rows=list(entry.get("price_rows", [])),
            specs=dict(entry.get("specs", {})),
        )

    def cancel(self) -> None:
        pass

    def close(self) -> None:
        self._catalog = {}
