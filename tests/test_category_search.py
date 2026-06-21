import pytest
from bs4 import BeautifulSoup
from PySide6.QtWidgets import QApplication

from digikey_scraper._keyword_map import CATEGORIES, lookup_category
from digikey_scraper._main_window import MainWindow
from digikey_scraper._main_window_category import MainWindowCategoryMixin
from digikey_scraper.container import build_container
from digikey_scraper.scraper import parse_category_listing


def test_categories_have_required_keys():
    for cat in CATEGORIES:
        assert "key" in cat
        assert "label_ko" in cat
        assert "label_en" in cat
        assert "url" in cat
        assert "icon" in cat


def test_lookup_by_korean():
    result = lookup_category("저항")
    assert result is not None
    assert result["key"] == "resistor"


def test_lookup_by_english():
    result = lookup_category("capacitor")
    assert result is not None
    assert result["key"] == "capacitor"


def test_lookup_case_insensitive():
    assert lookup_category("MOSFET") is not None
    assert lookup_category("mosfet") is not None


def test_lookup_unknown_returns_none():
    assert lookup_category("xyz_unknown_9999") is None


def test_lookup_empty_returns_none():
    assert lookup_category("") is None


# ── parse_category_listing tests ────────────────────────────────────────────


LISTING_HTML = """
<html><body>
<table>
  <tr>
    <td><a href="/en/products/detail/yageo/RC0402JR-071KL/726365">RC0402JR-071KL</a></td>
    <td>Res 1k Ohm 5% 1/16W 0402 SMD</td>
    <td>$0.10</td>
  </tr>
  <tr>
    <td><a href="/en/products/detail/vishay/CRCW040210K0FKED/71756">CRCW040210K0FKED</a></td>
    <td>Res 10k Ohm 1% 1/16W 0402 SMD</td>
    <td>$0.12</td>
  </tr>
</table>
</body></html>
"""


def test_parse_category_listing_returns_results():
    soup = BeautifulSoup(LISTING_HTML, "html.parser")
    results = parse_category_listing(soup, category_label="저항", limit=25)
    assert len(results) == 2


def test_parse_category_listing_sets_title():
    soup = BeautifulSoup(LISTING_HTML, "html.parser")
    results = parse_category_listing(soup, category_label="저항", limit=25)
    assert results[0].title == "RC0402JR-071KL"


def test_parse_category_listing_sets_query():
    soup = BeautifulSoup(LISTING_HTML, "html.parser")
    results = parse_category_listing(soup, category_label="저항", limit=25)
    assert all(r.query == "저항" for r in results)


def test_parse_category_listing_sets_product_url():
    soup = BeautifulSoup(LISTING_HTML, "html.parser")
    results = parse_category_listing(soup, category_label="저항", limit=25)
    assert "RC0402JR-071KL" in results[0].product_url


def test_parse_category_listing_respects_limit():
    soup = BeautifulSoup(LISTING_HTML, "html.parser")
    results = parse_category_listing(soup, category_label="저항", limit=1)
    assert len(results) == 1


def test_parse_category_listing_empty_soup():
    soup = BeautifulSoup("<html><body></body></html>", "html.parser")
    results = parse_category_listing(soup, category_label="저항", limit=25)
    assert results == []


# ── Integration smoke tests ──────────────────────────────────────────────────


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(qapp):
    w = MainWindow(build_container())
    yield w
    w.close()


def test_main_window_uses_category_mixin():
    assert issubclass(MainWindow, MainWindowCategoryMixin)


def test_category_page_exists(window):
    assert hasattr(window, "category_page")


def test_show_category_page_switches_stack(window):
    window.show_category_page()
    assert window.app_stack.currentWidget() is window.category_page


def test_show_search_page_switches_back(window):
    window.show_category_page()
    window.show_search_page()
    assert window.app_stack.currentWidget() is window.search_page


def test_category_tiles_exist(window):
    assert hasattr(window, "_category_tile_buttons")
    assert len(window._category_tile_buttons) == 12


def test_category_side_btn_exists(window):
    assert hasattr(window, "category_side_btn")


def test_category_back_to_search_btn_exists(window):
    assert hasattr(window, "category_back_btn")
    assert "←" in window.category_back_btn.text()


def test_category_back_to_search_btn_click_switches_stack(window):
    window.show_category_page()
    window.category_back_btn.click()
    assert window.app_stack.currentWidget() is window.search_page
