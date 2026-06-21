"""Chat display widgets extracted from _circuitkit_chat_design.py.

Holds AvatarLabel, PartEmbed, MessageWidget and ChannelsColumn so the main
chat window module stays focused on CircuitKitChatWindow orchestration.
"""

from __future__ import annotations

import webbrowser

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ._chat_data import AVATAR_COLORS, PRESENCE_COLORS

# ─────────────────────────────────────────────
#  아바타 위젯
# ─────────────────────────────────────────────
class AvatarLabel(QLabel):
    def __init__(self, initials, color_key, size=38, radius=11, font_size=13, parent=None):
        super().__init__(initials, parent)
        grad, _ = AVATAR_COLORS.get(color_key, AVATAR_COLORS['jw'])
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(
            f"QLabel{{background:{grad};color:white;font-weight:700;"
            f"font-size:{font_size}px;border-radius:{radius}px;}}"
        )


# ─────────────────────────────────────────────
#  부품 임베드 카드
# ─────────────────────────────────────────────
class PartEmbed(QFrame):
    def __init__(self, part, parent=None):
        super().__init__(parent)
        self.setObjectName('part_embed')
        self.setMaximumWidth(460)
        self.setStyleSheet("""
            QFrame#part_embed{background:white;border:1px solid #E4E7EC;
                border-left:3px solid #3B68F1;border-radius:10px;}
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 헤더
        head = QWidget()
        hl = QHBoxLayout(head)
        hl.setContentsMargins(13, 11, 13, 9)
        hl.setSpacing(10)

        icon = QLabel('IC')
        icon.setFixedSize(30, 30)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("background:#EEF4FF;color:#2952D6;border-radius:8px;font-size:16px;")
        hl.addWidget(icon)

        info = QVBoxLayout()
        info.setSpacing(2)
        name_row = QHBoxLayout()
        name_row.setSpacing(7)
        name_lbl = QLabel(part['name'])
        name_lbl.setStyleSheet("font-family:'Consolas',monospace;font-weight:700;font-size:14px;color:#0F172A;")
        name_row.addWidget(name_lbl)
        if part.get('best'):
            b = QLabel('추천')
            b.setStyleSheet("background:#EEF4FF;color:#1E3FAF;font-size:10px;font-weight:700;"
                            "border-radius:4px;padding:1px 6px;")
            name_row.addWidget(b)
        if part.get('cheapest'):
            b = QLabel('최저가')
            b.setStyleSheet("background:#ECFDF5;color:#047857;font-size:10px;font-weight:700;"
                            "border-radius:4px;padding:1px 6px;")
            name_row.addWidget(b)
        name_row.addStretch()
        maker = QLabel(f"{part['maker']} · {part['digikey']}")
        maker.setStyleSheet("font-size:11px;color:#94A3B8;")
        info.addLayout(name_row)
        info.addWidget(maker)
        hl.addLayout(info, 1)

        price_col = QVBoxLayout()
        price_col.setSpacing(1)
        price_col.setAlignment(Qt.AlignRight)
        amt = QLabel(part['price'])
        amt.setAlignment(Qt.AlignRight)
        amt.setStyleSheet("font-family:'Consolas',monospace;font-weight:700;font-size:16px;color:#0F172A;")
        unit = QLabel(part['priceUnit'])
        unit.setAlignment(Qt.AlignRight)
        unit.setStyleSheet("font-size:10px;color:#94A3B8;")
        price_col.addWidget(amt)
        price_col.addWidget(unit)
        hl.addLayout(price_col)
        root.addWidget(head)

        # 배지
        meta = QWidget()
        ml = QHBoxLayout(meta)
        ml.setContentsMargins(13, 0, 13, 11)
        ml.setSpacing(6)
        for txt, style in [
            (part['package'],  "background:#F4F5F7;color:#475569;"),
            (part['mount'],    "background:#F4F5F7;color:#475569;"),
            (f"● {part['status']}", "background:#ECFDF5;color:#047857;"),
        ]:
            badge = QLabel(txt)
            badge.setStyleSheet(f"QLabel{{font-size:11px;font-weight:500;border-radius:999px;"
                                f"padding:2px 8px;border:1px solid #E4E7EC;{style}}}")
            ml.addWidget(badge)
        ml.addStretch()
        root.addWidget(meta)

        # 풋터
        foot = QFrame()
        foot.setStyleSheet("QFrame{background:#FCFCFD;border-top:1px solid #EDF0F3;"
                           "border-bottom-left-radius:10px;border-bottom-right-radius:10px;}")
        fl = QHBoxLayout(foot)
        fl.setContentsMargins(13, 8, 13, 8)
        fl.setSpacing(6)
        for txt, url_key, color in [
            ('데이터시트 뷰어', 'datasheet_url', '#2952D6'),
            ('↗ DigiKey', 'digikey_url', '#2952D6'),
        ]:
            b = QPushButton(txt)
            b.setStyleSheet(f"QPushButton{{border:none;background:transparent;color:{color};"
                            f"font-size:12px;font-weight:500;border-radius:6px;padding:3px 7px;}}"
                            f"QPushButton:hover{{background:#EEF4FF;}}")
            b.setCursor(Qt.PointingHandCursor)
            url = str(part.get(url_key, "") or "")
            b.setEnabled(bool(url))
            if url:
                if url_key == 'datasheet_url':
                    b.clicked.connect(lambda _checked=False, target=url: self._open_datasheet(target, part))
                else:
                    b.clicked.connect(lambda _checked=False, target=url: self._open_external(target))
            else:
                b.setToolTip("링크 없음")
            fl.addWidget(b)
        fl.addStretch()
        stock_text = self._stock_text(part.get("stock", ""))
        if stock_text:
            stock = QLabel(stock_text)
            stock.setStyleSheet("font-size:11px;color:#047857;")
            fl.addWidget(stock)
        root.addWidget(foot)

    def _stock_text(self, value):
        text = str(value or "").strip()
        if not text:
            return ""
        if text.startswith("✓"):
            return text
        if text.startswith("재고"):
            return f"✓ {text}"
        return f"✓ 재고 {text}"

    def _open_datasheet(self, url, part):
        try:
            from .datasheet_viewer import open_datasheet

            self._ds_viewer = open_datasheet(url, str(part.get("name") or "Datasheet"), "ko", parent=self)
        except Exception:
            self._open_external(url)

    def _open_external(self, url):
        target = str(url or "").strip()
        if not target:
            return
        ok = QDesktopServices.openUrl(QUrl.fromUserInput(target))
        if not ok:
            webbrowser.open(target)


# ─────────────────────────────────────────────
#  메시지 위젯
# ─────────────────────────────────────────────
class MessageWidget(QFrame):
    react_clicked = Signal(str, object)  # msg_id, reaction_index or emoji str
    thread_clicked = Signal(str)
    pin_clicked = Signal(str)
    save_clicked = Signal(str)

    def __init__(self, msg, parent=None):
        super().__init__(parent)
        self.msg = msg
        self._build()

    def _build(self):
        m = self.msg
        grouped = m.get('grouped', False)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(24, 4 if grouped else 6, 24, 4 if grouped else 6)
        outer.setSpacing(11)
        outer.setAlignment(Qt.AlignTop)

        # 아바타 슬롯
        av_slot = QWidget()
        av_slot.setFixedWidth(38)
        av_layout = QVBoxLayout(av_slot)
        av_layout.setContentsMargins(0, 0, 0, 0)
        av_layout.setAlignment(Qt.AlignTop)
        if grouped:
            ts_lbl = QLabel(m.get('ts', ''))
            ts_lbl.setStyleSheet("color:#94A3B8;font-size:10px;font-family:'Consolas',monospace;")
            ts_lbl.setAlignment(Qt.AlignCenter)
            av_layout.addWidget(ts_lbl)
        else:
            av = AvatarLabel(m['initials'], m['color'])
            av_layout.addWidget(av)
        outer.addWidget(av_slot)

        # 본문
        body = QVBoxLayout()
        body.setSpacing(4)
        body.setAlignment(Qt.AlignTop)

        if not grouped:
            meta = QHBoxLayout()
            meta.setSpacing(8)
            author_lbl = QLabel(m['author'])
            author_lbl.setStyleSheet("font-size:14px;font-weight:700;color:#0F172A;")
            meta.addWidget(author_lbl)
            if m.get('bot'):
                bot_tag = QLabel('앱')
                bot_tag.setStyleSheet("background:#DCE7FF;color:#1E3FAF;font-size:9px;font-weight:700;"
                                      "border-radius:4px;padding:1px 5px;")
                meta.addWidget(bot_tag)
            ts_lbl = QLabel(m.get('ts', ''))
            ts_lbl.setStyleSheet("font-size:11px;color:#94A3B8;")
            meta.addWidget(ts_lbl)
            meta.addStretch()
            for label, active, signal in [
                ('저장됨' if m.get('saved') else '저장', bool(m.get('saved')), self.save_clicked),
                ('고정됨' if m.get('pinned') else '핀', bool(m.get('pinned')), self.pin_clicked),
            ]:
                action = QPushButton(label)
                action.setFixedHeight(22)
                action.setCursor(Qt.PointingHandCursor)
                action.setStyleSheet(
                    "QPushButton{border:none;background:#EEF4FF;color:#1E3FAF;"
                    "border-radius:6px;font-size:10px;font-weight:700;padding:0 7px;}"
                    if active else
                    "QPushButton{border:none;background:transparent;color:#94A3B8;"
                    "border-radius:6px;font-size:10px;font-weight:600;padding:0 7px;}"
                    "QPushButton:hover{background:#F4F5F7;color:#0F172A;}"
                )
                action.clicked.connect(lambda _=False, id_=m['id'], sig=signal: sig.emit(id_))
                meta.addWidget(action)
            body.addLayout(meta)

        # 텍스트
        if m.get('text'):
            text_lbl = QLabel(m['text'])
            text_lbl.setStyleSheet("font-size:14px;color:#0F172A;line-height:1.5;")
            text_lbl.setWordWrap(True)
            text_lbl.setTextFormat(Qt.RichText)
            body.addWidget(text_lbl)

        # 부품 임베드
        for part in (m.get('parts') or []):
            body.addWidget(PartEmbed(part))

        # 파일 임베드
        if m.get('file'):
            body.addWidget(self._file_widget(m['file']))
        for f in (m.get('files') or []):
            body.addWidget(self._file_widget(f))

        # 리액션
        if m.get('reactions'):
            react_row = QHBoxLayout()
            react_row.setSpacing(6)
            react_row.setAlignment(Qt.AlignLeft)
            for i, r in enumerate(m['reactions']):
                rb = QPushButton(f"{r['emo']}  {r['count']}")
                rb.setCursor(Qt.PointingHandCursor)
                if r.get('mine'):
                    rb.setStyleSheet("QPushButton{background:#EEF4FF;border:1px solid #D5E0FF;"
                                     "border-radius:999px;color:#1E3FAF;font-size:12px;"
                                     "font-weight:600;padding:0 8px;height:24px;}"
                                     "QPushButton:hover{border-color:#3B68F1;}")
                else:
                    rb.setStyleSheet("QPushButton{background:white;border:1px solid #E4E7EC;"
                                     "border-radius:999px;color:#475569;font-size:12px;"
                                     "font-weight:600;padding:0 8px;height:24px;}"
                                     "QPushButton:hover{border-color:#D0D5DD;}")
                idx = i
                rb.clicked.connect(lambda _, idx=idx: self.react_clicked.emit(m['id'], idx))
                react_row.addWidget(rb)
            add_btn = QPushButton('+')
            add_btn.setFixedSize(28, 24)
            add_btn.setCursor(Qt.PointingHandCursor)
            add_btn.setStyleSheet("QPushButton{background:transparent;border:1px solid #E4E7EC;"
                                  "border-radius:999px;color:#94A3B8;font-size:13px;}"
                                  "QPushButton:hover{background:#F4F5F7;}")
            add_btn.clicked.connect(lambda _=False, mid=m['id']: self._show_emoji_react_menu(mid, add_btn))
            react_row.addWidget(add_btn)
            react_row.addStretch()
            body.addLayout(react_row)

        # 스레드 뱃지
        if m.get('thread'):
            t = m['thread']
            thread_frame = QFrame()
            thread_frame.setCursor(Qt.PointingHandCursor)
            thread_frame.setStyleSheet("QFrame{background:white;border:1px solid #E4E7EC;"
                                       "border-radius:999px;}"
                                       "QFrame:hover{border-color:#D0D5DD;}")
            tl = QHBoxLayout(thread_frame)
            tl.setContentsMargins(6, 4, 10, 4)
            tl.setSpacing(7)
            for initials, color in t['avatars']:
                av = AvatarLabel(initials, color, size=20, radius=6, font_size=9)
                tl.addWidget(av)
            tl.addWidget(QLabel(f"답글 {t['count']}개",
                                styleSheet="color:#2952D6;font-size:12px;font-weight:600;"))
            tl.addWidget(QLabel(f"마지막 답글 {t['last']}",
                                styleSheet="color:#94A3B8;font-size:11px;"))
            thread_frame.mousePressEvent = lambda e, id_=m['id']: self.thread_clicked.emit(id_)
            body.addWidget(thread_frame)

        outer.addLayout(body, 1)

    def enterEvent(self, event):
        self.setStyleSheet("QFrame{background:#F8F9FB;}")
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet("")
        super().leaveEvent(event)

    def _show_emoji_react_menu(self, msg_id: str, anchor) -> None:
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        for emoji in ['👍', '✅', '🔧', '📌', '⚠️', '🎉', '❤️', '👀']:
            menu.addAction(emoji, lambda e=emoji: self.react_clicked.emit(msg_id, e))
        menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))

    def _file_widget(self, f):
        file_frame = QFrame()
        file_frame.setStyleSheet("QFrame{background:white;border:1px solid #E4E7EC;"
                                 "border-radius:10px;}")
        file_frame.setMaximumWidth(380)
        fl = QHBoxLayout(file_frame)
        fl.setContentsMargins(13, 10, 13, 10)
        fl.setSpacing(11)
        name = str(f.get('name') or 'file')
        ext = name.rsplit('.', 1)[-1].upper()[:4] if '.' in name else 'FILE'
        meta = str(f.get('meta') or f.get('size_text') or '')
        path = str(f.get('path') or '')
        fi_icon = QLabel(ext)
        fi_icon.setFixedSize(36, 36)
        fi_icon.setAlignment(Qt.AlignCenter)
        fi_icon.setStyleSheet("background:#FEF2F2;border-radius:8px;font-size:11px;font-weight:800;")
        fl.addWidget(fi_icon)
        fi_info = QVBoxLayout()
        fi_info.setSpacing(1)
        fi_info.addWidget(QLabel(name, styleSheet="font-size:13px;font-weight:600;color:#0F172A;"))
        fi_info.addWidget(QLabel(meta, styleSheet="font-size:11px;color:#94A3B8;"))
        fl.addLayout(fi_info, 1)
        dl = QPushButton('↓')
        dl.setFixedSize(30, 30)
        dl.setStyleSheet("QPushButton{border:1px solid #E4E7EC;background:white;border-radius:7px;"
                         "color:#475569;font-size:14px;}"
                         "QPushButton:hover{background:#F4F5F7;}"
                         "QPushButton:disabled{color:#CBD5E1;background:#F8FAFC;}")
        dl.setCursor(Qt.PointingHandCursor)
        dl.setEnabled(bool(path))
        if path:
            dl.clicked.connect(lambda _=False, p=path: QDesktopServices.openUrl(QUrl.fromLocalFile(p)))
        fl.addWidget(dl)
        return file_frame


# ─────────────────────────────────────────────
#  채널 목록 컬럼
# ─────────────────────────────────────────────
class ChannelsColumn(QFrame):
    channel_selected = Signal(str)
    room_removed = Signal(str)
    room_add_requested = Signal(str)
    new_message_requested = Signal()

    def __init__(self, channels, dms, active_id, parent=None):
        super().__init__(parent)
        self.channels = channels
        self.dms = dms
        self.active_id = active_id
        self.ch_open = True
        self.dm_open = True
        self.item_widgets = {}
        self.badge_widgets = {}
        self.item_labels = {}
        self.group_items = {"channel": [], "dm": []}
        self.group_headers = {}
        self._build()
        self.setObjectName('ch_col')
        self.setFixedWidth(248)
        self.setStyleSheet("""
            QFrame#ch_col{background:#F8F9FB;border-right:1px solid #E4E7EC;}
        """)

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 워크스페이스 헤더
        hdr = QFrame()
        hdr.setFixedHeight(52)
        hdr.setStyleSheet("border-bottom:1px solid #E4E7EC;")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(16, 0, 16, 0)
        hl.setSpacing(8)
        info = QVBoxLayout(); info.setSpacing(0)
        info.addWidget(QLabel('하드웨어팀', styleSheet="font-weight:700;font-size:14px;color:#0F172A;"))
        info.addWidget(QLabel('멤버 14 · 온라인 6', styleSheet="font-size:11px;color:#94A3B8;"))
        hl.addLayout(info, 1)
        new_msg = QPushButton('↗')
        new_msg.setFixedSize(28, 28)
        new_msg.setToolTip('새 메시지')
        new_msg.setCursor(Qt.PointingHandCursor)
        new_msg.setStyleSheet("QPushButton{border:none;background:transparent;color:#94A3B8;"
                              "border-radius:6px;font-size:15px;}"
                              "QPushButton:hover{background:#EEF0F3;color:#0F172A;}")
        new_msg.clicked.connect(self.new_message_requested.emit)
        hl.addWidget(new_msg)
        root.addWidget(hdr)

        # 검색창
        search = QFrame()
        search.setStyleSheet("QFrame{background:white;border:1px solid #E4E7EC;"
                             "border-radius:8px;margin:12px 12px 6px 12px;}")
        sl = QHBoxLayout(search)
        sl.setContentsMargins(12, 0, 12, 0)
        sl.setSpacing(0)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('메시지 · 채널 검색')
        self.search_input.setFixedHeight(32)
        self.search_input.setStyleSheet("QLineEdit{border:none;background:transparent;font-size:12px;color:#0F172A;}")
        self.search_input.textChanged.connect(self._filter_items)
        sl.addWidget(self.search_input, 1)
        root.addWidget(search)

        # 채널 + DM 스크롤
        scroll = QScrollArea()
        scroll.setObjectName('ch_scroll')
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        content = QWidget()
        content.setStyleSheet("background:transparent;")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(8, 6, 8, 14)
        cl.setSpacing(0)

        # 채널 그룹
        cl.addWidget(self._group_header('채널', self.ch_open, 'channel'))
        for c in self.channels:
            w = self._channel_item(c['id'], '#  ' + c['name'], c.get('unread', 0), is_dm=False)
            self.item_widgets[c['id']] = w
            self.group_items["channel"].append(c['id'])
            cl.addWidget(w)
        cl.addSpacing(8)

        # DM 그룹
        cl.addWidget(self._group_header('다이렉트 메시지', self.dm_open, 'dm'))
        for d in self.dms:
            w = self._dm_item(d)
            self.item_widgets[d['id']] = w
            self.group_items["dm"].append(d['id'])
            cl.addWidget(w)

        cl.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, 1)
        self._update_active()

    def _group_header(self, title, open_, group_kind):
        w = QFrame()
        wl = QHBoxLayout(w)
        wl.setContentsMargins(10, 6, 10, 4)
        wl.setSpacing(6)
        chev = QLabel('▾' if open_ else '▸')
        chev.setStyleSheet("color:#94A3B8;font-size:11px;")
        wl.addWidget(chev)
        lbl = QLabel(title)
        lbl.setStyleSheet("font-size:11px;font-weight:600;color:#94A3B8;letter-spacing:1px;")
        wl.addWidget(lbl, 1)
        add = QPushButton('+')
        add.setFixedSize(18, 18)
        add.setCursor(Qt.PointingHandCursor)
        add.setStyleSheet("QPushButton{border:none;background:transparent;color:#94A3B8;"
                          "border-radius:4px;font-size:14px;}"
                          "QPushButton:hover{background:#EEF0F3;color:#0F172A;}")
        add.clicked.connect(lambda _checked=False, kind=group_kind: self.room_add_requested.emit(kind))
        wl.addWidget(add)
        w.setCursor(Qt.PointingHandCursor)
        w.mousePressEvent = lambda e, kind=group_kind: self._toggle_group(kind)
        self.group_headers[group_kind] = chev
        return w

    def _toggle_group(self, kind):
        if kind == "channel":
            self.ch_open = not self.ch_open
            open_ = self.ch_open
        else:
            self.dm_open = not self.dm_open
            open_ = self.dm_open
        header = self.group_headers.get(kind)
        if header is not None:
            header.setText('▾' if open_ else '▸')
        for cid in self.group_items.get(kind, []):
            widget = self.item_widgets.get(cid)
            if widget is not None:
                widget.setVisible(open_)

    def _channel_item(self, cid, label, unread, is_dm=False):
        w = QFrame()
        w.setObjectName('ch_item')
        w.setCursor(Qt.PointingHandCursor)
        wl = QHBoxLayout(w)
        wl.setContentsMargins(10, 6, 10, 6)
        wl.setSpacing(6)
        lbl = QLabel(label)
        lbl.setObjectName('ch_label')
        lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        wl.addWidget(lbl)
        badge = QLabel(str(unread))
        badge.setObjectName('ch_badge')
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedHeight(18)
        badge.setStyleSheet("background:#E11D48;color:white;border-radius:9px;"
                            "font-size:11px;font-weight:700;padding:0 5px;")
        badge.setVisible(unread > 0)
        self.badge_widgets[cid] = badge
        wl.addWidget(badge)
        delete_btn = QPushButton('삭제')
        delete_btn.setFixedSize(34, 18)
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.setStyleSheet("QPushButton{border:none;background:transparent;color:#94A3B8;"
                                 "border-radius:4px;font-size:10px;font-weight:600;padding:0 4px;}"
                                 "QPushButton:hover{background:#FEE2E2;color:#BE123C;}")
        delete_btn.clicked.connect(lambda _checked=False, id_=cid: self.room_removed.emit(id_))
        wl.addWidget(delete_btn)
        w.mousePressEvent = lambda e, id_=cid: self._pick(id_)
        self.item_labels[cid] = label.lower()
        return w

    def _dm_item(self, d):
        w = QFrame()
        w.setObjectName('ch_item')
        w.setCursor(Qt.PointingHandCursor)
        wl = QHBoxLayout(w)
        wl.setContentsMargins(10, 6, 10, 6)
        wl.setSpacing(8)

        # 작은 아바타 + 프레즌스
        av_container = QWidget()
        av_container.setFixedSize(20, 20)
        av_lbl = QLabel(d['initials'], av_container)
        _, solid = AVATAR_COLORS.get(d['color'], AVATAR_COLORS['jw'])
        av_lbl.setFixedSize(18, 18)
        av_lbl.setAlignment(Qt.AlignCenter)
        av_lbl.setStyleSheet(f"background:{solid};color:white;border-radius:5px;"
                             f"font-size:9px;font-weight:700;")
        pres = QLabel('', av_container)
        pres.setFixedSize(8, 8)
        pres.move(10, 10)
        pres_color = PRESENCE_COLORS.get(d['presence'], '#CBD5E1')
        pres.setStyleSheet(f"background:{pres_color};border-radius:4px;"
                           f"border:1.5px solid #F8F9FB;")
        wl.addWidget(av_container)

        lbl = QLabel(d['name'])
        lbl.setObjectName('ch_label')
        lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        wl.addWidget(lbl)
        badge = QLabel(str(d.get('unread', 0)))
        badge.setObjectName('ch_badge')
        badge.setFixedHeight(18)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet("background:#E11D48;color:white;border-radius:9px;"
                            "font-size:11px;font-weight:700;padding:0 5px;")
        badge.setVisible(d.get('unread', 0) > 0)
        self.badge_widgets[d['id']] = badge
        wl.addWidget(badge)
        delete_btn = QPushButton('삭제')
        delete_btn.setFixedSize(34, 18)
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.setStyleSheet("QPushButton{border:none;background:transparent;color:#94A3B8;"
                                 "border-radius:4px;font-size:10px;font-weight:600;padding:0 4px;}"
                                 "QPushButton:hover{background:#FEE2E2;color:#BE123C;}")
        delete_btn.clicked.connect(lambda _checked=False, id_=d['id']: self.room_removed.emit(id_))
        wl.addWidget(delete_btn)
        w.mousePressEvent = lambda e, id_=d['id']: self._pick(id_)
        self.item_labels[d['id']] = d['name'].lower()
        return w

    def set_unread(self, cid, count):
        badge = self.badge_widgets.get(cid)
        if badge is None:
            return
        badge.setText(str(count))
        badge.setVisible(count > 0)

    def _filter_items(self, text):
        needle = str(text or "").strip().lower()
        for cid, widget in self.item_widgets.items():
            widget.setVisible(not needle or needle in self.item_labels.get(cid, ""))

    def _pick(self, cid):
        self.active_id = cid
        self._update_active()
        self.channel_selected.emit(cid)

    def _update_active(self):
        for cid, w in self.item_widgets.items():
            if cid == self.active_id:
                w.setStyleSheet("QFrame#ch_item{background:#3B68F1;border-radius:6px;}"
                                "QLabel#ch_label{color:white;font-weight:500;font-size:13px;}"
                                "QLabel#ch_badge{background:rgba(255,255,255,0.25);}")
            else:
                w.setStyleSheet("QFrame#ch_item{background:transparent;border-radius:6px;}"
                                "QFrame#ch_item:hover{background:#EEF0F3;}"
                                "QLabel#ch_label{color:#475569;font-size:13px;}"
                                "QLabel#ch_badge{background:#E11D48;}")
