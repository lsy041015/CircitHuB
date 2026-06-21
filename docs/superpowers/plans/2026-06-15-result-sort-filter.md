# Result Sort & Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 메인 검색 결과에 가격/재고/신선도 정렬, 회로 소자 유형 필터, 스펙 수치 범위 필터, 에러 숨기기를 추가한다.

**Architecture:** 순수 함수 모듈 `_filter_sort.py`에 모든 필터/정렬 로직을 격리하고, `_ui_builder.py`에 필터 바 위젯을 추가하며, `_main_window.py`에서 상태·시그널·`render_results()` 전처리를 연결한다. Qt 의존 없는 `_filter_sort.py`는 오프스크린 없이 테스트 가능하다.

**Tech Stack:** PySide6 (QComboBox, QCheckBox, QLineEdit), Python 3.10 dataclasses, pytest

---

## File Map

| 파일 | 변경 |
|------|------|
| `digikey_scraper/_filter_sort.py` | 신규 — 순수 함수 (Qt 없음) |
| `tests/test_filter_sort.py` | 신규 — 단위 테스트 |
| `digikey_scraper/_ui_builder.py` | 수정 — 필터 바 빌드 메서드 추가 |
| `digikey_scraper/_main_window.py` | 수정 — 상태 5개, 시그널 핸들러, `render_results()` 전처리 |

---

## Task 1: `_filter_sort.py` — 순수 로직 (TDD)

**Files:**
- Create: `digikey_scraper/_filter_sort.py`
- Create: `tests/test_filter_sort.py`

- [ ] **Step 1: 테스트 파일 작성**

```python
# tests/test_filter_sort.py
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
    spec_keys = SPEC_KEY_MAP["저항"][0]
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
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
QT_QPA_PLATFORM=offscreen pytest tests/test_filter_sort.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError: No module named 'digikey_scraper._filter_sort'`

- [ ] **Step 3: `_filter_sort.py` 구현**

```python
# digikey_scraper/_filter_sort.py
"""Pure filter/sort/parse logic. No Qt dependency."""
from __future__ import annotations

import re

from .models import ProductResult

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
    from .domain.pricing import extract_unit_price
    from .domain.pricing import price_rows as _parse_rows

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
        if type_str and detect_component_type(r) != type_str:
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
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
QT_QPA_PLATFORM=offscreen pytest tests/test_filter_sort.py -v
```

Expected: 전체 PASS. 실패 시 `parse_spec_value` regex 또는 `_get_stock` 파싱 확인.

- [ ] **Step 5: 커밋**

```bash
git add digikey_scraper/_filter_sort.py tests/test_filter_sort.py
git commit -m "feat(filter): add _filter_sort module with pure sort/filter/parse logic"
```

---

## Task 2: 필터 바 UI — `_ui_builder.py`

**Files:**
- Modify: `digikey_scraper/_ui_builder.py`

- [ ] **Step 1: `QComboBox`, `QCheckBox` 임포트 추가**

`_ui_builder.py` 11번째 줄 `from PySide6.QtWidgets import (` 블록에 추가:

```python
from PySide6.QtWidgets import (
    QCheckBox,    # ← 추가
    QComboBox,    # ← 추가
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
```

- [ ] **Step 2: `_build_filter_bar()` 메서드 추가**

`_ui_builder.py` 끝(`_build_results_area` 뒤)에 추가:

```python
def _build_filter_bar(self) -> QWidget:
    bar = QWidget()
    bar.setObjectName("FilterBar")
    bar.setVisible(False)
    bl = QHBoxLayout(bar)
    bl.setContentsMargins(0, 2, 0, 6)
    bl.setSpacing(10)

    sort_lbl = QLabel("정렬")
    sort_lbl.setObjectName("OptLabel")
    self.sort_combo = QComboBox()
    self.sort_combo.setFixedHeight(28)
    self.sort_combo.addItem("기본순", "none")
    self.sort_combo.addItem("가격↑", "price_asc")
    self.sort_combo.addItem("가격↓", "price_desc")
    self.sort_combo.addItem("재고↓", "stock_desc")
    self.sort_combo.addItem("최신순", "fresh_desc")
    self.sort_combo.currentIndexChanged.connect(self._on_sort_changed)
    bl.addWidget(sort_lbl)
    bl.addWidget(self.sort_combo)

    sep1 = QFrame()
    sep1.setFrameShape(QFrame.VLine)
    sep1.setObjectName("FilterSep")
    bl.addWidget(sep1)

    type_lbl = QLabel("유형")
    type_lbl.setObjectName("OptLabel")
    self.type_combo = QComboBox()
    self.type_combo.setFixedHeight(28)
    self.type_combo.addItem("전체", None)
    self.type_combo.currentIndexChanged.connect(self._on_type_changed)
    bl.addWidget(type_lbl)
    bl.addWidget(self.type_combo)

    self.range_min = QLineEdit()
    self.range_min.setObjectName("NumInput")
    self.range_min.setFixedWidth(70)
    self.range_min.setFixedHeight(28)
    self.range_min.setPlaceholderText("최소")
    self.range_min.setEnabled(False)
    self.range_min.textChanged.connect(self._on_spec_range_changed)

    self.range_max = QLineEdit()
    self.range_max.setObjectName("NumInput")
    self.range_max.setFixedWidth(70)
    self.range_max.setFixedHeight(28)
    self.range_max.setPlaceholderText("최대")
    self.range_max.setEnabled(False)
    self.range_max.textChanged.connect(self._on_spec_range_changed)

    self.range_unit_lbl = QLabel("")
    self.range_unit_lbl.setObjectName("OptLabel")

    bl.addWidget(self.range_min)
    tilde = QLabel("~")
    tilde.setObjectName("OptLabel")
    bl.addWidget(tilde)
    bl.addWidget(self.range_max)
    bl.addWidget(self.range_unit_lbl)

    bl.addStretch()

    self.hide_error_check = QCheckBox("에러 숨기기")
    self.hide_error_check.setObjectName("FilterCheck")
    self.hide_error_check.toggled.connect(self._on_hide_error_changed)
    bl.addWidget(self.hide_error_check)

    return bar
```

- [ ] **Step 3: `_build_results_area()` 에 필터 바 삽입**

`_build_results_area()` 안에서 `self.content_layout.addLayout(head)` 다음 줄, `self.result_stack = QStackedWidget()` 이전에 삽입:

현재 코드 (line 460–462):
```python
        self.content_layout.addLayout(head)

        self.result_stack = QStackedWidget()
```

변경 후:
```python
        self.content_layout.addLayout(head)

        self.filter_bar = self._build_filter_bar()
        self.content_layout.addWidget(self.filter_bar)

        self.result_stack = QStackedWidget()
```

- [ ] **Step 4: 앱 실행해 필터 바 표시 확인**

```bash
QT_QPA_PLATFORM=offscreen python -c "
from digikey_scraper._ui_builder import UiBuilderMixin
print('import OK')
"
```

Expected: `import OK` (에러 없음)

- [ ] **Step 5: 커밋**

```bash
git add digikey_scraper/_ui_builder.py
git commit -m "feat(filter): add filter bar widget to results area"
```

---

## Task 3: 상태 + 시그널 + `render_results()` 전처리 — `_main_window.py`

**Files:**
- Modify: `digikey_scraper/_main_window.py`

- [ ] **Step 1: 필터 상태 초기화 추가**

`_main_window.py` `MainWindow.__init__()` 안에서 `self._build_ui()` 호출 **직전**에 삽입.

현재 (line ~128-130):
```python
        self._last_result_columns = 0
        self.tab_var = "cards"
        ...
        self._build_ui()
```

삽입:
```python
        self._last_result_columns = 0
        self.tab_var = "cards"
        self._sort_key: str = "none"
        self._filter_type: str | None = None
        self._filter_spec_min: float | None = None
        self._filter_spec_max: float | None = None
        self._filter_hide_errors: bool = False
        self._build_ui()
```

- [ ] **Step 2: 시그널 핸들러 추가**

`_main_window.py` 파일 내 임의 위치(예: `render_results` 앞)에 4개 메서드 추가:

```python
def _on_sort_changed(self, index: int) -> None:
    self._sort_key = self.sort_combo.itemData(index) or "none"
    self.render_results()

def _on_type_changed(self, index: int) -> None:
    from ._filter_sort import SPEC_KEY_MAP

    type_str = self.type_combo.itemData(index)
    self._filter_type = type_str
    self._filter_spec_min = None
    self._filter_spec_max = None
    self.range_min.blockSignals(True)
    self.range_max.blockSignals(True)
    self.range_min.clear()
    self.range_max.clear()
    self.range_min.blockSignals(False)
    self.range_max.blockSignals(False)
    if type_str and type_str in SPEC_KEY_MAP:
        _, unit = SPEC_KEY_MAP[type_str]
        self.range_min.setEnabled(True)
        self.range_max.setEnabled(True)
        self.range_unit_lbl.setText(unit)
    else:
        self.range_min.setEnabled(False)
        self.range_max.setEnabled(False)
        self.range_unit_lbl.setText("")
    self.render_results()

def _on_spec_range_changed(self) -> None:
    def _parse(text: str) -> float | None:
        t = text.strip()
        if not t:
            return None
        try:
            return float(t)
        except ValueError:
            return None

    min_val = _parse(self.range_min.text())
    max_val = _parse(self.range_max.text())
    err_style = "border: 1px solid #e05;"
    self.range_min.setStyleSheet(
        err_style if self.range_min.text().strip() and min_val is None else ""
    )
    self.range_max.setStyleSheet(
        err_style if self.range_max.text().strip() and max_val is None else ""
    )
    self._filter_spec_min = min_val
    self._filter_spec_max = max_val
    self.render_results()

def _on_hide_error_changed(self, checked: bool) -> None:
    self._filter_hide_errors = checked
    self.render_results()
```

- [ ] **Step 3: `render_results()` 전처리 + 필터 바 업데이트**

현재 `render_results()` 시작부분 (line 229):
```python
    def render_results(self):
        while self.card_grid.count():
```

다음과 같이 변경 — 메서드 시작 직후에 전처리 삽입, `self.results` 참조 → `display` 변경:

```python
    def render_results(self):
        from ._filter_sort import apply_filter, apply_sort, detect_component_type

        # --- filter bar visibility + type combo refresh ---
        has_results = len(self.results) > 0
        if hasattr(self, "filter_bar"):
            self.filter_bar.setVisible(has_results)
        if hasattr(self, "type_combo") and has_results:
            current_type = self._filter_type
            self.type_combo.blockSignals(True)
            self.type_combo.clear()
            self.type_combo.addItem("전체", None)
            types_found = sorted(
                {detect_component_type(r) for r in self.results} - {None}
            )
            for t in types_found:
                self.type_combo.addItem(t, t)
            idx = self.type_combo.findData(current_type)
            self.type_combo.setCurrentIndex(idx if idx >= 0 else 0)
            self.type_combo.blockSignals(False)

        # --- build filtered+sorted display list ---
        display = apply_filter(
            self.results,
            self._filter_type,
            self._filter_spec_min,
            self._filter_spec_max,
            self._filter_hide_errors,
        )
        display = apply_sort(display, self._sort_key)

        # --- existing card-clear logic (unchanged) ---
        while self.card_grid.count():
            ...
```

그리고 카드 생성 루프에서 `self.results` → `display` 변경:

현재:
```python
        if not self.results:
            ...
        else:
            for i, result in enumerate(self.results):
                qt = self._query_times[i] if i < len(self._query_times) else 0.0
                card = ResultCard(i + 1, result, result.query in self.favorites, self.language, qt)
```

변경:
```python
        if not display:
            empty = QFrame()
            empty.setObjectName("EmptyPanel")
            el = QVBoxLayout(empty)
            el.setContentsMargins(16, 38, 16, 38)
            lbl = QLabel(self._tr("empty_results"))
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setObjectName("KvKey")
            el.addWidget(lbl)
            self.card_grid.addWidget(empty, 0, 0, 1, cols)
        else:
            for i, result in enumerate(display):
                # query_times index는 self.results 기반이므로 원본 인덱스 조회
                orig_idx = self.results.index(result) if result in self.results else i
                qt = self._query_times[orig_idx] if orig_idx < len(self._query_times) else 0.0
                card = ResultCard(i + 1, result, result.query in self.favorites, self.language, qt)
                card.copy_requested.connect(self.copy_text)
                card.favorite_requested.connect(self.toggle_favorite)
                card.candidate_requested.connect(self.search_candidate)
                card.share_requested.connect(self.share_text_to_chat)
                card.share_part_requested.connect(self.share_part_to_chat)
                self.card_grid.addWidget(card, i // cols, i % cols)
```

결과 카운트 레이블은 `self.results` (필터 전 전체 수) 기준 유지 — 기존 코드 변경 불필요.

- [ ] **Step 4: 전체 테스트 실행**

```bash
QT_QPA_PLATFORM=offscreen pytest --cov --cov-report=term-missing -q 2>&1 | tail -20
```

Expected: `_filter_sort` 테스트 포함 전체 PASS, coverage ≥85%.

- [ ] **Step 5: 커밋**

```bash
git add digikey_scraper/_main_window.py
git commit -m "feat(filter): wire sort/filter state and signals in MainWindow"
```

---

## Self-Review

**스펙 커버리지:**
- ✅ 가격/재고/신선도 정렬 (`apply_sort` Task 1)
- ✅ 소자 유형 필터 (`detect_component_type` + `apply_filter` Task 1, `type_combo` Task 2)
- ✅ 스펙 수치 범위 필터 (`parse_spec_value` + `apply_filter` Task 1, `range_min/max` Task 2)
- ✅ 에러 숨기기 (`apply_filter hide_errors` Task 1, `hide_error_check` Task 2)
- ✅ 결과 0개 시 빈 상태 UI 유지 (Task 3)
- ✅ IC/트랜지스터/커넥터 범위 필터 비활성화 (SPEC_KEY_MAP에 없음 → disabled, 스펙 명시)

**Placeholder 없음** ✅

**타입 일관성:**
- `apply_filter(results, type_str, spec_min, spec_max, hide_errors)` — Task 1 정의, Task 3 호출 동일 ✅
- `SPEC_KEY_MAP[key] → (list[str], str)` — Task 1 정의, Task 3 `_on_type_changed`에서 `SPEC_KEY_MAP[type_str]` 언팩 동일 ✅
- `self.sort_combo`, `self.type_combo`, `self.range_min`, `self.range_max`, `self.range_unit_lbl`, `self.hide_error_check`, `self.filter_bar` — Task 2에서 생성, Task 3에서 접근 ✅
