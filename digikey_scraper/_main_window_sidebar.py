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
        self.browser_label_w.setToolTip(self._tr("show_browser_tooltip"))
        self.browser_toggle.setToolTip(self._tr("show_browser_tooltip"))
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
        if hasattr(self, "_apply_category_language"):
            self._apply_category_language()

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
