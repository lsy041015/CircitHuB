# Category Detail & Shared Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 카테고리 검색 결과를 일반 부품 검색 결과와 같은 결과 파이프라인으로 통합하고, category listing 기반 최소 정보에서 product detail 기반 상세 정보까지 점진적으로 보강한다.

**Architecture:** 카테고리 검색은 `2-phase fetch` 로 바꾼다. 1단계에서 category listing 1페이지를 읽어 빠르게 `ProductResult` 목록을 만든 뒤, 2단계에서 같은 Selenium 세션으로 각 product detail 페이지를 순회하며 `price_rows`, `specs`, `datasheet_url`, `scraped_at` 를 hydrate 한다. UI는 별도 `category_result_area` 전용 렌더를 줄이고, 최종 표시를 기존 `self.results` + `render_results()` + filter/sort/share/history 흐름으로 통합한다.

**Tech Stack:** Python 3.10, PySide6, Selenium/Chrome, BeautifulSoup4, existing `scraper.py` detail parser, project `.venv`, pytest/unittest

---

## Recommended Approach

### Option A: Listing-only enrichment
- 장점: 빠름, 구현 단순
- 단점: price/spec/datasheet 빈칸 많음, 일반 검색 카드와 parity 안 나옴

### Option B: 2-phase progressive hydration (recommended)
- 장점: 첫 화면은 빠르고, 곧 일반 검색급 상세 데이터로 수렴
- 단점: worker/state 복잡도 증가, 네트워크 요청 수 증가

### Option C: Click-to-hydrate on demand
- 장점: 네트워크 절약
- 단점: 사용자가 상세를 눌러야만 정보가 채워짐, “완전 통합” 요구와 거리 있음

**Recommendation:** Option B. 현재 `fetch_product_detail()` / `ResultCard` / `render_results()` 를 가장 많이 재사용하면서, 사용감과 데이터 품질 둘 다 맞출 수 있다.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `digikey_scraper/scraper.py` | Modify | category listing row parser 확장 + detail hydrate entry helpers |
| `digikey_scraper/infrastructure/scraping/category_scraper.py` | Modify | listing fetch + detail hydration orchestration |
| `digikey_scraper/workers.py` | Modify | progressive category signals / worker state |
| `digikey_scraper/_main_window.py` | Modify | category 결과를 `self.results`/`render_results()` 로 통합, progress 반영 |
| `digikey_scraper/_ui_builder.py` | Modify | category launcher page 유지, shared result flow에 맞게 page behavior 조정 |
| `digikey_scraper/category_presenter.py` | Modify | source badge / hydration 상태 문구 |
| `digikey_scraper/_translations.py` | Modify | category hydrate 상태 문구 추가 |
| `tests/test_category_search.py` | Modify | parser + shared-flow regression |
| `tests/test_category_presenter.py` | Modify | hydrate/flow status copy regression |
| `README.md` | Modify | safe category regression command 유지/확장 |

---

## Behavioral Target

1. 사용자가 `카테고리 검색` 페이지에서 타일 클릭
2. listing 1페이지 결과가 빠르게 준비됨
3. UI가 기존 결과 패널을 사용해 결과 카드를 보여줌
4. filter/sort/favorite/share/save/history 가 category 결과에도 동일하게 작동
5. worker 가 detail hydration 진행률을 보내고, 카드가 점진적으로 상세화됨
6. 실패 시 `listing 실패` 와 `hydrate 일부 실패` 를 구분 표시

---

## Task 1: Lock shared-flow requirements with tests

**Files:**
- Modify: `tests/test_category_search.py`
- Modify: `tests/test_category_presenter.py`

- [ ] **Step 1: Add failing presenter tests for new hydration/status copy**

```python
def test_searching_result_payload_mentions_hydration():
    title, detail = category_result_payload(_tr("ko"), "searching", label="저항")
    assert "가져오는 중" in title
    assert "DigiKey" in detail


def test_badge_text_keeps_last_category_label():
    assert "저항" in category_badge_text(_tr("ko"), "저항")
```

- [ ] **Step 2: Add failing shared-flow UI tests**

```python
def test_category_finished_reuses_main_results_list(window):
    sample = [ProductResult(query="저항", title="RC0402", product_url="https://example.test/p")]
    window._on_category_finished(sample)
    assert window.results == sample


def test_category_finished_switches_to_search_page(window):
    sample = [ProductResult(query="저항", title="RC0402", product_url="https://example.test/p")]
    window.show_category_page()
    window._on_category_finished(sample)
    assert window.app_stack.currentWidget() is window.search_page
```

- [ ] **Step 3: Run tests and confirm RED**

Run:
```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest \
  tests/test_category_search.py tests/test_category_presenter.py -q
```

Expected:
- `test_category_finished_reuses_main_results_list` fail
- `test_category_finished_switches_to_search_page` fail
- any new presenter-copy tests fail

- [ ] **Step 4: Commit failing tests**

```bash
git add tests/test_category_search.py tests/test_category_presenter.py
git commit -m "test(category): lock shared flow expectations"
```

---

## Task 2: Enrich category listing parser

**Files:**
- Modify: `digikey_scraper/scraper.py`
- Modify: `tests/test_category_search.py`

- [ ] **Step 1: Extend HTML fixture with listing metadata**

```python
LISTING_HTML = """
<html><body>
  <table>
    <tr>
      <td><a href="/en/products/detail/yageo/RC0402JR-071KL/726365">RC0402JR-071KL</a></td>
      <td>Yageo</td>
      <td>Res 1k Ohm 5% 1/16W 0402 SMD</td>
      <td>1,245 In Stock</td>
      <td>$0.10</td>
    </tr>
  </table>
</body></html>
"""
```

- [ ] **Step 2: Add failing parser assertions**

```python
def test_parse_category_listing_sets_stock_and_price_preview():
    soup = BeautifulSoup(LISTING_HTML, "html.parser")
    result = parse_category_listing(soup, category_label="저항", limit=25)[0]
    assert result.specs.get("재고") == "1,245 In Stock"
    assert result.price_rows


def test_parse_category_listing_sets_manufacturer():
    soup = BeautifulSoup(LISTING_HTML, "html.parser")
    result = parse_category_listing(soup, category_label="저항", limit=25)[0]
    assert result.specs.get("제조사") == "Yageo"
```

- [ ] **Step 3: Implement minimal listing enrichment in `parse_category_listing()`**

Implementation target:
- reuse existing link extraction as base
- inspect nearby columns/cells for manufacturer / stock / price text
- populate:
  - `specs["제조사"]`
  - `specs["재고"]`
  - `price_rows`
  - `scraped_at` left empty here

- [ ] **Step 4: Run parser tests**

Run:
```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest \
  tests/test_category_search.py -k "parse_category_listing" -q
```

Expected: all parser tests pass

- [ ] **Step 5: Commit**

```bash
git add digikey_scraper/scraper.py tests/test_category_search.py
git commit -m "feat(category): enrich listing parser with preview metadata"
```

---

## Task 3: Add progressive detail hydration

**Files:**
- Modify: `digikey_scraper/infrastructure/scraping/category_scraper.py`
- Modify: `digikey_scraper/scraper.py`
- Modify: `tests/test_category_search.py`

- [ ] **Step 1: Add a pure helper test for “merge hydrated detail into listing result”**

```python
def test_category_detail_merge_preserves_query_and_url():
    listing = ProductResult(query="저항", title="RC0402", product_url="https://example.test/p")
    detail = ProductResult(
        query="RC0402",
        title="RC0402",
        product_url="https://example.test/p",
        datasheet_url="https://example.test/ds.pdf",
        price_rows=["1|$0.10|$0.10"],
        specs={"제조사": "Yageo"},
    )
    merged = merge_category_detail_result(listing, detail, scraped_at=123.0)
    assert merged.query == "저항"
    assert merged.product_url == "https://example.test/p"
    assert merged.datasheet_url.endswith(".pdf")
    assert merged.scraped_at == 123.0
```

- [ ] **Step 2: Implement helper in `scraper.py`**

Implementation target:
- new helper `merge_category_detail_result(listing, detail, scraped_at)`
- preserve category query label
- preserve listing URL/title fallback
- replace missing `price_rows`, `datasheet_url`, `specs`, `part_number`

- [ ] **Step 3: Extend `CategoryScraper` API**

Target shape:
```python
def fetch_listing(... ) -> list[ProductResult]:
    ...

def hydrate_details(
    self,
    results: list[ProductResult],
    timeout: int,
    on_progress: Callable[[int, int, ProductResult], None] | None = None,
) -> list[ProductResult]:
    ...
```

- [ ] **Step 4: Implement sequential hydration**

Implementation notes:
- same `self._driver` reuse
- for each listing result with `product_url`, call existing detail fetch path
- on failure, keep listing preview result and attach lightweight error marker in `specs` or `error`
- set `scraped_at` on hydrated results

- [ ] **Step 5: Add targeted unit-style test with monkeypatched detail fetch**

```python
def test_hydrate_details_keeps_listing_when_detail_fails(monkeypatch):
    ...
```

- [ ] **Step 6: Run category tests**

Run:
```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest \
  tests/test_category_search.py -q
```

Expected: category tests green

- [ ] **Step 7: Commit**

```bash
git add digikey_scraper/scraper.py digikey_scraper/infrastructure/scraping/category_scraper.py tests/test_category_search.py
git commit -m "feat(category): add progressive detail hydration"
```

---

## Task 4: Extend category worker signals for progressive updates

**Files:**
- Modify: `digikey_scraper/workers.py`
- Modify: `tests/test_category_search.py`

- [ ] **Step 1: Add failing signal-surface tests**

Implementation target:
- `CategorySignals` gains:
  - `listing_ready = Signal(list)`
  - `detail_progress = Signal(int, int, object)`
  - `hydration_done = Signal(list)`

- [ ] **Step 2: Update worker flow**

Target sequence:
1. `started(label)`
2. `listing_ready(listing_results)`
3. repeated `detail_progress(index, total, hydrated_result)`
4. `finished(final_results)`

- [ ] **Step 3: Keep old single-failure path**

Rules:
- listing fetch hard-fail => `failed`
- detail fetch partial fail => continue, emit degraded result

- [ ] **Step 4: Run focused tests**

Run:
```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m unittest tests.test_category_presenter -v
```

Plus:
```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest \
  tests/test_category_search.py -q
```

- [ ] **Step 5: Commit**

```bash
git add digikey_scraper/workers.py tests/test_category_search.py
git commit -m "feat(category): emit listing and hydration progress signals"
```

---

## Task 5: Route category results into main search flow

**Files:**
- Modify: `digikey_scraper/_main_window.py`
- Modify: `digikey_scraper/_ui_builder.py`
- Modify: `digikey_scraper/category_presenter.py`
- Modify: `digikey_scraper/_translations.py`
- Modify: `tests/test_category_search.py`
- Modify: `tests/test_category_presenter.py`

- [ ] **Step 1: Remove category-only final render dependency**

Target behavior:
- category page remains launcher
- final results live in `self.results`
- `render_results()` becomes single source of truth

- [ ] **Step 2: On listing-ready, optionally show category page placeholder**

Behavior:
- keep launcher visible while first listing loads
- show status copy from presenter helpers

- [ ] **Step 3: On category finished, switch to shared result page**

Implementation target:
```python
self.results = final_results
self.show_search_page()
self.render_results()
```

- [ ] **Step 4: Preserve category context**

Add state:
```python
self._result_source = "search" | "category"
self._category_feedback_label = ...
```

Use it for:
- source badge text
- status strip text
- history label prefix like `카테고리: 저항`

- [ ] **Step 5: Progressive hydration updates refresh main cards**

On `detail_progress`:
- replace matching `ProductResult` in `self.results`
- re-render cards
- keep current sort/filter state applied

- [ ] **Step 6: Ensure existing actions still work**

Verify category results support:
- favorite toggle
- candidate click noop-safe
- share/save text
- filter/sort on search page
- datasheet open if hydrated

- [ ] **Step 7: Run shared-flow regression**

Run:
```bash
./scripts/test_category_safe.sh
```

Expected:
- category UI tests green
- parser tests green
- presenter tests green

- [ ] **Step 8: Commit**

```bash
git add digikey_scraper/_main_window.py digikey_scraper/_ui_builder.py digikey_scraper/category_presenter.py digikey_scraper/_translations.py tests/test_category_search.py tests/test_category_presenter.py
git commit -m "feat(category): unify category results with shared result flow"
```

---

## Task 6: Docs and manual verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add manual verification checklist**

Checklist content:
- open app
- click category page
- click `저항`
- confirm results move into main result flow
- confirm badge shows `마지막 실행 · 저항`
- confirm sort/filter still works
- confirm datasheet button appears after hydration on at least one card

- [ ] **Step 2: Document safe regression command**

Keep:
```bash
./scripts/test_category_safe.sh
```

Add optional full command:
```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest \
  tests/test_category_search.py tests/test_category_presenter.py -q
```

- [ ] **Step 3: Run final verification**

Run:
```bash
./scripts/test_category_safe.sh
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m unittest \
  tests.test_category_presenter tests.test_safe_test_script -v
```

Expected:
- category regression green
- presenter/unit tests green

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs(category): document shared-flow verification"
```

---

## Risks / Watchpoints

- `render_results()` currently assumes main search ownership. Category source metadata must not leak into normal searches after reset.
- Progressive re-render on every hydrated item may flicker. If too noisy, batch updates every `N` items or every `250ms`.
- Some listing pages may not expose manufacturer/stock/price cleanly. Parser must fail soft.
- Detail hydration can be slow for `25` items. If UX degrades, cap hydration to first `10` while keeping listing preview for all `25`.

---

## Verification Matrix

- Parser-only:
```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_category_search.py -k "parse_category" -q
```

- Presenter-only:
```bash
.venv/bin/python -m unittest tests.test_category_presenter -v
```

- Shared category regression:
```bash
./scripts/test_category_safe.sh
```

- Manual GUI smoke:
1. launch app from `.venv`
2. click `카테고리 검색`
3. click `저항`
4. wait for cards
5. verify sort/filter/favorite/share

---

## Scope Guard

This plan does **not** include:
- main text-input auto-routing to category search
- multi-page category crawling
- supplier-comparison integration for category mode
- RAG/chat integration with category result context

Keep those out unless requirements change.
