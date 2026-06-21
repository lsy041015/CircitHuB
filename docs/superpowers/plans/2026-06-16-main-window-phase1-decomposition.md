# MainWindow Phase 1 Decomposition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** production `MainWindow` 에서 남은 `sidebar/status`, `io`, `chat bridge` 책임을 별도 mixin 으로 분리하고, production-only runtime test 전환 준비를 끝낸다.

**Architecture:** 기존 실행 경로 `digikey_price_scraper.py -> digikey_scraper.qt_gui -> digikey_scraper._main_window.MainWindow` 는 유지한다. `_main_window.py` 는 coordinator 역할만 남기고, 남은 책임은 `_main_window_sidebar.py`, `_main_window_io.py`, `_main_window_chat.py` 로 이동한다. 테스트는 기존 방식처럼 “`MainWindow` 가 새 mixin 을 상속한다” 구조 잠금 + 기존 behavior smoke 재검증으로 진행한다.

**Tech Stack:** Python 3.10, PySide6, pytest, unittest, existing `digikey_scraper` mixin structure

---

## File Map

- Create: `digikey_scraper/_main_window_sidebar.py`
- Create: `digikey_scraper/_main_window_io.py`
- Create: `digikey_scraper/_main_window_chat.py`
- Modify: `digikey_scraper/_main_window.py`
- Create: `tests/test_main_window_sidebar.py`
- Create: `tests/test_main_window_io.py`
- Modify: `tests/test_chat.py`
- Modify: `tests/test_windows_runtime.py`

---

### Task 1: Extract sidebar/status/language presentation

**Files:**
- Create: `digikey_scraper/_main_window_sidebar.py`
- Modify: `digikey_scraper/_main_window.py:400-550`
- Create: `tests/test_main_window_sidebar.py`

- [ ] **Step 1: Write the failing sidebar mixin tests**

```python
# tests/test_main_window_sidebar.py
import unittest

from digikey_scraper._main_window import MainWindow
from digikey_scraper._main_window_sidebar import MainWindowSidebarMixin


class MainWindowSidebarTests(unittest.TestCase):
    def test_main_window_uses_sidebar_mixin(self) -> None:
        self.assertTrue(issubclass(MainWindow, MainWindowSidebarMixin))

    def test_api_state_ready_updates_footer_labels(self) -> None:
        window = MainWindow.__new__(MainWindow)
        window.footer_name = type("L", (), {"setText": lambda self, text: setattr(self, "text", text)})()
        window.footer_meta = type("L", (), {"setText": lambda self, text: setattr(self, "text", text)})()
        window.sb_connected = type("L", (), {"setText": lambda self, text: setattr(self, "text", text)})()
        window.sb_api = type("L", (), {"setText": lambda self, text: setattr(self, "text", text)})()

        window._set_api_state("ready")

        self.assertEqual(window.footer_name.text, "DigiKey")
        self.assertEqual(window.sb_connected.text, "● 준비됨")
```

- [ ] **Step 2: Run the sidebar tests to verify RED**

Run:
```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/test_main_window_sidebar.py -q
```

Expected:
- import error for `digikey_scraper._main_window_sidebar`
- or `issubclass` failure until the mixin is wired

- [ ] **Step 3: Create `MainWindowSidebarMixin` with the moved methods**

```python
# digikey_scraper/_main_window_sidebar.py
from __future__ import annotations

from ._widgets import SideFavoriteItem, SideHistoryItem


class MainWindowSidebarMixin:
    def render_sidebar_lists(self):
        while self.history_container_layout.count():
            item = self.history_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        items = self.history[-8:] if self.history else []
        for label, queries, meta, status in reversed(items):
            widget = SideHistoryItem(label, meta, status, payload=list(queries))
            widget.item_clicked.connect(self._load_history_label)
            self.history_container_layout.addWidget(widget)

        while self.fav_container_layout.count():
            item = self.fav_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for name in sorted(self.favorites):
            price = self.favorite_prices.get(name, "")
            widget = SideFavoriteItem(name, price)
            widget.item_clicked.connect(self._load_fav_item)
            self.fav_container_layout.addWidget(widget)

        if hasattr(self, "_hist_count_cnt"):
            self._hist_count_cnt.setText(str(len(items)))
        if hasattr(self, "_fav_count_cnt"):
            self._fav_count_cnt.setText(str(len(self.favorites)))

    def _apply_language(self):
        self.setWindowTitle(self._tr("window_title"))

        self.sidebar_desc.setText(self._tr("sidebar_subtitle"))
        self.new_search_btn.text_lbl.setText(self._tr("new_search"))
        self.category_side_btn.setText(self._tr("category_sidebar"))
        self.chat_open_btn.setText(self._tr("chat_open"))
        self._set_api_state("ready")
        if hasattr(self, "_hist_count_lbl"):
            self._hist_count_lbl.setText(self._tr("recent_search"))
        if hasattr(self, "_fav_count_lbl"):
            self._fav_count_lbl.setText(self._tr("favorites"))

        self.header_title.setText(self._tr("header_title"))
        self.header_sub.setText(self._tr("header_subtitle"))
        if hasattr(self, "category_page_title"):
            self.category_page_title.setText(self._tr("category_title"))
        if hasattr(self, "category_back_btn"):
            self.category_back_btn.setText(self._tr("category_back_to_search"))
        if hasattr(self, "category_last_badge"):
            self._refresh_category_badge()
        if hasattr(self, "category_page_sub"):
            self.category_page_sub.setText(self._tr("category_subtitle"))
        if hasattr(self, "category_hint_title"):
            self.category_hint_title.setText(self._tr("category_hint_title"))
        if hasattr(self, "category_hint_body"):
            self.category_hint_body.setText(self._tr("category_hint_body"))
        self.import_bom_btn.setText(self._tr("import_bom"))
        self.save_results_btn.setText(self._tr("save_results"))

        self.panel_tag.setText(self._tr("part_input_label"))
        self.panel_helper.setText(self._tr("part_input_helper"))
        self.example_btn.setText(self._tr("example"))
        self.clear_btn.setText(self._tr("clear"))
        self._chip_input.setPlaceholderText(
            self._tr("part_placeholder_more") if self.parts else self._tr("part_placeholder")
        )
        self.timeout_label_w.setText(self._tr("timeout"))
        self.seconds_label_w.setText(self._tr("seconds"))
        self.browser_label_w.setText(self._tr("show_browser"))
        self.auto_save_label_w.setText(self._tr("auto_save"))
        self.share_label_w.setText(self._tr("share"))
        self.share_toggle_btn.setText("⌃" if self.share_controls.isVisible() else "≋")
        self.cancel_btn.setText(self._tr("cancel"))
        self._update_run_button()

        if not self.is_searching:
            self._set_strip("neutral", self._tr("ready_to_search"))

        self.results_title.setText(self._tr("results"))
        self.card_btn.setText(f"▦ {self._tr('card_view')}")
        self.text_btn.setText(f"☰ {self._tr('text_view')}")
        self.card_btn.setToolTip(self._tr("card_view"))
        self.text_btn.setToolTip(self._tr("text_view"))

        self._set_api_state("ready")
        self._update_statusbar()

        self.render_sidebar_lists()
        self.render_chips()
        self.render_results()
        if self._category_results and hasattr(self, "category_result_area"):
            self._render_category_results(self._category_results)
        elif hasattr(self, "category_result_area"):
            self._set_category_result_message(
                self._category_feedback_state,
                label=self._category_feedback_label,
                error=self._category_feedback_error,
            )

    def _update_statusbar(self):
        self.sb_parts.setText(self._tr("statusbar_parts_fmt", n=len(self.parts)))
        try:
            timeout_value = int(self.timeout_input.text().strip())
        except (ValueError, AttributeError):
            timeout_value = int(self.timeout_default)
        self.sb_timeout.setText(self._tr("statusbar_timeout_fmt", t=timeout_value))

    def _set_api_state(self, state: str, detail: str = "") -> None:
        labels = {
            "ready": ("DigiKey", "검색 준비", "● 준비됨"),
            "searching": ("DigiKey", "조회 중", "● 조회 중"),
            "ok": ("DigiKey", "최근 조회 정상", "● 정상"),
            "warning": ("DigiKey", "후보/일부 오류", "● 확인 필요"),
            "error": ("DigiKey", "최근 조회 실패", "● 오류"),
        }
        name, meta, status = labels.get(state, labels["ready"])
        if detail:
            meta = detail
        self.footer_name.setText(name)
        self.footer_meta.setText(meta)
        self.sb_connected.setText(status)
        self.sb_api.setText(meta)
```

- [ ] **Step 4: Wire the sidebar mixin into `MainWindow`**

```diff
--- a/digikey_scraper/_main_window.py
+++ b/digikey_scraper/_main_window.py
@@
-from ._main_window_search import MainWindowSearchMixin
+from ._main_window_search import MainWindowSearchMixin
+from ._main_window_sidebar import MainWindowSidebarMixin
@@
 class MainWindow(
     MainWindowCategoryMixin,
     MainWindowPartsMixin,
     MainWindowSearchMixin,
+    MainWindowSidebarMixin,
     UiBuilderMixin,
     SharingMixin,
     PartSuggestionsMixin,
     QMainWindow,
 ):
```

- [ ] **Step 5: Remove the moved methods from `_main_window.py` and rerun tests**

Run:
```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/test_main_window_sidebar.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 QT_QPA_PLATFORM=offscreen python3 -m pytest tests/test_category_search.py tests/test_windows_runtime.py -q
python3 -m ruff check digikey_scraper/_main_window.py digikey_scraper/_main_window_sidebar.py tests/test_main_window_sidebar.py
```

Expected:
- sidebar tests pass
- category/runtime tests pass
- ruff passes

- [ ] **Step 6: Commit**

```bash
git add digikey_scraper/_main_window.py digikey_scraper/_main_window_sidebar.py tests/test_main_window_sidebar.py
git commit -m "refactor(ui): extract main window sidebar mixin"
```

---

### Task 2: Extract import/save/copy IO helpers

**Files:**
- Create: `digikey_scraper/_main_window_io.py`
- Modify: `digikey_scraper/_main_window.py:688-740`
- Create: `tests/test_main_window_io.py`

- [ ] **Step 1: Write the failing IO mixin tests**

```python
# tests/test_main_window_io.py
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from digikey_scraper._main_window import MainWindow
from digikey_scraper._main_window_io import MainWindowIoMixin


class MainWindowIoTests(unittest.TestCase):
    def test_main_window_uses_io_mixin(self) -> None:
        self.assertTrue(issubclass(MainWindow, MainWindowIoMixin))

    def test_get_result_text_strips_whitespace(self) -> None:
        window = MainWindow.__new__(MainWindow)
        window.latest_share_text = "  abc  \n"
        self.assertEqual(window.get_result_text(), "abc")

    def test_auto_save_results_writes_expected_file(self) -> None:
        window = MainWindow.__new__(MainWindow)
        window.latest_share_text = "hello"
        with TemporaryDirectory() as tmp:
            window.auto_save_dir = Path(tmp)
            saved = window._auto_save_results()
        self.assertIsNotNone(saved)
        self.assertTrue(saved.name.startswith("digikey_results_"))
```

- [ ] **Step 2: Run the IO tests to verify RED**

Run:
```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/test_main_window_io.py -q
```

Expected:
- import error for `digikey_scraper._main_window_io`
- or `issubclass` failure

- [ ] **Step 3: Create `MainWindowIoMixin` and move the IO methods**

```python
# digikey_scraper/_main_window_io.py
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QFileDialog, QMessageBox

from ._helpers import split_part_tokens
from .sharing import build_share_filename


class MainWindowIoMixin:
    def import_bom(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            self._tr("import_bom_dialog_title"),
            "",
            "Text/CSV files (*.txt *.csv *.tsv);;All files (*.*)",
        )
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = Path(path).read_text(encoding="cp949", errors="ignore")
        self.parts = []
        for token in split_part_tokens(text):
            if re.search(r"[A-Z0-9]", token):
                self.add_part(token)
        self.set_status(self._tr("bom_loaded_status", name=Path(path).name))
        self.save_settings()

    def _auto_save_results(self) -> Path | None:
        text = self.latest_share_text.strip()
        if not text:
            return None
        self.auto_save_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.auto_save_dir / f"digikey_results_{timestamp}.txt"
        path.write_text(text, encoding="utf-8")
        return path

    def get_result_text(self) -> str:
        return self.latest_share_text.strip()

    def copy_text(self, text: str):
        if text:
            QGuiApplication.clipboard().setText(text)
            self.set_status(self._tr("copied_status"))

    def save_results_as(self):
        text = self.get_result_text()
        if not text:
            QMessageBox.warning(self, self._tr("no_save_title"), self._tr("no_save_message"))
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            self._tr("save_dialog_title"),
            build_share_filename(),
            "Text files (*.txt);;All files (*.*)",
        )
        if not path:
            return
        Path(path).write_text(text, encoding="utf-8")
        self.set_status(self._tr("saved_status", path=path))
```

- [ ] **Step 4: Wire the IO mixin into `MainWindow` and remove duplicate methods**

```diff
--- a/digikey_scraper/_main_window.py
+++ b/digikey_scraper/_main_window.py
@@
-from ._main_window_sidebar import MainWindowSidebarMixin
+from ._main_window_io import MainWindowIoMixin
+from ._main_window_sidebar import MainWindowSidebarMixin
@@
 class MainWindow(
     MainWindowCategoryMixin,
     MainWindowPartsMixin,
     MainWindowSearchMixin,
     MainWindowSidebarMixin,
+    MainWindowIoMixin,
     UiBuilderMixin,
     SharingMixin,
     PartSuggestionsMixin,
     QMainWindow,
 ):
```

- [ ] **Step 5: Rerun IO and runtime verification**

Run:
```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/test_main_window_io.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 QT_QPA_PLATFORM=offscreen python3 -m pytest tests/test_windows_runtime.py -q
python3 -m ruff check digikey_scraper/_main_window.py digikey_scraper/_main_window_io.py tests/test_main_window_io.py
```

Expected:
- IO tests pass
- runtime smoke passes
- ruff passes

- [ ] **Step 6: Commit**

```bash
git add digikey_scraper/_main_window.py digikey_scraper/_main_window_io.py tests/test_main_window_io.py
git commit -m "refactor(ui): extract main window io mixin"
```

---

### Task 3: Extract chat bridge from MainWindow

**Files:**
- Create: `digikey_scraper/_main_window_chat.py`
- Modify: `digikey_scraper/_main_window.py:622-647`
- Modify: `tests/test_chat.py`

- [ ] **Step 1: Add failing chat mixin structure test**

```python
# tests/test_chat.py
from digikey_scraper._main_window_chat import MainWindowChatMixin


class ChatTests(unittest.TestCase):
    def test_main_window_uses_chat_mixin(self) -> None:
        self.assertTrue(issubclass(MainWindow, MainWindowChatMixin))
```

- [ ] **Step 2: Run the chat tests to verify RED**

Run:
```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 QT_QPA_PLATFORM=offscreen python3 -m pytest tests/test_chat.py -q
```

Expected:
- import error for `digikey_scraper._main_window_chat`
- or `issubclass` failure

- [ ] **Step 3: Create `MainWindowChatMixin`**

```python
# digikey_scraper/_main_window_chat.py
from __future__ import annotations

from PySide6.QtCore import Qt

from ._circuitkit_chat_design import CircuitKitChatWindow as ChatDialog
from .models import ProductResult


class MainWindowChatMixin:
    def open_chat(self):
        if self.chat_dialog is None:
            self.chat_dialog = ChatDialog(self)
            self.chat_dialog.setWindowFlags(Qt.Widget)
            self.chat_dialog.set_embedded_mode(True)
            self.chat_dialog.search_requested.connect(self.show_search_page)
            if hasattr(self, "app_stack"):
                self.app_stack.addWidget(self.chat_dialog)
        if hasattr(self, "app_stack"):
            self.app_stack.setCurrentWidget(self.chat_dialog)
        self.chat_open_btn.setObjectName("ChatSideBtnActive")
        self.chat_open_btn.style().unpolish(self.chat_open_btn)
        self.chat_open_btn.style().polish(self.chat_open_btn)

    def share_text_to_chat(self, text: str):
        self.open_chat()
        if self.chat_dialog is not None:
            self.chat_dialog.attach_share_text(text)
        self.set_status(self._tr("chat_share_ready"))

    def share_part_to_chat(self, result: ProductResult):
        self.open_chat()
        if self.chat_dialog is not None and hasattr(self.chat_dialog, "attach_part_card"):
            self.chat_dialog.attach_part_card(result)
        self.set_status(self._tr("chat_share_ready"))
```

- [ ] **Step 4: Wire the mixin and remove duplicate chat bridge methods**

```diff
--- a/digikey_scraper/_main_window.py
+++ b/digikey_scraper/_main_window.py
@@
-from ._main_window_io import MainWindowIoMixin
+from ._main_window_chat import MainWindowChatMixin
+from ._main_window_io import MainWindowIoMixin
@@
 class MainWindow(
     MainWindowCategoryMixin,
     MainWindowPartsMixin,
     MainWindowSearchMixin,
     MainWindowSidebarMixin,
     MainWindowIoMixin,
+    MainWindowChatMixin,
     UiBuilderMixin,
     SharingMixin,
     PartSuggestionsMixin,
     QMainWindow,
 ):
```

- [ ] **Step 5: Rerun chat and runtime verification**

Run:
```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 QT_QPA_PLATFORM=offscreen python3 -m pytest tests/test_chat.py tests/test_windows_runtime.py -q
python3 -m ruff check digikey_scraper/_main_window.py digikey_scraper/_main_window_chat.py tests/test_chat.py
```

Expected:
- chat tests pass
- runtime smoke passes
- ruff passes

- [ ] **Step 6: Commit**

```bash
git add digikey_scraper/_main_window.py digikey_scraper/_main_window_chat.py tests/test_chat.py
git commit -m "refactor(ui): extract main window chat mixin"
```

---

### Task 4: Prepare production-only runtime path

**Files:**
- Modify: `tests/test_windows_runtime.py`

- [ ] **Step 1: Add a production-only structure test**

```python
def test_qt_gui_mainwindow_is_production_window(self) -> None:
    from digikey_scraper.qt_gui import MainWindow as ExportedMainWindow
    from digikey_scraper._main_window import MainWindow as ProductionMainWindow

    self.assertIs(ExportedMainWindow, ProductionMainWindow)
```

- [ ] **Step 2: Mark legacy CircuitKit runtime coverage as removable by naming**

```python
def test_legacy_circuitkit_window_switches_search_and_chat_pages(self) -> None:
    app = QApplication.instance() or QApplication([])
    window = CircuitKitWindow()
    try:
        self.assertEqual(window.page_stack.currentIndex(), 0)
        window._switch_page("chat")
        self.assertEqual(window.page_stack.currentIndex(), 1)
        self.assertEqual(window.active_page, "chat")
        window._open_chat("NE5532P")
        self.assertIn("NE5532P", [p["name"] for p in window.chat_window.composer.attached])
        window._switch_page("search")
        self.assertEqual(window.page_stack.currentIndex(), 0)
    finally:
        window.close()
        app.processEvents()
```

Change only the test name in this step. Do not remove behavior yet.

- [ ] **Step 3: Run runtime tests**

Run:
```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 QT_QPA_PLATFORM=offscreen python3 -m pytest tests/test_windows_runtime.py -q
```

Expected:
- runtime tests pass
- one test name now clearly identifies legacy path

- [ ] **Step 4: Commit**

```bash
git add tests/test_windows_runtime.py
git commit -m "test(runtime): mark legacy circuitkit path explicitly"
```

---

### Task 5: Final phase-1 verification

**Files:**
- Modify: none
- Test: `tests/test_main_window_sidebar.py`
- Test: `tests/test_main_window_io.py`
- Test: `tests/test_main_window_search.py`
- Test: `tests/test_part_suggestions.py`
- Test: `tests/test_category_search.py`
- Test: `tests/test_chat.py`
- Test: `tests/test_windows_runtime.py`

- [ ] **Step 1: Run the focused pytest suite**

Run:
```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 QT_QPA_PLATFORM=offscreen python3 -m pytest \
  tests/test_main_window_sidebar.py \
  tests/test_main_window_io.py \
  tests/test_main_window_search.py \
  tests/test_part_suggestions.py \
  tests/test_category_search.py \
  tests/test_chat.py \
  tests/test_windows_runtime.py -q
```

Expected:
- all selected tests pass

- [ ] **Step 2: Run lint on touched production modules**

Run:
```bash
python3 -m ruff check \
  digikey_scraper/_main_window.py \
  digikey_scraper/_main_window_sidebar.py \
  digikey_scraper/_main_window_io.py \
  digikey_scraper/_main_window_chat.py \
  tests/test_main_window_sidebar.py \
  tests/test_main_window_io.py \
  tests/test_main_window_search.py
```

Expected:
- `All checks passed!`

- [ ] **Step 3: Inspect remaining `_main_window.py` seams**

Run:
```bash
rg -n "^    def " digikey_scraper/_main_window.py
```

Expected:
- mostly coordinator/lifecycle methods remain
- no sidebar/io/chat bridge bodies remain

- [ ] **Step 4: Commit phase-1 completion**

```bash
git add digikey_scraper/_main_window.py \
  digikey_scraper/_main_window_sidebar.py \
  digikey_scraper/_main_window_io.py \
  digikey_scraper/_main_window_chat.py \
  tests/test_main_window_sidebar.py \
  tests/test_main_window_io.py \
  tests/test_main_window_search.py \
  tests/test_chat.py \
  tests/test_windows_runtime.py
git commit -m "refactor(ui): finish main window phase1 split"
```
