"""Multi-supplier aggregation (composite SupplierScraper).

Queries several suppliers for the same part and returns the best result.
Because it implements the SupplierScraper port itself, the existing
SearchService / ResilientSupplier stack works unchanged — composition, not
modification (WS-1 "multi-source price aggregation").

Strategy "best_price": among non-error results, pick the one with the lowest
unit price (min across its price breaks). Falls back to the first non-error
result, then to the last error result.
"""

from __future__ import annotations

from ...domain.models import ProductResult
from ...domain.ports import SupplierScraper
from ...domain.pricing import extract_unit_price, price_rows


def _min_unit_price(result: ProductResult) -> float:
    best = float("inf")
    for _qty, unit, _ext in price_rows(result.price_rows, limit=50):
        price = extract_unit_price(unit)
        if price < best:
            best = price
    return best


class AggregatingSupplier:
    def __init__(self, suppliers: list[SupplierScraper], strategy: str = "best_price") -> None:
        if not suppliers:
            raise ValueError("at least one supplier required")
        self.suppliers = suppliers
        self.strategy = strategy

    @property
    def driver(self):
        # Expose the first supplier's driver (if any) for GUI compatibility.
        for s in self.suppliers:
            drv = getattr(s, "driver", None)
            if drv is not None:
                return drv
        return None

    def open(self) -> None:
        for s in self.suppliers:
            s.open()

    def fetch_one(self, query: str, timeout: int) -> ProductResult:
        successes: list[ProductResult] = []
        last_error: ProductResult | None = None
        for s in self.suppliers:
            try:
                result = s.fetch_one(query, timeout)
            except Exception as exc:
                last_error = ProductResult(query=query, error=str(exc))
                continue
            if result.error:
                last_error = result
            else:
                successes.append(result)

        if not successes:
            return last_error or ProductResult(query=query, error="no supplier returned a result")

        if self.strategy == "best_price":
            return min(successes, key=_min_unit_price)
        return successes[0]

    def cancel(self) -> None:
        for s in self.suppliers:
            s.cancel()

    def close(self) -> None:
        for s in self.suppliers:
            s.close()
