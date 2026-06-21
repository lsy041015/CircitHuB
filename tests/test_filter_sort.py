"""Unit tests for _filter_sort — no Qt required."""
import pytest
from digikey_scraper.models import ProductResult
from digikey_scraper._filter_sort import (
    SPEC_KEY_MAP,
    apply_filter,
    apply_sort,
    detect_component_type,
    parse_spec_value,
)


def _r(title="", price_rows=None, specs=None, error=None, scraped_at=None):
    return ProductResult(
        query=title,
        title=title,
        price_rows=price_rows or [],
        specs=specs or {},
        error=error,
        scraped_at=scraped_at,
    )


# ── parse_spec_value ────────────────────────────────────────────────────────

def test_parse_spec_value_kilo_ohm():
    assert parse_spec_value("10 kΩ") == pytest.approx(10_000.0)

def test_parse_spec_value_nano_farad():
    assert parse_spec_value("100nF") == pytest.approx(1e-7)

def test_parse_spec_value_micro_farad():
    assert parse_spec_value("4.7µF") == pytest.approx(4.7e-6)

def test_parse_spec_value_plain_number():
    assert parse_spec_value("100") == pytest.approx(100.0)

def test_parse_spec_value_mega():
    assert parse_spec_value("1M") == pytest.approx(1e6)

def test_parse_spec_value_fail():
    assert parse_spec_value("N/A") is None
    assert parse_spec_value("") is None


# ── detect_component_type ───────────────────────────────────────────────────

def test_detect_resistor():
    r = _r(title="10 kOhm Resistor 0402")
    assert detect_component_type(r) == "저항"

def test_detect_capacitor():
    r = _r(title="100nF Capacitor X7R")
    assert detect_component_type(r) == "캐패시터"

def test_detect_none():
    r = _r(title="Unknown Part XYZ")
    assert detect_component_type(r) is None


# ── apply_sort ──────────────────────────────────────────────────────────────

def test_sort_price_asc():
    r1 = _r("A", price_rows=["1|$0.50|$0.50"])
    r2 = _r("B", price_rows=["1|$0.20|$0.20"])
    r3 = _r("C", price_rows=["1|$1.00|$1.00"])
    result = apply_sort([r1, r2, r3], "price_asc")
    assert [x.title for x in result] == ["B", "A", "C"]

def test_sort_price_desc():
    r1 = _r("A", price_rows=["1|$0.50|$0.50"])
    r2 = _r("B", price_rows=["1|$0.20|$0.20"])
    r3 = _r("C", price_rows=["1|$1.00|$1.00"])
    result = apply_sort([r1, r2, r3], "price_desc")
    assert [x.title for x in result] == ["C", "A", "B"]

def test_sort_price_asc_malformed_row_sorts_last():
    r_good = _r("Good", price_rows=["1|$0.50|$0.50"])
    r_bad = _r("Bad", price_rows=["malformed"])
    result = apply_sort([r_bad, r_good], "price_asc")
    assert result[0].title == "Good"
    assert result[1].title == "Bad"

def test_sort_stock_desc():
    r1 = _r("A", specs={"재고": "100"})
    r2 = _r("B", specs={"재고": "500"})
    r3 = _r("C", specs={"재고": "50"})
    result = apply_sort([r1, r2, r3], "stock_desc")
    assert [x.title for x in result] == ["B", "A", "C"]

def test_sort_freshness_desc():
    r1 = _r("A", scraped_at=1000.0)
    r2 = _r("B", scraped_at=3000.0)
    r3 = _r("C", scraped_at=2000.0)
    result = apply_sort([r1, r2, r3], "fresh_desc")
    assert [x.title for x in result] == ["B", "C", "A"]

def test_sort_none_preserves_order():
    r1, r2, r3 = _r("A"), _r("B"), _r("C")
    result = apply_sort([r1, r2, r3], "none")
    assert [x.title for x in result] == ["A", "B", "C"]


# ── apply_filter ────────────────────────────────────────────────────────────

def test_filter_hide_errors():
    r_ok = _r("Good")
    r_err = _r("Bad", error="timeout")
    result = apply_filter([r_ok, r_err], None, None, None, hide_errors=True)
    assert result == [r_ok]

def test_filter_type_resistor():
    res = _r("10k Resistor 0402")
    cap = _r("100nF Capacitor X7R")
    unk = _r("Unknown Part")
    result = apply_filter([res, cap, unk], "저항", None, None, False)
    assert result == [res]

def test_filter_spec_range_passes_when_in_range():
    r = _r("Res", specs={"저항값": "10 kΩ"})  # 10000 Ω
    # min=5000, max=20000 → should pass
    result = apply_filter([r], "저항", 5_000.0, 20_000.0, False)
    assert result == [r]

def test_filter_spec_range_excludes_out_of_range():
    r = _r("Res", specs={"저항값": "1 kΩ"})  # 1000 Ω
    # min=5000 → should exclude
    result = apply_filter([r], "저항", 5_000.0, None, False)
    assert result == []

def test_filter_spec_range_passes_when_value_missing():
    r = _r("Res", specs={})  # no spec → should pass through
    result = apply_filter([r], "저항", 5_000.0, 20_000.0, False)
    assert result == [r]
