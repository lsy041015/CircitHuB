"""Pure pricing/BOM logic. No framework or IO dependencies."""

from __future__ import annotations

import re

from .models import ProductResult

BOM_SAMPLE_QTY = 100


def price_rows(rows: list[str], limit: int = 8) -> list[tuple[str, str, str]]:
    parsed = []
    for row in rows[:limit]:
        pieces = [p.strip() for p in row.split("|")]
        if len(pieces) >= 3:
            parsed.append((pieces[0], pieces[1], pieces[2]))
        elif len(pieces) == 2:
            parsed.append((pieces[0], pieces[1], ""))
        else:
            parsed.append((row, "", ""))
    return parsed or [("N/A", "", "")]


def extract_unit_price(value: str) -> float:
    m = re.search(r"[-+]?\d+(?:,\d{3})*(?:\.\d+)?", value)
    if not m:
        return float("inf")
    return float(m.group(0).replace(",", ""))


def calc_bom_total(
    results: list[ProductResult],
    quantities: dict[str, int] | None = None,
    default_quantity: int = BOM_SAMPLE_QTY,
) -> float:
    quantities = quantities or {}
    total = 0.0
    for r in results:
        if r.error or r.candidate_results or not r.price_rows:
            continue
        requested_qty = max(1, int(quantities.get(r.query, default_quantity)))
        rows = price_rows(r.price_rows, limit=20)
        best = float("inf")
        for qty_s, unit_s, _ in rows:
            try:
                qty = int(re.sub(r"[^\d]", "", qty_s) or "0")
                if 0 < qty <= requested_qty:
                    u = extract_unit_price(unit_s)
                    if u < best:
                        best = u
            except Exception:
                pass
        if best < float("inf"):
            total += best * requested_qty
    return total
