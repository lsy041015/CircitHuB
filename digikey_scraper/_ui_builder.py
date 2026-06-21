"""Qt widget construction for MainWindow, extracted as a mixin.

Pure view assembly (no business logic). MainWindow inherits this so the bulk of
``_build_*`` code lives outside the main module. All methods rely on attributes
and callbacks defined on the concrete MainWindow instance.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
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

from ._widgets import FlowLayout, NewSearchButton, ToggleSwitch


class UiBuilderMixin:
    def _build_ui(self):
        stage = QWidget()
        stage.setObjectName("Stage")
        outer = QVBoxLayout(stage)
        outer.setContentsMargins(0, 0, 0, 0)

        window = QFrame()
        window.setObjectName("Window")
        wl = QVBoxLayout(window)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.setSpacing(0)
        outer.addWidget(window)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        wl.addLayout(body, 1)
        body.addWidget(self._build_sidebar())
        self.app_stack = QStackedWidget()
        self.search_page = self._build_main()
        self.app_stack.addWidget(self.search_page)
        self.category_page = self._build_category_page()
        self.app_stack.addWidget(self.category_page)
        body.addWidget(self.app_stack, 1)
        self.setCentralWidget(stage)

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(264)
        vl = QVBoxLayout(sidebar)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        hdr = QWidget()
        hdr_l = QHBoxLayout(hdr)
        hdr_l.setContentsMargins(18, 20, 18, 14)
        hdr_l.setSpacing(10)
        logo = QLabel("CK")
        logo.setObjectName("LogoBadge")
        logo.setAlignment(Qt.AlignCenter)
        logo.setFixedSize(32, 32)
        hdr_l.addWidget(logo)
        name_col = QVBoxLayout()
        name_col.setSpacing(1)
        app_name = QLabel("CircuitKit")
        app_name.setObjectName("AppName")
        self.sidebar_desc = QLabel("")
        self.sidebar_desc.setObjectName("AppDesc")
        name_col.addWidget(app_name)
        name_col.addWidget(self.sidebar_desc)
        hdr_l.addLayout(name_col)
        hdr_l.addStretch()
        vl.addWidget(hdr)

        self.new_search_btn = NewSearchButton()
        self.new_search_btn.clicked.connect(self.new_search)
        ns_wrap = QWidget()
        ns_l = QHBoxLayout(ns_wrap)
        ns_l.setContentsMargins(14, 0, 14, 14)
        ns_l.addWidget(self.new_search_btn)
        vl.addWidget(ns_wrap)

        self.category_side_btn = QPushButton("")
        self.category_side_btn.setObjectName("CategorySideBtn")
        self.category_side_btn.clicked.connect(self.show_category_page)
        cat_wrap = QWidget()
        cat_l = QHBoxLayout(cat_wrap)
        cat_l.setContentsMargins(14, 0, 14, 6)
        cat_l.addWidget(self.category_side_btn)
        vl.addWidget(cat_wrap)

        self.chat_open_btn = QPushButton("")
        self.chat_open_btn.setObjectName("ChatSideBtn")
        self.chat_open_btn.clicked.connect(self.open_chat)
        chat_wrap = QWidget()
        chat_l = QHBoxLayout(chat_wrap)
        chat_l.setContentsMargins(14, 0, 14, 12)
        chat_l.addWidget(self.chat_open_btn)
        vl.addWidget(chat_wrap)

        self.ai_chat_btn = QPushButton("AI 채팅")
        self.ai_chat_btn.setObjectName("AiChatSideBtn")
        self.ai_chat_btn.clicked.connect(self.toggle_ai_chat_dock)
        ai_chat_wrap = QWidget()
        ai_chat_l = QHBoxLayout(ai_chat_wrap)
        ai_chat_l.setContentsMargins(14, 0, 14, 6)
        ai_chat_l.addWidget(self.ai_chat_btn)
        vl.addWidget(ai_chat_wrap)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setObjectName("SidebarScroll")
        body_w = QWidget()
        body_w.setObjectName("SidebarBody")
        body_l = QVBoxLayout(body_w)
        body_l.setContentsMargins(0, 0, 0, 0)
        body_l.setSpacing(0)

        hist_hdr = self._side_section_header("", "hist_count")
        body_l.addWidget(hist_hdr)
        self.history_container = QWidget()
        self.history_container_layout = QVBoxLayout(self.history_container)
        self.history_container_layout.setContentsMargins(6, 0, 6, 4)
        self.history_container_layout.setSpacing(1)
        body_l.addWidget(self.history_container)

        fav_hdr = self._side_section_header("", "fav_count")
        body_l.addWidget(fav_hdr)
        self.fav_container = QWidget()
        self.fav_container_layout = QVBoxLayout(self.fav_container)
        self.fav_container_layout.setContentsMargins(6, 0, 6, 4)
        self.fav_container_layout.setSpacing(1)
        body_l.addWidget(self.fav_container)
        body_l.addStretch(1)

        scroll.setWidget(body_w)
        vl.addWidget(scroll, 1)

        footer = QFrame()
        footer.setObjectName("SideFooter")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(14, 10, 14, 12)
        fl.setSpacing(10)

        dk_avatar = QLabel("DK")
        dk_avatar.setObjectName("DKAvatar")
        dk_avatar.setAlignment(Qt.AlignCenter)
        dk_avatar.setFixedSize(28, 28)
        fl.addWidget(dk_avatar)

        info_col = QVBoxLayout()
        info_col.setSpacing(1)
        self.footer_name = QLabel("")
        self.footer_name.setObjectName("FooterName")
        self.footer_meta = QLabel("")
        self.footer_meta.setObjectName("FooterMeta")
        info_col.addWidget(self.footer_name)
        info_col.addWidget(self.footer_meta)
        fl.addLayout(info_col, 1)

        gear = QPushButton("⚙")
        gear.setObjectName("GearBtn")
        gear.clicked.connect(self.focus_settings)
        fl.addWidget(gear)
        vl.addWidget(footer)

        self._hist_hdr_ref = hist_hdr
        self._fav_hdr_ref = fav_hdr
        return sidebar

    def _side_section_header(self, title_key: str, count_attr: str) -> QWidget:
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(18, 8, 18, 4)
        row.setSpacing(6)
        lbl = QLabel("")
        lbl.setObjectName("SectionTitle")
        cnt = QLabel("0")
        cnt.setObjectName("CountBadge")
        row.addWidget(lbl)
        row.addStretch()
        row.addWidget(cnt)
        setattr(self, f"_{count_attr}_lbl", lbl)
        setattr(self, f"_{count_attr}_cnt", cnt)
        return w

    def _build_main(self) -> QWidget:
        main = QFrame()
        main.setObjectName("Main")
        vl = QVBoxLayout(main)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        hdr = QFrame()
        hdr.setObjectName("Header")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(28, 18, 28, 14)
        hl.setSpacing(18)
        title_col = QVBoxLayout()
        self.header_title = QLabel("")
        self.header_title.setObjectName("Title")
        self.header_sub = QLabel("")
        self.header_sub.setObjectName("Subtitle")
        title_col.addWidget(self.header_title)
        title_col.addWidget(self.header_sub)
        hl.addLayout(title_col, 1)
        self.import_bom_btn = QPushButton("")
        self.import_bom_btn.clicked.connect(self.import_bom)
        self.save_results_btn = QPushButton("")
        self.save_results_btn.clicked.connect(self.save_results_as)
        hl.addWidget(self.import_bom_btn)
        hl.addWidget(self.save_results_btn)
        vl.addWidget(hdr)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        content = QWidget()
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(28, 18, 28, 24)
        self.content_layout.setSpacing(10)
        self.scroll.setWidget(content)
        vl.addWidget(self.scroll, 1)

        self._build_input_panel()
        self._build_status_strip()
        self._build_results_area()

        sb = QFrame()
        sb.setObjectName("Statusbar")
        sb.setFixedHeight(28)
        sl = QHBoxLayout(sb)
        sl.setContentsMargins(14, 0, 14, 0)
        sl.setSpacing(12)
        self.sb_connected = QLabel("")
        self.sb_connected.setObjectName("SbOk")
        self.sb_api = QLabel("DigiKey API")
        self.sb_api.setObjectName("SbItem")
        self.sb_cache = QLabel("")
        self.sb_cache.setObjectName("SbItem")
        sl.addWidget(self.sb_connected)
        sl.addWidget(self.sb_api)
        sl.addWidget(self.sb_cache)
        sl.addStretch()
        self.sb_parts = QLabel("")
        self.sb_parts.setObjectName("SbItem")
        self.sb_timeout = QLabel("")
        self.sb_timeout.setObjectName("SbItem")
        sl.addWidget(self.sb_parts)
        sl.addWidget(self.sb_timeout)
        vl.addWidget(sb)
        return main

    def _build_input_panel(self):
        panel = QFrame()
        panel.setObjectName("InputPanel")
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setSpacing(0)

        top = QFrame()
        top.setObjectName("PanelTop")
        tl = QHBoxLayout(top)
        tl.setContentsMargins(14, 9, 14, 9)
        tl.setSpacing(12)
        self.panel_tag = QLabel("")
        self.panel_tag.setObjectName("PanelTagLabel")
        tl.addWidget(self.panel_tag)
        self.panel_helper = QLabel("")
        self.panel_helper.setObjectName("PanelHelper")
        tl.addWidget(self.panel_helper, 1)
        self.example_btn = QPushButton("")
        self.example_btn.setObjectName("Ghost")
        self.example_btn.clicked.connect(self.load_example)
        self.clear_btn = QPushButton("")
        self.clear_btn.setObjectName("DangerGhost")
        self.clear_btn.clicked.connect(self.clear_parts)
        tl.addWidget(self.example_btn)
        tl.addWidget(self.clear_btn)
        pl.addWidget(top)

        self.chip_area = QFrame()
        self.chip_area.setObjectName("ChipArea")
        self.chip_area.setMinimumHeight(110)
        self.chip_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.chip_area.mousePressEvent = lambda e: self._chip_input.setFocus()

        self._chip_flow = FlowLayout(h_spacing=7, v_spacing=7)
        self._chip_flow.setContentsMargins(14, 10, 14, 10)
        self.chip_area.setLayout(self._chip_flow)

        self._chip_input = QLineEdit()
        self._chip_input.setObjectName("ChipLineEdit")
        self._chip_input.setFrame(False)
        self._chip_input.setMinimumWidth(200)
        self._chip_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._chip_input.setFixedHeight(28)
        self._chip_input.returnPressed.connect(self.commit_input)
        self._chip_input.textEdited.connect(self._on_chip_text_edited)
        self._chip_flow.addWidget(self._chip_input)
        pl.addWidget(self.chip_area)

        opts = QFrame()
        opts.setObjectName("OptionsRow")
        ol = QHBoxLayout(opts)
        ol.setContentsMargins(14, 10, 14, 10)
        ol.setSpacing(16)

        tg = QHBoxLayout()
        tg.setSpacing(7)
        tg.addWidget(QLabel("⏱"))
        self.timeout_label_w = QLabel("")
        self.timeout_label_w.setObjectName("OptLabel")
        tg.addWidget(self.timeout_label_w)
        self.timeout_input = QLineEdit(self.timeout_default)
        self.timeout_input.setObjectName("NumInput")
        self.timeout_input.setFixedWidth(58)
        self.timeout_input.setFixedHeight(28)
        tg.addWidget(self.timeout_input)
        self.seconds_label_w = QLabel("")
        self.seconds_label_w.setObjectName("OptLabel")
        tg.addWidget(self.seconds_label_w)
        ol.addLayout(tg)

        bg = QHBoxLayout()
        bg.setSpacing(8)
        self.browser_toggle = ToggleSwitch(self.show_browser_default)
        self.browser_toggle.toggled.connect(lambda _: self.save_settings())
        bg.addWidget(self.browser_toggle)
        self.browser_label_w = QLabel("")
        self.browser_label_w.setObjectName("OptLabel")
        bg.addWidget(self.browser_label_w)
        ol.addLayout(bg)

        ag = QHBoxLayout()
        ag.setSpacing(8)
        self.auto_save_toggle = ToggleSwitch(self.auto_save_default)
        self.auto_save_toggle.toggled.connect(lambda _: self.save_settings())
        ag.addWidget(self.auto_save_toggle)
        self.auto_save_label_w = QLabel("")
        self.auto_save_label_w.setObjectName("OptLabel")
        ag.addWidget(self.auto_save_label_w)
        ol.addLayout(ag)

        sg = QHBoxLayout()
        sg.setSpacing(7)
        self.share_toggle_btn = QPushButton("≋")
        self.share_toggle_btn.setObjectName("Ghost")
        self.share_toggle_btn.setFixedHeight(28)
        self.share_toggle_btn.clicked.connect(self.toggle_share_controls)
        sg.addWidget(self.share_toggle_btn)
        self.share_label_w = QLabel("")
        self.share_label_w.setObjectName("OptLabel")
        sg.addWidget(self.share_label_w)

        self.share_controls = QWidget()
        share_controls_l = QHBoxLayout(self.share_controls)
        share_controls_l.setContentsMargins(0, 0, 0, 0)
        share_controls_l.setSpacing(6)
        self.peer_ip = QLineEdit()
        self.peer_ip.setText(self.peer_ip_default)
        self.peer_ip.setPlaceholderText("192.168.0.10")
        self.peer_ip.setFixedWidth(120)
        self.peer_ip.setFixedHeight(28)
        self.share_port = QLineEdit(self.share_port_default)
        self.share_port.setFixedWidth(58)
        self.share_port.setFixedHeight(28)
        share_controls_l.addWidget(self.peer_ip)
        share_controls_l.addWidget(QLabel(":"))
        share_controls_l.addWidget(self.share_port)
        self.send_btn = QPushButton("↗")
        self.send_btn.setObjectName("Ghost")
        self.send_btn.setFixedSize(32, 28)
        self.send_btn.clicked.connect(self.start_send_share)
        self.restart_rx_btn = QPushButton("↺")
        self.restart_rx_btn.setObjectName("Ghost")
        self.restart_rx_btn.setFixedSize(32, 28)
        self.restart_rx_btn.clicked.connect(self.restart_receiver)
        share_controls_l.addWidget(self.send_btn)
        share_controls_l.addWidget(self.restart_rx_btn)
        self.share_controls.setVisible(self.share_controls_visible_default)
        sg.addWidget(self.share_controls)
        ol.addLayout(sg)

        ol.addStretch()

        self.cancel_btn = QPushButton("")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_search)
        ol.addWidget(self.cancel_btn)

        self.run_btn = QPushButton("")
        self.run_btn.setObjectName("Primary")
        self.run_btn.clicked.connect(self.start_search)
        ol.addWidget(self.run_btn)
        pl.addWidget(opts)

        self.content_layout.addWidget(panel)

        self.timeout_input.editingFinished.connect(self.save_settings)
        self.peer_ip.editingFinished.connect(self.save_settings)
        self.share_port.editingFinished.connect(self.save_settings)

    def _build_status_strip(self):
        self.status_strip = QFrame()
        self.status_strip.setObjectName("StripNeutral")
        sl = QHBoxLayout(self.status_strip)
        sl.setContentsMargins(14, 9, 14, 9)
        sl.setSpacing(10)

        self.strip_dot = QLabel("●")
        self.strip_dot.setFixedSize(10, 10)
        self.strip_dot.setStyleSheet("color:#10B981; font-size:9px;")
        sl.addWidget(self.strip_dot)

        self.strip_main = QLabel("")
        self.strip_main.setObjectName("StripText")
        sl.addWidget(self.strip_main)

        self.strip_extra = QLabel("")
        self.strip_extra.setObjectName("StripText")
        sl.addWidget(self.strip_extra)

        sl.addStretch()

        self.strip_done_tag = QLabel("")
        self.strip_done_tag.setObjectName("StripDoneTag")
        sl.addWidget(self.strip_done_tag)

        self.strip_bar = QProgressBar()
        self.strip_bar.setObjectName("StripBar")
        self.strip_bar.setRange(0, 100)
        self.strip_bar.setValue(0)
        self.strip_bar.setFixedWidth(120)
        self.strip_bar.setFixedHeight(4)
        self.strip_bar.setTextVisible(False)
        sl.addWidget(self.strip_bar)

        self.content_layout.addWidget(self.status_strip)

    def _build_results_area(self):
        head = QHBoxLayout()
        self.results_title = QLabel("")
        self.results_title.setObjectName("ResultsTitle")
        self.results_count = QLabel("")
        self.results_count.setObjectName("ResultCount")
        head.addWidget(self.results_title)
        head.addWidget(self.results_count)
        head.addStretch()

        tab_bar = QFrame()
        tab_bar.setObjectName("TabBar")
        tab_l = QHBoxLayout(tab_bar)
        tab_l.setContentsMargins(2, 2, 2, 2)
        tab_l.setSpacing(0)
        self.card_btn = QPushButton("")
        self.card_btn.setObjectName("TabBtnActive")
        self.card_btn.setMinimumWidth(86)
        self.card_btn.setToolTip("Card view")
        self.card_btn.clicked.connect(lambda: self.switch_tab("cards"))
        self.text_btn = QPushButton("")
        self.text_btn.setObjectName("TabBtn")
        self.text_btn.setMinimumWidth(86)
        self.text_btn.setToolTip("Text view")
        self.text_btn.clicked.connect(lambda: self.switch_tab("text"))
        tab_l.addWidget(self.card_btn)
        tab_l.addWidget(self.text_btn)
        head.addWidget(tab_bar)
        self.content_layout.addLayout(head)

        self.filter_bar = self._build_filter_bar()
        self.content_layout.addWidget(self.filter_bar)

        self.result_stack = QStackedWidget()
        self.card_page = QWidget()
        self.card_grid = QGridLayout(self.card_page)
        self.card_grid.setContentsMargins(0, 0, 0, 0)
        self.card_grid.setSpacing(14)
        self.text_result = QTextEdit()
        self.text_result.setObjectName("TextResult")
        self.text_result.setReadOnly(True)
        self.result_stack.addWidget(self.card_page)
        self.result_stack.addWidget(self.text_result)
        self.content_layout.addWidget(self.result_stack)
        self.switch_tab("cards")
        self.render_results()

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

    @staticmethod
    def _make_symbol_pixmap(svg: str, w: int = 60, h: int = 32) -> "QPixmap":
        from PySide6.QtCore import QByteArray
        from PySide6.QtGui import QImage, QPainter, QPixmap
        from PySide6.QtSvg import QSvgRenderer

        scale = 2  # render at 2× for HiDPI
        img = QImage(w * scale, h * scale, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(0)
        painter = QPainter(img)
        QSvgRenderer(QByteArray(svg.encode())).render(painter)
        painter.end()
        pix = QPixmap.fromImage(img)
        pix.setDevicePixelRatio(scale)
        return pix

    def _build_category_page(self) -> QWidget:
        from ._circuit_symbols import CIRCUIT_SVGS
        from ._keyword_map import CATEGORIES

        page = QWidget()
        page.setObjectName("CategoryPage")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(0)

        title_row = QWidget()
        title_row_l = QHBoxLayout(title_row)
        title_row_l.setContentsMargins(0, 0, 0, 0)
        title_row_l.setSpacing(12)

        self.category_page_title = QLabel("")
        self.category_page_title.setObjectName("CategoryPageTitle")
        title_row_l.addWidget(self.category_page_title)
        title_row_l.addStretch(1)

        self.category_back_btn = QPushButton("")
        self.category_back_btn.setObjectName("CategoryBackBtn")
        self.category_back_btn.clicked.connect(self.show_search_page)
        title_row_l.addWidget(self.category_back_btn)

        self.category_last_badge = QLabel("")
        self.category_last_badge.setObjectName("CategoryLastBadge")
        self.category_page_sub = QLabel("")
        self.category_page_sub.setObjectName("CategoryPageSub")
        self.category_page_sub.setWordWrap(True)
        outer.addWidget(title_row)
        outer.addSpacing(4)
        outer.addWidget(self.category_last_badge)
        outer.addSpacing(6)
        outer.addWidget(self.category_page_sub)
        outer.addSpacing(14)

        hint_card = QFrame()
        hint_card.setObjectName("CategoryHintCard")
        hint_l = QVBoxLayout(hint_card)
        hint_l.setContentsMargins(14, 12, 14, 12)
        hint_l.setSpacing(4)
        self.category_hint_title = QLabel("")
        self.category_hint_title.setObjectName("CategoryHintTitle")
        self.category_hint_body = QLabel("")
        self.category_hint_body.setObjectName("CategoryHintBody")
        self.category_hint_body.setWordWrap(True)
        hint_l.addWidget(self.category_hint_title)
        hint_l.addWidget(self.category_hint_body)
        outer.addWidget(hint_card)
        outer.addSpacing(20)

        grid_w = QWidget()
        grid = QGridLayout(grid_w)
        grid.setSpacing(10)
        grid.setContentsMargins(0, 0, 0, 0)

        self._category_tile_buttons: list[QFrame] = []
        cols = 4
        for idx, cat in enumerate(CATEGORIES):
            # QFrame renders child labels properly on all platforms.
            # QPushButton overlays native paint on Linux, hiding child widgets.
            tile = QFrame()
            tile.setObjectName("CategoryTile")
            tile.setFrameShape(QFrame.StyledPanel)
            tile.setFrameShadow(QFrame.Plain)
            tile.setCursor(Qt.PointingHandCursor)
            tile.setMinimumSize(90, 90)

            vl = QVBoxLayout(tile)
            vl.setContentsMargins(8, 10, 8, 8)
            vl.setSpacing(3)

            svg_str = CIRCUIT_SVGS.get(cat["key"])
            if svg_str:
                symbol_lbl = QLabel()
                symbol_lbl.setPixmap(self._make_symbol_pixmap(svg_str, 60, 32))
                symbol_lbl.setObjectName("TileSymbol")
                symbol_lbl.setAlignment(Qt.AlignHCenter)
                vl.addWidget(symbol_lbl)
            else:
                icon_lbl = QLabel(cat["icon"])
                icon_lbl.setObjectName("TileIcon")
                icon_lbl.setAlignment(Qt.AlignHCenter)
                vl.addWidget(icon_lbl)

            ko_lbl = QLabel(cat["label_ko"])
            ko_lbl.setObjectName("TileKo")
            ko_lbl.setAlignment(Qt.AlignHCenter)
            en_lbl = QLabel(cat["label_en"])
            en_lbl.setObjectName("TileEn")
            en_lbl.setAlignment(Qt.AlignHCenter)
            vl.addWidget(ko_lbl)
            vl.addWidget(en_lbl)

            # Python dynamic mousePressEvent — no subclass needed
            def _make_handler(c: dict):
                def _on_press(event):
                    if event.button() == Qt.LeftButton:
                        self.search_category(c)
                return _on_press

            tile.mousePressEvent = _make_handler(cat)  # type: ignore[method-assign]
            grid.addWidget(tile, idx // cols, idx % cols)
            self._category_tile_buttons.append(tile)

        outer.addWidget(grid_w)
        outer.addSpacing(20)

        self.category_result_area = QScrollArea()
        self.category_result_area.setWidgetResizable(True)
        self.category_result_area.setObjectName("ResultScroll")
        outer.addWidget(self.category_result_area, 1)

        return page
