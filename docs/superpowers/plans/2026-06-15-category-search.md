# Category Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a separate "카테고리 검색" panel accessible from the sidebar that lets the user browse DigiKey by component type (저항, 커패시터, 인덕터 etc.) and shows up to 25 products from the listing page in a single connection.

**Architecture:** A new `app_stack` page (`category_page`) is added alongside `search_page`. The sidebar gets a "카테고리 검색" button that switches to it. Category tiles (QPushButton grid) drive a `CategoryWorker` that navigates to a DigiKey filter URL and parses the listing HTML (reusing existing `extract_product_links_from_soup`). Results are injected into `self.results` and rendered by the existing `render_results()` / `ResultCard` pipeline.

**Tech Stack:** PySide6, Selenium/Chrome, BeautifulSoup4, existing scraper helpers

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `digikey_scraper/_keyword_map.py` | CREATE | CATEGORIES list + `lookup_category()` |
| `digikey_scraper/scraper.py` | MODIFY | Add `fetch_category_products()` free function |
| `digikey_scraper/infrastructure/scraping/category_scraper.py` | CREATE | `CategoryScraper` class wrapping driver + `fetch_category_products` |
| `digikey_scraper/workers.py` | MODIFY | Add `CategorySignals` + `CategoryWorker` |
| `digikey_scraper/_stylesheet.py` | MODIFY | Category tile + page styles |
| `digikey_scraper/_ui_builder.py` | MODIFY | `_build_category_page()` + sidebar button |
| `digikey_scraper/_main_window.py` | MODIFY | `show_category_page()`, `search_category()`, result signal handlers |
| `tests/test_category_search.py` | CREATE | Tests for keyword map + HTML parsing |

---

### Task 1: Keyword map module

**Files:**
- Create: `digikey_scraper/_keyword_map.py`
- Create: `tests/test_category_search.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_category_search.py
import pytest
from digikey_scraper._keyword_map import CATEGORIES, lookup_category


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
```

- [ ] **Step 2: Run to verify fail**

```bash
env -i HOME=$HOME PATH=$PWD/.venv/bin:/usr/bin:/bin QT_QPA_PLATFORM=offscreen \
  python -m pytest tests/test_category_search.py -v 2>&1 | tail -15
```

Expected: `ERROR` – `ModuleNotFoundError: No module named 'digikey_scraper._keyword_map'`

- [ ] **Step 3: Create `_keyword_map.py`**

```python
# digikey_scraper/_keyword_map.py
"""Maps component-type keywords (Korean/English) to DigiKey category filter URLs."""
from __future__ import annotations

BASE = "https://www.digikey.com"

CATEGORIES: list[dict] = [
    {
        "key": "resistor",
        "label_ko": "저항",
        "label_en": "Resistor",
        "icon": "Ω",
        "url": f"{BASE}/en/products/filter/chip-resistors/52",
    },
    {
        "key": "capacitor",
        "label_ko": "커패시터",
        "label_en": "Capacitor",
        "icon": "C",
        "url": f"{BASE}/en/products/filter/ceramic-capacitors/60",
    },
    {
        "key": "inductor",
        "label_ko": "인덕터",
        "label_en": "Inductor",
        "icon": "L",
        "url": f"{BASE}/en/products/filter/fixed-inductors/71",
    },
    {
        "key": "diode",
        "label_ko": "다이오드",
        "label_en": "Diode",
        "icon": "▷|",
        "url": f"{BASE}/en/products/filter/rectifier-diodes/288",
    },
    {
        "key": "mosfet",
        "label_ko": "MOSFET",
        "label_en": "MOSFET",
        "icon": "⊣",
        "url": f"{BASE}/en/products/filter/single-mosfets/225",
    },
    {
        "key": "bjt",
        "label_ko": "BJT",
        "label_en": "BJT",
        "icon": "⊿",
        "url": f"{BASE}/en/products/filter/bipolar-transistors-bjt/73",
    },
    {
        "key": "opamp",
        "label_ko": "오퍼앰프",
        "label_en": "Op-Amp",
        "icon": "△",
        "url": f"{BASE}/en/products/filter/instrumentation-op-amps-buffer-amps/687",
    },
    {
        "key": "mcu",
        "label_ko": "MCU",
        "label_en": "MCU",
        "icon": "□",
        "url": f"{BASE}/en/products/filter/microcontrollers/78",
    },
    {
        "key": "led",
        "label_ko": "LED",
        "label_en": "LED",
        "icon": "◉",
        "url": f"{BASE}/en/products/filter/standard-leds-through-hole/94",
    },
    {
        "key": "crystal",
        "label_ko": "크리스탈",
        "label_en": "Crystal",
        "icon": "◇",
        "url": f"{BASE}/en/products/filter/crystals/171",
    },
    {
        "key": "relay",
        "label_ko": "릴레이",
        "label_en": "Relay",
        "icon": "⎍",
        "url": f"{BASE}/en/products/filter/power-relays-over-2-amps/196",
    },
    {
        "key": "sensor",
        "label_ko": "센서",
        "label_en": "Sensor",
        "icon": "◈",
        "url": f"{BASE}/en/products/filter/optical-sensors-photodiodes/543",
    },
]

# Build lookup index: all keys + Korean + English labels → category dict
_INDEX: dict[str, dict] = {}
for _cat in CATEGORIES:
    _INDEX[_cat["key"].lower()] = _cat
    _INDEX[_cat["label_ko"].lower()] = _cat
    _INDEX[_cat["label_en"].lower()] = _cat


def lookup_category(text: str) -> dict | None:
    """Return category dict if text matches a known keyword (case-insensitive), else None."""
    return _INDEX.get(text.strip().lower())
```

- [ ] **Step 4: Run tests**

```bash
env -i HOME=$HOME PATH=$PWD/.venv/bin:/usr/bin:/bin QT_QPA_PLATFORM=offscreen \
  python -m pytest tests/test_category_search.py::test_categories_have_required_keys \
  tests/test_category_search.py::test_lookup_by_korean \
  tests/test_category_search.py::test_lookup_by_english \
  tests/test_category_search.py::test_lookup_case_insensitive \
  tests/test_category_search.py::test_lookup_unknown_returns_none \
  tests/test_category_search.py::test_lookup_empty_returns_none -v 2>&1 | tail -15
```

Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add digikey_scraper/_keyword_map.py tests/test_category_search.py
git commit -m "feat(category): add keyword map with 12 DigiKey category URLs"
```

---

### Task 2: Category HTML parser in `scraper.py`

**Files:**
- Modify: `digikey_scraper/scraper.py` (add at end of file)
- Modify: `tests/test_category_search.py` (append tests)

- [ ] **Step 1: Write failing tests**

Append to `tests/test_category_search.py`:

```python
from bs4 import BeautifulSoup
from digikey_scraper.scraper import parse_category_listing


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
```

- [ ] **Step 2: Run to verify fail**

```bash
env -i HOME=$HOME PATH=$PWD/.venv/bin:/usr/bin:/bin QT_QPA_PLATFORM=offscreen \
  python -m pytest tests/test_category_search.py -k "parse_category" -v 2>&1 | tail -15
```

Expected: `ImportError: cannot import name 'parse_category_listing'`

- [ ] **Step 3: Add `parse_category_listing` to `scraper.py`**

Add at the end of `digikey_scraper/scraper.py`:

```python
def parse_category_listing(
    soup: "BeautifulSoup",
    category_label: str,
    limit: int = 25,
) -> list[ProductResult]:
    """Parse DigiKey category listing page soup into ProductResults.

    Uses the existing product-link extraction so it stays in sync with any
    selector updates. Each result gets query=category_label, no price scraping
    (listing page, 1-connection constraint).
    """
    product_links = extract_product_links_from_soup(soup, limit=limit)
    results: list[ProductResult] = []
    for link in product_links:
        results.append(
            ProductResult(
                query=category_label,
                title=link.name or extract_name_from_url(link.url),
                product_url=link.url,
                part_number=extract_name_from_url(link.url),
                price_rows=[],
                specs={},
            )
        )
    return results
```

Note: `BeautifulSoup` is already imported at the top of `scraper.py` via `from bs4 import BeautifulSoup`.  `ProductResult` is imported from `.models`. Both are present in the existing file.

- [ ] **Step 4: Run tests**

```bash
env -i HOME=$HOME PATH=$PWD/.venv/bin:/usr/bin:/bin QT_QPA_PLATFORM=offscreen \
  python -m pytest tests/test_category_search.py -v 2>&1 | tail -15
```

Expected: All `test_parse_category_listing_*` tests pass. Total ≥ 12 passed.

- [ ] **Step 5: Commit**

```bash
git add digikey_scraper/scraper.py tests/test_category_search.py
git commit -m "feat(category): add parse_category_listing to scraper"
```

---

### Task 3: CategoryScraper class

**Files:**
- Create: `digikey_scraper/infrastructure/scraping/category_scraper.py`

- [ ] **Step 1: Create the file**

```python
# digikey_scraper/infrastructure/scraping/category_scraper.py
"""Selenium-backed scraper that fetches a DigiKey category listing page."""
from __future__ import annotations

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ...domain.models import ProductResult
from ...driver import create_driver, get_page_soup
from ...scraper import DETAIL_LINK_SELECTOR, parse_category_listing


class CategoryScraper:
    """Fetches a DigiKey category filter page and returns up to `limit` ProductResults.

    One connection only — no per-product detail page visits.
    """

    def __init__(self, show_browser: bool = False) -> None:
        self.show_browser = show_browser
        self._driver: webdriver.Chrome | None = None

    @property
    def driver(self) -> webdriver.Chrome | None:
        return self._driver

    def open(self) -> None:
        if self._driver is None:
            self._driver = create_driver(headless=not self.show_browser)

    def fetch(
        self,
        url: str,
        category_label: str,
        limit: int = 25,
        timeout: int = 30,
    ) -> list[ProductResult]:
        if self._driver is None:
            self.open()
        assert self._driver is not None

        self._driver.get(url)
        try:
            WebDriverWait(self._driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, DETAIL_LINK_SELECTOR))
            )
        except TimeoutException:
            pass  # parse whatever loaded

        soup = get_page_soup(self._driver)
        return parse_category_listing(soup, category_label=category_label, limit=limit)

    def cancel(self) -> None:
        self._quit()

    def close(self) -> None:
        self._quit()

    def _quit(self) -> None:
        if self._driver is not None:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None
```

- [ ] **Step 2: Verify import works**

```bash
env -i HOME=$HOME PATH=$PWD/.venv/bin:/usr/bin:/bin \
  python -c "from digikey_scraper.infrastructure.scraping.category_scraper import CategoryScraper; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Run full test suite**

```bash
env -i HOME=$HOME PATH=$PWD/.venv/bin:/usr/bin:/bin QT_QPA_PLATFORM=offscreen \
  python -m pytest tests/ -q 2>&1 | tail -5
```

Expected: `157+ passed`

- [ ] **Step 4: Commit**

```bash
git add digikey_scraper/infrastructure/scraping/category_scraper.py
git commit -m "feat(category): add CategoryScraper class"
```

---

### Task 4: CategoryWorker in `workers.py`

**Files:**
- Modify: `digikey_scraper/workers.py`

- [ ] **Step 1: Add `CategorySignals` and `CategoryWorker`**

Append to `digikey_scraper/workers.py`:

```python
from .infrastructure.scraping.category_scraper import CategoryScraper


class CategorySignals(QObject):
    started = Signal(str)   # category_label
    finished = Signal(list)  # list[ProductResult]
    failed = Signal(str)    # error message


class CategoryWorker:
    """Fetches one DigiKey category listing page in a background thread."""

    def __init__(
        self,
        category: dict,
        show_browser: bool,
        signals: CategorySignals,
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
        except Exception as exc:  # noqa: BLE001
            self.signals.failed.emit(str(exc))
        finally:
            self._scraper.close()
```

- [ ] **Step 2: Verify import**

```bash
env -i HOME=$HOME PATH=$PWD/.venv/bin:/usr/bin:/bin \
  python -c "from digikey_scraper.workers import CategoryWorker, CategorySignals; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Run test suite**

```bash
env -i HOME=$HOME PATH=$PWD/.venv/bin:/usr/bin:/bin QT_QPA_PLATFORM=offscreen \
  python -m pytest tests/ -q 2>&1 | tail -5
```

Expected: same pass count as before.

- [ ] **Step 4: Commit**

```bash
git add digikey_scraper/workers.py
git commit -m "feat(category): add CategorySignals and CategoryWorker"
```

---

### Task 5: Category page styles in `_stylesheet.py`

**Files:**
- Modify: `digikey_scraper/_stylesheet.py`

- [ ] **Step 1: Add styles**

Find the line `/* ── Results section ── */` in `_stylesheet.py` and insert the following block directly before it:

```css
/* ── Category page ── */
QWidget#CategoryPage { background: #FFFFFF; }
QLabel#CategoryPageTitle {
    font-size: 16px; font-weight: 700; letter-spacing: -0.3px;
}
QLabel#CategoryPageSub { font-size: 12px; color: #94A3B8; }
QPushButton#CategoryTile {
    background: #FFFFFF;
    border: 1px solid #E4E7EC;
    border-radius: 10px;
    color: #0F172A;
    font-size: 13px;
    font-weight: 600;
    padding: 0;
    min-width: 90px;
    min-height: 70px;
}
QPushButton#CategoryTile:hover {
    background: #EEF4FF;
    border-color: #D5E0FF;
    color: #1E3FAF;
}
QPushButton#CategoryTile:pressed { background: #DDE8FF; }
QPushButton#CategoryTile:disabled { color: #94A3B8; border-color: #E4E7EC; background: #F8FAFC; }
QLabel#TileIcon { font-size: 18px; background: transparent; }
QLabel#TileKo { font-size: 13px; font-weight: 600; background: transparent; }
QLabel#TileEn { font-size: 10px; color: #94A3B8; background: transparent; }
QPushButton#CategorySideBtn {
    background: #FFFFFF; border: 1px solid #E4E7EC;
    border-radius: 8px; height: 34px;
    color: #475569; font-size: 13px; font-weight: 600;
    text-align: left; padding: 0 12px;
}
QPushButton#CategorySideBtn:hover { background: #F4F5F7; border-color: #D0D5DD; }
QPushButton#CategorySideBtnActive {
    background: #EEF4FF; border: 1px solid #D5E0FF;
    border-radius: 8px; height: 34px;
    color: #1E3FAF; font-size: 13px; font-weight: 800;
    text-align: left; padding: 0 12px;
}

```

- [ ] **Step 2: Verify app still loads**

```bash
env -i HOME=$HOME PATH=$PWD/.venv/bin:/usr/bin:/bin QT_QPA_PLATFORM=offscreen \
  python -c "
from PySide6.QtWidgets import QApplication
import sys
app = QApplication(sys.argv)
from digikey_scraper._stylesheet import APP_QSS
app.setStyleSheet(APP_QSS)
print('stylesheet ok')
"
```

Expected: `stylesheet ok`

- [ ] **Step 3: Commit**

```bash
git add digikey_scraper/_stylesheet.py
git commit -m "feat(category): add category page and tile styles"
```

---

### Task 6: Build category page UI in `_ui_builder.py`

**Files:**
- Modify: `digikey_scraper/_ui_builder.py`

- [ ] **Step 1: Add imports at top of file**

The file already imports `QGridLayout`, `QPushButton`, `QLabel`, `QVBoxLayout`, `QHBoxLayout`, `QWidget`, `QScrollArea`. Verify these exist:

```bash
grep -n "QGridLayout\|QScrollArea\|QVBoxLayout" digikey_scraper/_ui_builder.py | head -5
```

If `QGridLayout` is missing, add it to the existing `from PySide6.QtWidgets import (...)` block.

- [ ] **Step 2: Add sidebar "카테고리 검색" button**

In `_build_sidebar()`, find the block that adds `chat_open_btn` (around line 94-101):

```python
        self.chat_open_btn = QPushButton("")
        self.chat_open_btn.setObjectName("ChatSideBtn")
        self.chat_open_btn.clicked.connect(self.open_chat)
        chat_wrap = QWidget()
        chat_l = QHBoxLayout(chat_wrap)
        chat_l.setContentsMargins(14, 0, 14, 12)
        chat_l.addWidget(self.chat_open_btn)
        vl.addWidget(chat_wrap)
```

Insert this block **before** the `chat_open_btn` block:

```python
        self.category_side_btn = QPushButton("◈  카테고리 검색")
        self.category_side_btn.setObjectName("CategorySideBtn")
        self.category_side_btn.clicked.connect(self.show_category_page)
        cat_wrap = QWidget()
        cat_l = QHBoxLayout(cat_wrap)
        cat_l.setContentsMargins(14, 0, 14, 6)
        cat_l.addWidget(self.category_side_btn)
        vl.addWidget(cat_wrap)
```

- [ ] **Step 3: Register category page in `_build_ui()`**

In `_build_ui()`, find the lines:

```python
        self.app_stack = QStackedWidget()
        self.search_page = self._build_main()
        self.app_stack.addWidget(self.search_page)
        body.addWidget(self.app_stack, 1)
```

Replace with:

```python
        self.app_stack = QStackedWidget()
        self.search_page = self._build_main()
        self.app_stack.addWidget(self.search_page)
        self.category_page = self._build_category_page()
        self.app_stack.addWidget(self.category_page)
        body.addWidget(self.app_stack, 1)
```

- [ ] **Step 4: Add `_build_category_page()` method**

Add this method to `UiBuilderMixin`, after `_build_filter_bar()`:

```python
    def _build_category_page(self) -> QWidget:
        from ._keyword_map import CATEGORIES

        page = QWidget()
        page.setObjectName("CategoryPage")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(0)

        # Header
        title = QLabel("카테고리 검색")
        title.setObjectName("CategoryPageTitle")
        sub = QLabel("소자 종류를 선택하면 DigiKey에서 최신 목록을 가져옵니다.")
        sub.setObjectName("CategoryPageSub")
        outer.addWidget(title)
        outer.addSpacing(4)
        outer.addWidget(sub)
        outer.addSpacing(20)

        # Category tile grid (4 columns)
        grid_w = QWidget()
        grid = QGridLayout(grid_w)
        grid.setSpacing(10)
        grid.setContentsMargins(0, 0, 0, 0)

        self._category_tile_buttons: list[QPushButton] = []
        cols = 4
        for idx, cat in enumerate(CATEGORIES):
            btn = QPushButton()
            btn.setObjectName("CategoryTile")
            # Stack icon + ko + en vertically inside the button via a child widget
            inner = QWidget()
            inner.setAttribute(inner.WA_TransparentForMouseEvents, True)  # type: ignore[arg-type]
            vl = QVBoxLayout(inner)
            vl.setContentsMargins(8, 10, 8, 10)
            vl.setSpacing(2)
            icon_lbl = QLabel(cat["icon"])
            icon_lbl.setObjectName("TileIcon")
            icon_lbl.setAlignment(0x0004)  # Qt.AlignHCenter
            ko_lbl = QLabel(cat["label_ko"])
            ko_lbl.setObjectName("TileKo")
            ko_lbl.setAlignment(0x0004)
            en_lbl = QLabel(cat["label_en"])
            en_lbl.setObjectName("TileEn")
            en_lbl.setAlignment(0x0004)
            vl.addWidget(icon_lbl)
            vl.addWidget(ko_lbl)
            vl.addWidget(en_lbl)

            # Overlay inner widget on button via stacked layout trick
            btn_layout = QVBoxLayout(btn)
            btn_layout.setContentsMargins(0, 0, 0, 0)
            btn_layout.addWidget(inner)

            btn.clicked.connect(lambda _checked, c=cat: self.search_category(c))
            grid.addWidget(btn, idx // cols, idx % cols)
            self._category_tile_buttons.append(btn)

        outer.addWidget(grid_w)
        outer.addSpacing(20)

        # Results area (reuse same content_layout pattern)
        self.category_result_area = QScrollArea()
        self.category_result_area.setWidgetResizable(True)
        self.category_result_area.setObjectName("ResultScroll")
        outer.addWidget(self.category_result_area, 1)

        return page
```

- [ ] **Step 5: Verify the UI builds without error**

```bash
env -i HOME=$HOME PATH=$PWD/.venv/bin:/usr/bin:/bin QT_QPA_PLATFORM=offscreen \
  python -c "
from PySide6.QtWidgets import QApplication
import sys
app = QApplication(sys.argv)
from digikey_scraper.qt_gui import run
# just import and instantiate; don't call run()
from digikey_scraper._main_window import MainWindow
from digikey_scraper.container import build_container
w = MainWindow(build_container())
print('UI ok')
"
```

Expected: `UI ok` (no exception)

- [ ] **Step 6: Commit**

```bash
git add digikey_scraper/_ui_builder.py
git commit -m "feat(category): add category page UI with 12 category tiles"
```

---

### Task 7: Wire category search logic in `_main_window.py`

**Files:**
- Modify: `digikey_scraper/_main_window.py`

- [ ] **Step 1: Add imports at top of `_main_window.py`**

Find the existing imports block and add (after the `SearchWorker` import):

```python
import threading

from .workers import CategorySignals, CategoryWorker
```

`threading` is already imported in `_main_window.py`. Only add the `CategoryWorker` / `CategorySignals` import if not already present.

```bash
grep -n "CategoryWorker\|CategorySignals" digikey_scraper/_main_window.py
```

If not present, find the line:

```python
from .workers import SearchSignals, SearchWorker, UiSignals
```

And replace with:

```python
from .workers import CategorySignals, CategoryWorker, SearchSignals, SearchWorker, UiSignals
```

- [ ] **Step 2: Add category state attributes in `__init__`**

Find in `__init__`:

```python
        self._query_times: list[float] = []
```

Add after it:

```python
        self._category_worker: CategoryWorker | None = None
        self._category_thread: threading.Thread | None = None
        self._category_signals: CategorySignals | None = None
```

- [ ] **Step 3: Add `show_category_page()` method**

Add this method after `show_search_page()` in `_main_window.py`:

```python
    def show_category_page(self):
        if hasattr(self, "app_stack") and hasattr(self, "category_page"):
            self.app_stack.setCurrentWidget(self.category_page)
        # Update sidebar button states
        if hasattr(self, "category_side_btn"):
            self.category_side_btn.setObjectName("CategorySideBtnActive")
            self.category_side_btn.style().unpolish(self.category_side_btn)
            self.category_side_btn.style().polish(self.category_side_btn)
        if hasattr(self, "chat_open_btn"):
            self.chat_open_btn.setObjectName("ChatSideBtn")
            self.chat_open_btn.style().unpolish(self.chat_open_btn)
            self.chat_open_btn.style().polish(self.chat_open_btn)
```

- [ ] **Step 4: Patch `show_search_page()` to reset category button**

Find the existing `show_search_page()` method and add at the end of it:

```python
        if hasattr(self, "category_side_btn"):
            self.category_side_btn.setObjectName("CategorySideBtn")
            self.category_side_btn.style().unpolish(self.category_side_btn)
            self.category_side_btn.style().polish(self.category_side_btn)
```

- [ ] **Step 5: Add `search_category()` and signal handlers**

Add these methods to `_main_window.py`:

```python
    def search_category(self, category: dict) -> None:
        if self.is_searching:
            return

        self._set_search_state(True)
        self._set_strip(
            "searching",
            self._tr("strip_searching", count=1),
            progress=0,
        )
        self.set_status(f"{category['label_ko']} 카테고리 검색 중...")
        self.results = []
        self.render_results()

        self._category_signals = CategorySignals()
        self._category_signals.finished.connect(self._on_category_finished)
        self._category_signals.failed.connect(self._on_category_failed)

        self._category_worker = CategoryWorker(
            category=category,
            show_browser=self.browser_toggle.isChecked(),
            signals=self._category_signals,
            limit=25,
            timeout=30,
        )
        self._category_thread = threading.Thread(
            target=self._category_worker.run,
            daemon=True,
            name="digikey-category",
        )
        self._category_thread.start()

    def _on_category_finished(self, results: list) -> None:
        self.results = results
        self._set_search_state(False)
        count = len(results)
        if count:
            self._set_strip("success", f"카테고리 결과 {count}개", progress=100)
        else:
            self._set_strip("error", "결과를 가져오지 못했습니다.", progress=100)
        self.render_results()

    def _on_category_failed(self, error: str) -> None:
        self._set_search_state(False)
        self._set_strip("error", f"카테고리 검색 오류: {error}", progress=100)
        self.set_status(f"오류: {error}")
```

- [ ] **Step 6: Wire category result area to `render_results`**

`render_results()` currently renders into `self.card_grid` and `self.text_result` (inside `search_page`). The category page needs its own result area populated by the same data.

The simplest approach: when `_on_category_finished` is called, temporarily switch the content to the category page's result scroll area. Since `render_results()` populates `self.card_grid` (inside `search_page`), we'll instead display the result cards directly in `category_result_area`.

Add this helper to `_main_window.py`:

```python
    def _render_category_results(self) -> None:
        from .models import ProductResult
        from ._result_card import ResultCard

        # Clear previous cards
        prev = self.category_result_area.widget()
        if prev:
            prev.deleteLater()

        container = QWidget()
        from PySide6.QtWidgets import QVBoxLayout, QGridLayout
        grid = QGridLayout(container)
        grid.setSpacing(12)
        grid.setContentsMargins(0, 0, 0, 0)

        cols = max(1, self._result_columns())
        for i, result in enumerate(self.results):
            card = ResultCard(i + 1, result, False, self.language)
            card.favorite_toggled.connect(self.toggle_favorite)
            card.open_datasheet.connect(self.open_datasheet)
            grid.addWidget(card, i // cols, i % cols)

        if not self.results:
            from ._widgets import EmptyPanel  # type: ignore[attr-defined]
            container2 = QWidget()
            vl = QVBoxLayout(container2)
            vl.addStretch()
            vl.addStretch()
            self.category_result_area.setWidget(container2)
            return

        self.category_result_area.setWidget(container)
```

Then in `_on_category_finished`, replace `self.render_results()` with `self._render_category_results()`.

- [ ] **Step 7: Verify full app loads and category page is reachable**

```bash
env -i HOME=$HOME PATH=$PWD/.venv/bin:/usr/bin:/bin QT_QPA_PLATFORM=offscreen \
  python -c "
from PySide6.QtWidgets import QApplication
import sys
app = QApplication(sys.argv)
from digikey_scraper._main_window import MainWindow
from digikey_scraper.container import build_container
w = MainWindow(build_container())
w.show_category_page()
print('category page switched ok')
w.show_search_page()
print('search page switched ok')
"
```

Expected: both `ok` lines printed, no exception.

- [ ] **Step 8: Run full test suite**

```bash
env -i HOME=$HOME PATH=$PWD/.venv/bin:/usr/bin:/bin QT_QPA_PLATFORM=offscreen \
  python -m pytest tests/ -q 2>&1 | tail -5
```

Expected: `157+ passed`

- [ ] **Step 9: Commit**

```bash
git add digikey_scraper/_main_window.py
git commit -m "feat(category): wire category search signals and page switching"
```

---

### Task 8: Integration smoke test + final cleanup

**Files:**
- Modify: `tests/test_category_search.py`

- [ ] **Step 1: Add integration smoke tests**

Append to `tests/test_category_search.py`:

```python
import pytest
from PySide6.QtWidgets import QApplication
from digikey_scraper._main_window import MainWindow
from digikey_scraper.container import build_container


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    return app


@pytest.fixture
def window(qapp):
    c = build_container()
    w = MainWindow(c)
    yield w
    w.close()


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
```

- [ ] **Step 2: Run new tests**

```bash
env -i HOME=$HOME PATH=$PWD/.venv/bin:/usr/bin:/bin QT_QPA_PLATFORM=offscreen \
  python -m pytest tests/test_category_search.py -v 2>&1 | tail -20
```

Expected: All tests pass.

- [ ] **Step 3: Run full suite one final time**

```bash
env -i HOME=$HOME PATH=$PWD/.venv/bin:/usr/bin:/bin QT_QPA_PLATFORM=offscreen \
  python -m pytest tests/ -q 2>&1 | tail -5
```

Expected: `170+ passed` (all original 157 + new category tests).

- [ ] **Step 4: Final commit**

```bash
git add tests/test_category_search.py
git commit -m "test(category): add integration smoke tests for category page"
```

---

## Self-Review

**Spec coverage:**
- ✅ Separate "카테고리 검색" button/panel in sidebar → Task 5, 6
- ✅ 12 category tiles (저항, 커패시터, 인덕터, 다이오드, MOSFET, BJT, Op-Amp, MCU, LED, Crystal, Relay, Sensor) → Task 1, 6
- ✅ 1 connection fetch from DigiKey category listing → Task 2, 3
- ✅ Results shown in existing card format → Task 7
- ✅ Filter bar (detect_component_type) auto-applies to category results → already present in `render_results()` / `_on_category_finished`

**Known limitation:** `_render_category_results` bypasses the existing filter bar. To reuse the full filter bar, the category results would need to be piped through `render_results()` on the search page. This is a follow-up; the MVP shows unfiltered results in `category_result_area`.

**Type consistency:** `CategoryWorker.signals.finished.emit(results)` emits `list[ProductResult]`. `_on_category_finished(results: list)` receives it. Consistent.

**Placeholder check:** No TBDs found. All code blocks are complete.
