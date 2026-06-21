import time
from urllib.parse import quote

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ._helpers import extract_unit_price, price_rows
from ._translations import TRANSLATIONS
from .constants import SEARCH_URL
from .formatters import format_result_text
from .models import ProductResult


class ResultCard(QFrame):
    copy_requested = Signal(str)
    favorite_requested = Signal(str)
    candidate_requested = Signal(str)
    share_requested = Signal(str)
    share_part_requested = Signal(object)

    def __init__(self, index: int, result: ProductResult, favorite: bool,
                 language: str = "ko", query_time: float = 0.0):
        super().__init__()
        self.result = result
        self.lang = language if language in TRANSLATIONS else "ko"
        self._qtime = query_time
        self.setObjectName("Card")
        self.setAttribute(Qt.WA_Hover)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setMinimumWidth(0)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        stripe = QFrame()
        stripe.setObjectName(self._status_stripe_object())
        stripe.setFixedHeight(4)
        root.addWidget(stripe)
        self._build_head(root, index, favorite)
        if result.candidate_results:
            self._build_candidates(root)
        elif result.error:
            self._build_error(root)
        else:
            self._build_kv(root)
            self._build_price(root)
            self._build_footer(root)

    def _t(self, key: str, **kw) -> str:
        _card_tr = {
            "ko": {
                "notice": "안내", "cand_notice": "아래 후보 중 정확한 부품명을 입력해 다시 조회하세요.",
                "cand_label": "후보 {i}", "no_info": "N/A", "error": "오류",
                "description": "설명", "pkg_mount": "패키지 / 실장", "stock": "재고",
                "stock_unit": "개 보유", "power_temp": "전원 / 온도",
                "price_title": "수량별 단가", "best": "최저 ${v}", "discount": "{p}% ↓",
                "qty_hdr": "수량", "unit_hdr": "단가", "total_hdr": "합계",
                "cand_title": "{q} 후보 {n}개", "cand_sub": "정확한 부품명을 골라 다시 조회하세요",
                "datasheet": "데이터시트", "digikey_link": "DigiKey 상세", "buy": "구매",
                "share_chat": "팀 채팅에 공유",
                "retry": "다시 조회",
                "open_search": "DigiKey 열기",
                "qtime": "조회 {t:.1f}s", "status_ok": "정상", "status_err": "오류", "status_cand": "후보",
            },
            "en": {
                "notice": "Notice", "cand_notice": "Select the exact part from candidates and search again.",
                "cand_label": "Candidate {i}", "no_info": "N/A", "error": "Error",
                "description": "Description", "pkg_mount": "Package / Mount", "stock": "Stock",
                "stock_unit": "in stock", "power_temp": "Power / Temp",
                "price_title": "Unit Price by Qty", "best": "Best ${v}", "discount": "{p}% ↓",
                "qty_hdr": "Qty", "unit_hdr": "Unit", "total_hdr": "Total",
                "cand_title": "{q} {n} candidates", "cand_sub": "Pick exact part and search again",
                "datasheet": "Datasheet", "digikey_link": "DigiKey", "buy": "Buy",
                "share_chat": "Share to team chat",
                "retry": "Retry",
                "open_search": "Open DigiKey",
                "qtime": "Query {t:.1f}s", "status_ok": "OK", "status_err": "Error", "status_cand": "Candidates",
            },
        }
        txt = _card_tr.get(self.lang, _card_tr["ko"]).get(key, key)
        return txt.format(**kw) if kw else txt

    def _status_stripe_object(self) -> str:
        if self.result.error:
            return "CardStripeError"
        if self.result.candidate_results:
            return "CardStripeWarn"
        return "CardStripeOk"

    def _status_badge_text(self) -> str:
        if self.result.error:
            return self._t("status_err")
        if self.result.candidate_results:
            return self._t("status_cand")
        return self._t("status_ok")

    def _status_badge_object(self) -> str:
        if self.result.error:
            return "BadgeError"
        if self.result.candidate_results:
            return "BadgeWarn"
        return "BadgeSuccess"

    def _build_head(self, root, index: int, favorite: bool):
        head = QFrame()
        head.setObjectName("CardHead")
        hl = QHBoxLayout(head)
        hl.setContentsMargins(14, 12, 14, 12)
        hl.setSpacing(10)

        num = QLabel(f"{index:02d}")
        num.setObjectName("CardNumber")
        num.setAlignment(Qt.AlignCenter)
        num.setFixedSize(26, 26)
        hl.addWidget(num)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)

        name_row = QHBoxLayout()
        name_row.setSpacing(6)
        name_row.setContentsMargins(0, 0, 0, 0)

        name_lbl = QLabel(self._card_title())
        name_lbl.setObjectName("PartName")
        name_lbl.setWordWrap(True)
        name_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        name_lbl.setMaximumHeight(42)
        name_lbl.setToolTip(self._card_title())
        name_row.addWidget(name_lbl)

        badge = QLabel(self._status_badge_text())
        badge.setObjectName(self._status_badge_object())
        badge.setAlignment(Qt.AlignCenter)
        name_row.addWidget(badge)
        name_row.addStretch()
        title_col.addLayout(name_row)

        sub_lbl = QLabel(self._card_subtitle())
        sub_lbl.setObjectName("CardMaker")
        sub_lbl.setWordWrap(True)
        sub_lbl.setMaximumHeight(34)
        sub_lbl.setToolTip(self._card_subtitle())
        title_col.addWidget(sub_lbl)
        hl.addLayout(title_col, 1)

        fav = QPushButton("★" if favorite else "☆")
        fav.setObjectName("FavOn" if favorite else "FavOff")
        fav.clicked.connect(lambda: self.favorite_requested.emit(self.result.query))
        copy_btn = QPushButton("⧉")
        copy_btn.setObjectName("IconBtn")
        copy_btn.setFixedSize(26, 26)
        copy_btn.clicked.connect(lambda: self.copy_requested.emit(
            format_result_text(self.result, self.lang)
        ))
        share_btn = QPushButton("↗")
        share_btn.setObjectName("IconBtn")
        share_btn.setFixedSize(26, 26)
        share_btn.setToolTip(self._t("share_chat"))
        share_btn.clicked.connect(self._share_to_chat)
        hl.addWidget(fav)
        hl.addWidget(share_btn)
        hl.addWidget(copy_btn)
        root.addWidget(head)

    def _share_to_chat(self) -> None:
        self.share_requested.emit(format_result_text(self.result, self.lang))
        if not self.result.error and not self.result.candidate_results:
            self.share_part_requested.emit(self.result)

    def _card_title(self) -> str:
        if self.result.candidate_results:
            return self._t("cand_title", q=self.result.query, n=len(self.result.candidate_results))
        return self.result.title or self.result.query

    def _card_subtitle(self) -> str:
        if self.result.candidate_results:
            return self._t("cand_sub")
        if self.result.error:
            return self.result.error[:80]
        mfr = self.result.specs.get("제조사", self.result.specs.get("Manufacturer", ""))
        pn = self.result.part_number or ""
        parts = [p for p in [mfr, pn] if p]
        return " · ".join(parts) if parts else self._t("no_info")

    def _build_candidates(self, root):
        body = QFrame()
        gl = QGridLayout(body)
        gl.setContentsMargins(16, 12, 16, 12)
        gl.setHorizontalSpacing(14)
        gl.setVerticalSpacing(8)
        self._kv(gl, 0, self._t("notice"), self._t("cand_notice"))
        for i, cand in enumerate(self.result.candidate_results[:6], start=1):
            label = QLabel(self._t("cand_label", i=i))
            label.setObjectName("KvKey")
            gl.addWidget(label, i, 0)
            btn = QPushButton(f"{cand.title or cand.query} · {cand.part_number or self._t('no_info')}")
            btn.setObjectName("CandidateBtn")
            btn.setToolTip(cand.query or cand.title)
            btn.clicked.connect(
                lambda _checked=False, value=self._candidate_search_value(cand): self.candidate_requested.emit(value)
            )
            gl.addWidget(btn, i, 1)
        root.addWidget(body)

    def _candidate_search_value(self, cand: ProductResult) -> str:
        return (cand.part_number or cand.query or cand.title).strip()

    def _build_error(self, root):
        body = QFrame()
        gl = QGridLayout(body)
        gl.setContentsMargins(16, 12, 16, 8)
        self._kv(gl, 0, self._t("error"), self.result.error or "", error=True)
        actions = QHBoxLayout()
        actions.setContentsMargins(0, 6, 0, 0)
        actions.setSpacing(8)
        retry_btn = QPushButton(self._t("retry"))
        retry_btn.setObjectName("Ghost")
        retry_btn.clicked.connect(lambda: self.candidate_requested.emit(self.result.query))
        open_btn = QPushButton(self._t("open_search"))
        open_btn.setObjectName("Ghost")
        open_btn.clicked.connect(self._open_digikey_search)
        actions.addStretch()
        actions.addWidget(retry_btn)
        actions.addWidget(open_btn)
        action_w = QWidget()
        action_w.setLayout(actions)
        gl.addWidget(action_w, 1, 0, 1, 2)
        root.addWidget(body)

    def _open_digikey_search(self) -> None:
        QDesktopServices.openUrl(QUrl(SEARCH_URL.format(query=quote(self.result.query))))

    def _build_kv(self, root):
        body = QFrame()
        gl = QGridLayout(body)
        gl.setContentsMargins(16, 12, 16, 8)
        gl.setHorizontalSpacing(14)
        gl.setVerticalSpacing(8)
        gl.setColumnMinimumWidth(0, 92)
        gl.setColumnStretch(1, 1)

        row = 0
        self._kv(gl, row, self._t("description"), self.result.title or self._t("no_info"))
        row += 1

        pkg = self.result.specs.get("패키지 / 케이스", self.result.specs.get("Package / Case", ""))
        mount = self.result.specs.get("실장유형", self.result.specs.get("실장 유형",
                self.result.specs.get("Mounting Type", "")))
        status = self.result.specs.get("제품 상태", self.result.specs.get("Part Status", "Active"))

        k_lbl = QLabel(self._t("pkg_mount"))
        k_lbl.setObjectName("KvKey")
        k_lbl.setAlignment(Qt.AlignTop)
        gl.addWidget(k_lbl, row, 0)

        badge_row = QHBoxLayout()
        badge_row.setSpacing(6)
        badge_row.setContentsMargins(0, 0, 0, 0)
        for text in [pkg, mount]:
            if text:
                b = QLabel(text)
                b.setObjectName("BadgeDefault")
                badge_row.addWidget(b)
        if status:
            ok_style = "BadgeSuccess" if "active" in status.lower() else "BadgeWarn"
            b = QLabel(status)
            b.setObjectName(ok_style)
            badge_row.addWidget(b)
        badge_row.addStretch()
        badge_w = QWidget()
        badge_w.setLayout(badge_row)
        gl.addWidget(badge_w, row, 1)
        row += 1

        stock = self.result.specs.get("재고", self.result.specs.get("Quantity Available", ""))
        if stock:
            k_lbl2 = QLabel(self._t("stock"))
            k_lbl2.setObjectName("KvKey")
            gl.addWidget(k_lbl2, row, 0)
            stock_row = QHBoxLayout()
            stock_row.setContentsMargins(0, 0, 0, 0)
            stock_row.setSpacing(6)
            sv = QLabel(stock)
            sv.setObjectName("KvValMono")
            su = QLabel(self._t("stock_unit"))
            su.setObjectName("KvKey")
            stock_row.addWidget(sv)
            stock_row.addWidget(su)
            stock_row.addStretch()
            sw = QWidget()
            sw.setLayout(stock_row)
            gl.addWidget(sw, row, 1)
            row += 1

        vmin = self.result.specs.get("전압 - 범위(최소)", self.result.specs.get("Voltage - Supply, Single/Dual (±) (Min)", ""))
        vmax = self.result.specs.get("전압 - 범위(최대)", self.result.specs.get("Voltage - Supply, Single/Dual (±) (Max)", ""))
        temp = self.result.specs.get("작동 온도", self.result.specs.get("Operating Temperature", ""))
        parts = []
        if vmin or vmax:
            parts.append(f"{vmin} ~ {vmax}".strip(" ~"))
        if temp:
            parts.append(temp)
        if parts:
            self._kv(gl, row, self._t("power_temp"), "  ·  ".join(parts))

        root.addWidget(body)

    def _kv(self, layout: QGridLayout, row: int, key: str, val: str, error: bool = False):
        k = QLabel(key)
        k.setObjectName("KvKey")
        k.setAlignment(Qt.AlignTop)
        k.setMinimumWidth(92)
        v = QLabel(val)
        v.setObjectName("KvErr" if error else "KvVal")
        v.setWordWrap(True)
        v.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(k, row, 0)
        layout.addWidget(v, row, 1)

    def _freshness_text(self) -> str:
        """Human relative time since the price was scraped, so users don't act
        on stale data (FRESH5)."""
        ts = getattr(self.result, "scraped_at", None)
        if not ts:
            return ""
        delta = max(0, int(time.time() - ts))
        ko = self.lang == "ko"
        if delta < 45:
            return "방금 업데이트" if ko else "Updated just now"
        if delta < 3600:
            n = max(1, delta // 60)
            return f"{n}분 전 업데이트" if ko else f"Updated {n} min ago"
        if delta < 86400:
            n = delta // 3600
            return f"{n}시간 전 업데이트" if ko else f"Updated {n}h ago"
        n = delta // 86400
        return f"{n}일 전 업데이트" if ko else f"Updated {n}d ago"

    def _build_price(self, root):
        if not self.result.price_rows:
            return
        rows = price_rows(self.result.price_rows)
        unit_prices = [extract_unit_price(r[1]) for r in rows if r[1]]
        if not unit_prices:
            return
        top_unit = unit_prices[0]
        best_unit = min(unit_prices)

        section = QFrame()
        section.setObjectName("PriceSection")
        vl = QVBoxLayout(section)
        vl.setContentsMargins(16, 4, 16, 12)
        vl.setSpacing(4)

        ph = QHBoxLayout()
        ph.setContentsMargins(0, 0, 0, 4)
        pt = QLabel(self._t("price_title"))
        pt.setObjectName("PriceTitle")
        ph.addWidget(pt)
        fresh = self._freshness_text()
        if fresh:
            fl = QLabel(fresh)
            fl.setObjectName("PriceFreshness")
            fl.setStyleSheet("color:#8E96AE; font-size:11px; padding-left:8px;")
            ph.addWidget(fl)
        ph.addStretch()
        if top_unit > 0 and best_unit < top_unit:
            disc = int(((top_unit - best_unit) / top_unit) * 100)
            best_txt = f"최저 ${best_unit:.4f}  ·  {disc}% ↓" if self.lang == "ko" else f"Best ${best_unit:.4f}  ·  {disc}% ↓"
        else:
            best_txt = f"${best_unit:.4f}" if best_unit < float("inf") else ""
        if best_txt:
            bb = QLabel(best_txt)
            bb.setObjectName("PriceBestBadge")
            ph.addWidget(bb)
        vl.addLayout(ph)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(0)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 0)
        grid.setColumnStretch(3, 0)
        grid.setColumnMinimumWidth(0, 48)
        grid.setColumnMinimumWidth(1, 82)

        for col, hdr in enumerate([self._t("qty_hdr"), self._t("unit_hdr"),
                                    self._t("total_hdr"), ""]):
            lbl = QLabel(hdr)
            lbl.setObjectName("PriceHdr")
            lbl.setAlignment(Qt.AlignLeft if col == 0 else Qt.AlignRight)
            if col == 2:
                lbl.setMaximumWidth(86)
            if col == 3:
                lbl.setMaximumWidth(44)
            grid.addWidget(lbl, 0, col)

        for i, (qty_s, unit_s, ext_s) in enumerate(rows, start=1):
            is_best = abs(extract_unit_price(unit_s) - best_unit) < 1e-9 if unit_s else False
            grid_row = i * 2 - 1
            q_lbl = QLabel(qty_s)
            q_lbl.setObjectName("PriceBestQty" if is_best else "PriceQty")
            q_lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            grid.addWidget(q_lbl, grid_row, 0)

            u_lbl = QLabel(unit_s)
            u_lbl.setObjectName("PriceBestCell" if is_best else "PriceCell")
            u_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            u_lbl.setMinimumWidth(82)
            grid.addWidget(u_lbl, grid_row, 1)

            e_lbl = QLabel(ext_s)
            e_lbl.setObjectName("PriceBestCell" if is_best else "PriceCell")
            e_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            e_lbl.setMaximumWidth(86)
            e_lbl.setToolTip(ext_s)
            grid.addWidget(e_lbl, grid_row, 2)

            uv = extract_unit_price(unit_s)
            if i == 1 or top_unit <= 0:
                sav_lbl = QLabel("—")
                sav_lbl.setObjectName("PriceSavingsDash")
            else:
                pct = int(((top_unit - uv) / top_unit) * 100)
                sav_lbl = QLabel(f"−{pct}%")
                sav_lbl.setObjectName("PriceSavings")
            sav_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            sav_lbl.setMaximumWidth(44)
            grid.addWidget(sav_lbl, grid_row, 3)

            if i < len(rows):
                div = QFrame()
                div.setObjectName("PriceRowDiv")
                div.setFixedHeight(1)
                grid.addWidget(div, grid_row + 1, 0, 1, 4)
                grid.setRowMinimumHeight(grid_row + 1, 1)

        vl.addLayout(grid)
        root.addWidget(section)

    def _build_footer(self, root):
        footer = QFrame()
        footer.setObjectName("CardFooter")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(12, 6, 12, 6)
        fl.setSpacing(2)

        if self.result.datasheet_url:
            ds = QPushButton(f"PDF {self._t('datasheet')}")
            ds.setObjectName("FooterPrimary")
            ds.clicked.connect(self._open_datasheet)
            fl.addWidget(ds)
            fl.addWidget(self._sep())

        if self.result.product_url:
            dk = QPushButton(self._t("digikey_link"))
            dk.setObjectName("FooterLink")
            dk.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.result.product_url)))
            fl.addWidget(dk)
            fl.addWidget(self._sep())

            buy = QPushButton(f"↗ {self._t('buy')}")
            buy.setObjectName("FooterLinkMuted")
            buy.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.result.product_url)))
            fl.addWidget(buy)

        fl.addStretch()

        if self._qtime > 0:
            t_lbl = QLabel(self._t("qtime", t=self._qtime))
            t_lbl.setObjectName("FooterTime")
            fl.addWidget(t_lbl)

        root.addWidget(footer)

    def _open_datasheet(self):
        from .datasheet_viewer import open_datasheet
        self._ds_viewer = open_datasheet(self.result.datasheet_url, self.result.title, self.lang, parent=self)

    def _sep(self) -> QLabel:
        s = QLabel()
        s.setObjectName("FooterSep")
        s.setFixedSize(1, 14)
        return s
