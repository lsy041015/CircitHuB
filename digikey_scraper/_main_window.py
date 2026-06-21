import socket
import sys
import threading
from typing import TYPE_CHECKING

from PySide6.QtCore import QStringListModel, Qt
from PySide6.QtWidgets import (
    QApplication,
    QCompleter,
    QFrame,
    QLabel,
    QMainWindow,
    QVBoxLayout,
)
from selenium import webdriver

from ._circuitkit_chat_design import CircuitKitChatWindow as ChatDialog
from ._helpers import (
    AUTO_SAVE_DIR,
    SETTINGS_FILE,
    normalize_part_query,
    price_rows,
    runtime_path,
    split_part_tokens,
)
from ._main_window_category import MainWindowCategoryMixin
from ._main_window_chat import MainWindowChatMixin
from ._main_window_io import MainWindowIoMixin
from ._main_window_parts import MainWindowPartsMixin
from ._main_window_search import MainWindowSearchMixin
from ._main_window_sidebar import MainWindowSidebarMixin
from ._result_card import ResultCard
from ._sharing_mixin import SharingMixin
from ._stylesheet import APP_QSS
from ._translations import TRANSLATIONS
from ._ui_builder import UiBuilderMixin
from ._widgets import (
    PartChip,
)
from .constants import DEFAULT_SHARE_PORT
from .models import ProductResult
from .workers import UiSignals

__all__ = ["MainWindow", "ChatDialog", "main"]

# Part-suggestion corpus + ranking helpers live in _parts_mixin.
# _spell_match_score is re-exported for backward compatibility (tests import
# it from this module).
from ._parts_mixin import PartSuggestionsMixin, _spell_match_score  # noqa: E402,F401

if TYPE_CHECKING:
    from .workers import CategorySignals, CategoryWorker, SearchSignals, SearchWorker


class MainWindow(
    MainWindowChatMixin,
    MainWindowCategoryMixin,
    MainWindowPartsMixin,
    MainWindowSearchMixin,
    MainWindowSidebarMixin,
    MainWindowIoMixin,
    UiBuilderMixin,
    SharingMixin,
    PartSuggestionsMixin,
    QMainWindow,
):
    def __init__(self, container=None):
        super().__init__()
        from .container import build_container

        self.container = container or build_container()
        self.settings_store = self.container.settings
        self.result_repository = self.container.results
        self.language = "ko"
        self._status_message = ""
        self._strip_state = "neutral"  # neutral | searching | success | cancelled | error
        self._last_bom_total = 0.0
        self._last_avg_time = 0.0
        self._query_times: list[float] = []
        self._last_query_ts = 0.0
        self._category_worker: CategoryWorker | None = None
        self._category_thread: threading.Thread | None = None
        self._category_signals: CategorySignals | None = None
        self._category_results: list[ProductResult] = []
        self._category_feedback_state = "idle"
        self._category_feedback_label = ""
        self._category_feedback_error = ""

        self.setWindowTitle(self._tr("window_title"))
        self.resize(1120, 760)
        self.setMinimumSize(900, 620)

        self.settings_path = runtime_path(SETTINGS_FILE)
        self.auto_save_dir = runtime_path(AUTO_SAVE_DIR)

        loaded = self._load_settings()
        self.parts = self._sanitize_parts(loaded.get("parts")) or self._default_parts()
        self.results: list[ProductResult] = []
        self.history: list[tuple[str, list[str], str, str]] = []  # (label, queries, meta, status)
        self.favorites: set[str] = set(
            normalize_part_query(x)
            for x in loaded.get("favorites", ["LM358P"])
            if normalize_part_query(x)
        ) or {"LM358P"}
        self.favorite_prices: dict[str, str] = {}
        self.latest_share_text = ""
        self._skip_next_chip_commit = False

        try:
            tv = int(loaded.get("timeout", 15))
            self.timeout_default = str(tv if tv > 0 else 15)
        except (TypeError, ValueError):
            self.timeout_default = "15"

        self.show_browser_default = bool(loaded.get("show_browser", False))
        self.peer_ip_default = str(loaded.get("peer_ip", ""))
        try:
            sp = int(loaded.get("share_port", DEFAULT_SHARE_PORT))
            self.share_port_default = str(sp if 1 <= sp <= 65535 else DEFAULT_SHARE_PORT)
        except (TypeError, ValueError):
            self.share_port_default = str(DEFAULT_SHARE_PORT)
        self.auto_save_default = bool(loaded.get("auto_save_enabled", False))
        self.share_controls_visible_default = bool(loaded.get("share_controls_visible", False))

        lang = str(loaded.get("language", "ko")).lower()
        self.language = lang if lang in TRANSLATIONS else "ko"

        self.receiver_socket: socket.socket | None = None
        self.receiver_running = False
        self.worker: SearchWorker | None = None
        self.search_thread: threading.Thread | None = None
        self.search_signals: SearchSignals | None = None
        self.chat_dialog: ChatDialog | None = None
        self.ui_signals = UiSignals()
        self.ui_signals.status.connect(self.set_status)
        self.ui_signals.status_key.connect(self.set_status_key)
        self.ui_signals.received_share.connect(self.show_received_share)
        self.current_driver: webdriver.Chrome | None = None
        self.is_searching = False
        self.search_started_at = 0.0
        self.search_total = 0
        self._last_result_columns = 0
        self.tab_var = "cards"
        self._part_suggestion_model: QStringListModel | None = None
        self._part_completer: QCompleter | None = None

        self._sort_key: str = "none"
        self._filter_type: str | None = None
        self._filter_spec_min: float | None = None
        self._filter_spec_max: float | None = None
        self._filter_hide_errors: bool = False
        self._build_ui()
        self._setup_part_completer()
        self._apply_language()
        self._set_category_result_message("idle")
        self.start_receiver()
        self._setup_ai_chat_dock()

    def _default_parts(self):
        return [
            {"name": "LM358P", "qty": 1},
            {"name": "TL072CP", "qty": 1},
            {"name": "NE5532P", "qty": 1},
        ]

    def _sanitize_parts(self, raw) -> list:
        if not isinstance(raw, list):
            return []
        out = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            n = normalize_part_query(item.get("name", ""))
            if not n:
                continue
            try:
                q = max(1, int(item.get("qty", 1)))
            except (TypeError, ValueError):
                q = 1
            out.append({"name": n, "qty": q})
        return out

    def _load_settings(self) -> dict:
        return self.settings_store.load()

    def save_settings(self):
        try:
            to = (
                int(self.timeout_input.text().strip())
                if hasattr(self, "timeout_input")
                else int(self.timeout_default)
            )
        except ValueError:
            to = 15
        try:
            port = (
                int(self.share_port.text().strip())
                if hasattr(self, "share_port")
                else int(self.share_port_default)
            )
            if not 1 <= port <= 65535:
                raise ValueError
        except ValueError:
            port = DEFAULT_SHARE_PORT
        data = {
            "timeout": to,
            "show_browser": self.browser_toggle.isChecked()
            if hasattr(self, "browser_toggle")
            else self.show_browser_default,
            "peer_ip": self.peer_ip.text().strip()
            if hasattr(self, "peer_ip")
            else self.peer_ip_default,
            "share_port": port,
            "share_controls_visible": (
                self.share_controls.isVisible()
                if hasattr(self, "share_controls")
                else self.share_controls_visible_default
            ),
            "auto_save_enabled": self.auto_save_toggle.isChecked()
            if hasattr(self, "auto_save_toggle")
            else self.auto_save_default,
            "parts": self.parts,
            "favorites": sorted(self.favorites),
            "language": self.language,
        }
        self.settings_store.save(data)

    def _tr(self, key: str, **kw) -> str:
        txt = TRANSLATIONS.get(self.language, TRANSLATIONS["ko"]).get(key, key)
        return txt.format(**kw) if kw else txt

    def render_chips(self):
        while self._chip_flow.count():
            item = self._chip_flow.takeAt(0)
            w = item.widget()
            if w and w is not self._chip_input:
                w.deleteLater()

        for part in self.parts:
            chip = PartChip(part["name"], part["qty"])
            chip.remove_requested.connect(self.remove_part)
            chip.quantity_changed.connect(self.set_part_quantity)
            chip.setEnabled(not self.is_searching)
            self._chip_flow.addWidget(chip)

        self._chip_flow.addWidget(self._chip_input)
        self._chip_input.setPlaceholderText(
            self._tr("part_placeholder_more") if self.parts else self._tr("part_placeholder")
        )
        self.chip_area.updateGeometry()
        self._refresh_part_suggestions()

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

    def render_results(self):
        from ._filter_sort import apply_filter, apply_sort, detect_component_type

        # filter bar visibility + type combo refresh
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

        # build filtered+sorted display list
        display = apply_filter(
            self.results,
            self._filter_type,
            self._filter_spec_min,
            self._filter_spec_max,
            self._filter_hide_errors,
        )
        display = apply_sort(display, self._sort_key)

        # --- existing card-clear logic continues below ---
        while self.card_grid.count():
            item = self.card_grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        for c in range(max(self._last_result_columns, 1) + 1):
            self.card_grid.setColumnStretch(c, 0)
            self.card_grid.setColumnMinimumWidth(c, 0)

        len(self.parts)
        done = len(self.results)
        if done:
            errors = sum(1 for result in self.results if result.error)
            candidates = sum(1 for result in self.results if result.candidate_results)
            suffix = []
            if errors:
                suffix.append(f"ERR {errors}")
            if candidates:
                suffix.append(f"CAND {candidates}")
            self.results_count.setText(f"{done}" + (f" · {' · '.join(suffix)}" if suffix else ""))
        else:
            self.results_count.setText("")

        cols = self._result_columns()
        self._last_result_columns = cols
        for c in range(cols):
            self.card_grid.setColumnStretch(c, 1)
            self.card_grid.setColumnMinimumWidth(c, 0)

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
                orig_idx = next(
                    (j for j, r in enumerate(self.results) if r is result), i
                )
                qt = self._query_times[orig_idx] if orig_idx < len(self._query_times) else 0.0
                card = ResultCard(i + 1, result, result.query in self.favorites, self.language, qt)
                card.copy_requested.connect(self.copy_text)
                card.favorite_requested.connect(self.toggle_favorite)
                card.candidate_requested.connect(self.search_candidate)
                card.share_requested.connect(self.share_text_to_chat)
                card.share_part_requested.connect(self.share_part_to_chat)
                self.card_grid.addWidget(card, i // cols, i % cols)

        self.text_result.setPlainText(self.latest_share_text or self._tr("text_result_fallback"))

    def _result_columns(self) -> int:
        vw = self.scroll.viewport().width() if hasattr(self, "scroll") else self.width()
        if vw >= 1100:
            return 3
        if vw >= 700:
            return 2
        return 1

    def _on_language_changed(self, code: str):
        if code == self.language:
            return
        self.language = code
        self._apply_language()
        self.save_settings()

    def _update_run_button(self):
        if self.is_searching:
            self.run_btn.setText(self._tr("searching"))
        else:
            n = len(self.parts)
            suffix = f"  {n}" if n > 0 else ""
            self.run_btn.setText(f"▶  {self._tr('run_search')}{suffix}")

    def focus_settings(self):
        self.share_controls.setVisible(True)
        self.share_toggle_btn.setText("⌃")
        self.timeout_input.setFocus()
        self.set_status("설정 영역을 열었습니다.")
        self.save_settings()

    def _set_strip(
        self,
        state: str,
        main_text: str,
        extra_text: str = "",
        done_tag: str = "",
        progress: int = 0,
    ):
        name_map = {
            "neutral": "StripNeutral",
            "searching": "StripSearching",
            "success": "StripSuccess",
            "cancelled": "StripCancelled",
            "error": "StripError",
        }
        text_obj_map = {
            "neutral": "StripText",
            "searching": "StripTextBlue",
            "success": "StripText",
            "cancelled": "StripTextWarn",
            "error": "StripTextErr",
        }
        dot_color_map = {
            "neutral": "#94A3B8",
            "searching": "#3B68F1",
            "success": "#10B981",
            "cancelled": "#F59E0B",
            "error": "#EF4444",
        }
        bar_obj_map = {
            "searching": "StripBarBlue",
            "success": "StripBar",
            "cancelled": "StripBar",
            "error": "StripBar",
        }

        self.status_strip.setObjectName(name_map.get(state, "StripNeutral"))
        self.status_strip.setStyleSheet("")
        self.status_strip.style().unpolish(self.status_strip)
        self.status_strip.style().polish(self.status_strip)

        text_obj = text_obj_map.get(state, "StripText")
        self.strip_main.setObjectName(text_obj)
        self.strip_main.setText(main_text)
        self.strip_extra.setObjectName(text_obj)
        self.strip_extra.setText(extra_text)
        self.strip_done_tag.setText(done_tag)

        dot_c = dot_color_map.get(state, "#94A3B8")
        self.strip_dot.setStyleSheet(f"color:{dot_c}; font-size:9px;")

        bar_obj = bar_obj_map.get(state, "StripBar")
        self.strip_bar.setObjectName(bar_obj)
        self.strip_bar.setValue(progress)

    def _on_chip_text_edited(self, text: str):
        self._refresh_part_suggestions(text)
        if any(sep in text for sep in [",", ";", "\n", "\t"]):
            self.commit_input()

    def commit_input(self):
        if getattr(self, "_skip_next_chip_commit", False):
            self._skip_next_chip_commit = False
            self._chip_input.clear()
            return
        text = self._chip_input.text()
        for tok in split_part_tokens(text):
            self.add_part(tok)
        self._chip_input.clear()

    def toggle_share_controls(self):
        visible = not self.share_controls.isVisible()
        self.share_controls.setVisible(visible)
        self.share_toggle_btn.setText("⌃" if visible else "≋")
        self.save_settings()

    def switch_tab(self, tab: str):
        self.tab_var = tab
        is_cards = tab == "cards"
        self.result_stack.setCurrentIndex(0 if is_cards else 1)
        self.card_btn.setObjectName("TabBtnActive" if is_cards else "TabBtn")
        self.text_btn.setObjectName("TabBtnActive" if not is_cards else "TabBtn")
        for btn in [self.card_btn, self.text_btn]:
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not hasattr(self, "card_grid"):
            return
        if self._result_columns() != self._last_result_columns:
            self.render_results()

    def set_status(self, message: str, _progress=None):
        self._status_message = message
        self.sb_cache.setText(message)

    def set_status_key(self, key: str, values=None):
        values = values or {}
        self.set_status(self._tr(key, **values))

    def get_share_port(self) -> int:
        try:
            port = int(self.share_port.text().strip())
            if not 1 <= port <= 65535:
                raise ValueError
            return port
        except ValueError as exc:
            raise ValueError(self._tr("port_error")) from exc

    def toggle_favorite(self, name: str):
        if name in self.favorites:
            self.favorites.discard(name)
            self.favorite_prices.pop(name, None)
        else:
            self.favorites.add(name)
            for r in self.results:
                if r.query == name and not r.error and r.price_rows:
                    rows = price_rows(r.price_rows)
                    if rows and rows[0][1]:
                        self.favorite_prices[name] = rows[0][1]
        self.render_sidebar_lists()
        self.render_results()
        self.save_settings()

    def closeEvent(self, event):
        if self.worker:
            self.worker.cancel()
        self.save_settings()
        self.stop_receiver()
        if self.chat_dialog is not None:
            self.chat_dialog.close()
            self.chat_dialog = None
        if self.current_driver:
            try:
                self.current_driver.quit()
            except Exception:
                pass
        event.accept()


def main():
    from .container import build_container

    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(APP_QSS)
    w = MainWindow(build_container())
    w.show()
    sys.exit(app.exec())
