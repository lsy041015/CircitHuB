from __future__ import annotations

import threading

from ._result_card import ResultCard
from .category_presenter import (
    category_badge_text,
    category_result_payload,
    category_strip_payload,
)
from .workers import CategorySignals, CategoryWorker


class MainWindowCategoryMixin:
    def _apply_category_language(self) -> None:
        if hasattr(self, "category_page_title"):
            self.category_page_title.setText(self._tr("category_title"))
        if hasattr(self, "category_back_btn"):
            self.category_back_btn.setText(self._tr("category_back_to_search"))
        if hasattr(self, "category_page_sub"):
            self.category_page_sub.setText(self._tr("category_subtitle"))
        if hasattr(self, "category_hint_title"):
            self.category_hint_title.setText(self._tr("category_hint_title"))
        if hasattr(self, "category_hint_body"):
            self.category_hint_body.setText(self._tr("category_hint_body"))
        if hasattr(self, "category_last_badge"):
            self._refresh_category_badge()
        if not hasattr(self, "category_result_area"):
            return
        if self._category_results:
            self._render_category_results(self._category_results)
            return
        self._set_category_result_message(
            self._category_feedback_state,
            label=self._category_feedback_label,
            error=self._category_feedback_error,
        )

    def _refresh_category_badge(self) -> None:
        if hasattr(self, "category_last_badge"):
            self.category_last_badge.setText(
                category_badge_text(self._tr, self._category_feedback_label)
            )

    def show_search_page(self):
        if hasattr(self, "app_stack") and hasattr(self, "search_page"):
            self.app_stack.setCurrentWidget(self.search_page)
        if hasattr(self, "chat_open_btn"):
            self.chat_open_btn.setObjectName("ChatSideBtn")
            self.chat_open_btn.style().unpolish(self.chat_open_btn)
            self.chat_open_btn.style().polish(self.chat_open_btn)
        if hasattr(self, "category_side_btn"):
            self.category_side_btn.setObjectName("CategorySideBtn")
            self.category_side_btn.style().unpolish(self.category_side_btn)
            self.category_side_btn.style().polish(self.category_side_btn)

    def show_category_page(self):
        if hasattr(self, "app_stack") and hasattr(self, "category_page"):
            self.app_stack.setCurrentWidget(self.category_page)
        if not self._category_results:
            self._set_category_result_message(
                self._category_feedback_state,
                label=self._category_feedback_label,
                error=self._category_feedback_error,
            )
        if hasattr(self, "category_side_btn"):
            self.category_side_btn.setObjectName("CategorySideBtnActive")
            self.category_side_btn.style().unpolish(self.category_side_btn)
            self.category_side_btn.style().polish(self.category_side_btn)
        if hasattr(self, "chat_open_btn"):
            self.chat_open_btn.setObjectName("ChatSideBtn")
            self.chat_open_btn.style().unpolish(self.chat_open_btn)
            self.chat_open_btn.style().polish(self.chat_open_btn)

    def search_category(self, category: dict) -> None:
        if self.is_searching:
            return
        self._category_results = []
        self._category_feedback_label = category["label_ko"]
        self._category_feedback_error = ""
        self._set_category_result_message("searching", label=category["label_ko"])
        self._set_search_state(True)
        state, main, detail, progress = category_strip_payload(
            self._tr, "searching", label=category["label_ko"]
        )
        self._set_strip(state, main, detail, progress=progress)
        self.set_status(f"{category['label_ko']} 카테고리 검색 중...")

        self._category_signals = CategorySignals()
        self._category_signals.finished.connect(self._on_category_finished)
        self._category_signals.failed.connect(self._on_category_failed)

        show_browser = self.browser_toggle.isChecked() if hasattr(self, "browser_toggle") else False
        self._category_worker = CategoryWorker(
            category=category,
            show_browser=show_browser,
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
        self._set_search_state(False)
        self._category_results = list(results)
        count = len(results)
        if count:
            state, main, detail, progress = category_strip_payload(
                self._tr, "success", label=self._category_feedback_label, count=count
            )
            self._set_strip(state, main, detail, progress=progress)
        else:
            state, main, detail, progress = category_strip_payload(
                self._tr, "empty", label=self._category_feedback_label
            )
            self._set_strip(state, main, detail, progress=progress)
        self._render_category_results(self._category_results)

    def _on_category_failed(self, error: str) -> None:
        self._set_search_state(False)
        self._category_results = []
        self._category_feedback_error = error
        state, main, detail, progress = category_strip_payload(
            self._tr, "error", label=self._category_feedback_label, error=error
        )
        self._set_strip(state, main, detail, progress=progress)
        self._set_category_result_message("error", label=self._category_feedback_label, error=error)
        self.set_status(f"오류: {error}")

    def _render_category_results(self, results: list) -> None:
        from PySide6.QtWidgets import QGridLayout, QWidget

        prev = self.category_result_area.widget()
        if prev:
            prev.deleteLater()

        if not results:
            self._set_category_result_message("empty", label=self._category_feedback_label)
            return

        self._category_feedback_state = "success"
        self._category_feedback_error = ""
        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(12)
        grid.setContentsMargins(0, 0, 0, 0)
        cols = max(1, self._result_columns())
        for i, result in enumerate(results):
            card = ResultCard(i + 1, result, False, self.language)
            card.favorite_requested.connect(self.toggle_favorite)
            card.candidate_requested.connect(self.search_candidate)
            grid.addWidget(card, i // cols, i % cols)

        self.category_result_area.setWidget(container)

    def _set_category_result_message(self, stage: str, *, label: str = "", error: str = "") -> None:
        from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

        self._category_feedback_state = stage
        self._category_feedback_label = label
        self._category_feedback_error = error
        self._refresh_category_badge()

        prev = self.category_result_area.widget()
        if prev:
            prev.deleteLater()

        title, detail = category_result_payload(self._tr, stage, label=label, error=error)
        container = QWidget()
        outer = QVBoxLayout(container)
        outer.setContentsMargins(0, 12, 0, 0)
        outer.addStretch()

        card = QFrame()
        card.setObjectName("CategoryEmptyCard")
        body = QVBoxLayout(card)
        body.setContentsMargins(18, 18, 18, 18)
        body.setSpacing(6)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("CategoryEmptyTitle")
        detail_lbl = QLabel(detail)
        detail_lbl.setObjectName("CategoryEmptyBody")
        detail_lbl.setWordWrap(True)
        body.addWidget(title_lbl)
        body.addWidget(detail_lbl)
        outer.addWidget(card)
        outer.addStretch()
        self.category_result_area.setWidget(container)
