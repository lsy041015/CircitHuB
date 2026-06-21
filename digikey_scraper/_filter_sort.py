"""Pure filter/sort/parse logic. No Qt dependency."""
from __future__ import annotations

import re

from .models import ProductResult
from .domain.pricing import extract_unit_price
from .domain.pricing import price_rows as _parse_rows

COMPONENT_TYPES: dict[str, list[str]] = {
    "저항":     ["resistor", "저항", "res "],
    "캐패시터":  ["capacitor", "캐패시터", "cap "],
    "인덕터":   ["inductor", "인덕터"],
    "IC":       ["ic ", "mcu", "microcontroller", "module"],
    "다이오드":  ["diode", "다이오드", "led", "zener"],
    "트랜지스터": ["transistor", "mosfet", "fet", "bjt"],
    "커넥터":   ["connector", "커넥터", "header", "socket"],
}

# type → (spec dict key candidates, unit label)
# Only types with a meaningful single numeric spec have entries.
# IC, 트랜지스터, 커넥터 intentionally absent → range filter disabled.
SPEC_KEY_MAP: dict[str, tuple[list[str], str]] = {
    "저항":    (["저항값", "저항", "Resistance"], "Ω"),
    "캐패시터": (["정전용량", "Capacitance", "용량"], "F"),
    "인덕터":  (["인덕턴스", "Inductance"], "H"),
    "다이오드": (["순방향전압", "Forward Voltage", "Voltage"], "V"),
}

_SI_PREFIX: dict[str, float] = {
    "p": 1e-12,
    "n": 1e-9,
    "µ": 1e-6,
    "u": 1e-6,
    "m": 1e-3,
    "k": 1e3,
    "K": 1e3,
    "M": 1e6,
    "G": 1e9,
}

# Matches: digits, optional SI prefix, optional unit chars
_SPEC_RE = re.compile(r"([\d.]+)\s*([pnµumkKMG]?)[ΩFHVohm\s]?")


def parse_spec_value(text: str) -> float | None:
    """Parse a spec string like '10 kΩ' → 10000.0. Returns None on failure."""
    if not text:
        return None
    m = _SPEC_RE.search(text)
    if not m:
        return None
    try:
        value = float(m.group(1))
    except ValueError:
        return None
    multiplier = _SI_PREFIX.get(m.group(2), 1.0)
    return value * multiplier


def detect_component_type(result: ProductResult) -> str | None:
    """Return the first matching COMPONENT_TYPES key, or None."""
    text = (result.title or "").lower()
    for type_name, keywords in COMPONENT_TYPES.items():
        for kw in keywords:
            if kw.lower() in text:
                return type_name
    return None


def _get_best_price(result: ProductResult) -> float:
    if not result.price_rows:
        return float("inf")
    parsed = _parse_rows(result.price_rows, limit=1)
    return extract_unit_price(parsed[0][1]) if parsed else float("inf")


def _get_stock(result: ProductResult) -> int:
    raw = result.specs.get("재고") or result.specs.get("Quantity Available", "")
    m = re.search(r"[\d,]+", raw)
    if m:
        try:
            return int(m.group(0).replace(",", ""))
        except ValueError:
            return 0
    return 0


def apply_sort(results: list[ProductResult], sort_key: str) -> list[ProductResult]:
    if sort_key == "price_asc":
        return sorted(results, key=_get_best_price)
    if sort_key == "price_desc":
        return sorted(results, key=_get_best_price, reverse=True)
    if sort_key == "stock_desc":
        return sorted(results, key=_get_stock, reverse=True)
    if sort_key == "fresh_desc":
        return sorted(results, key=lambda r: r.scraped_at or 0.0, reverse=True)
    return list(results)


def apply_filter(
    results: list[ProductResult],
    type_str: str | None,
    spec_min: float | None,
    spec_max: float | None,
    hide_errors: bool,
) -> list[ProductResult]:
    spec_keys = SPEC_KEY_MAP.get(type_str or "", ([], ""))[0] if type_str else []
    out: list[ProductResult] = []
    for r in results:
        if hide_errors and r.error:
            continue
        if type_str:
            detected = detect_component_type(r)
            has_spec_range = spec_min is not None or spec_max is not None
            if has_spec_range:
                # With a spec range active, only exclude items positively identified
                # as a different type; unknowns pass through (spec range will handle them).
                if detected is not None and detected != type_str:
                    continue
            else:
                # Without a spec range, require an exact type match.
                if detected != type_str:
                    continue
        if spec_keys and (spec_min is not None or spec_max is not None):
            val: float | None = None
            for key in spec_keys:
                raw = r.specs.get(key, "")
                if raw:
                    val = parse_spec_value(raw)
                    if val is not None:
                        break
            if val is not None:
                if spec_min is not None and val < spec_min:
                    continue
                if spec_max is not None and val > spec_max:
                    continue
        out.append(r)
    return out
