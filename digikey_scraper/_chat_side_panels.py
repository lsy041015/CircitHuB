from __future__ import annotations
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QStackedWidget, QVBoxLayout,
    QScrollArea, QWidget, QLineEdit,
)
from PySide6.QtCore import Qt, Signal

PANEL_QSS = """
QFrame#right_panel { background:#FFFFFF; border-left:1px solid #E4E7EC; }
QFrame#panel_hdr {
    background:#F8F9FB; border-bottom:1px solid #E4E7EC;
    min-height:44px; max-height:44px;
}
QLabel#panel_title { font-size:13px; font-weight:700; color:#0F172A; }
QPushButton#panel_close {
    border:none; background:transparent; color:#94A3B8;
    font-size:14px; border-radius:4px;
}
QPushButton#panel_close:hover { background:#EEF0F3; color:#0F172A; }
QScrollArea#panel_scroll { border:none; background:transparent; }
"""

_PAGE_TITLES = {0: '활동', 1: '저장됨', 2: '핀 고정', 3: '멤버', 4: '스레드'}


class RightPanelContainer(QFrame):
    PAGE_ACTIVITY = 0
    PAGE_SAVED    = 1
    PAGE_PINNED   = 2
    PAGE_MEMBERS  = 3
    PAGE_THREAD   = 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('right_panel')
        self.setFixedWidth(280)
        self.hide()
        self.setStyleSheet(PANEL_QSS)

        vb = QVBoxLayout(self)
        vb.setContentsMargins(0, 0, 0, 0)
        vb.setSpacing(0)

        hdr = QFrame(); hdr.setObjectName('panel_hdr')
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(14, 0, 8, 0); hl.setSpacing(0)
        self._title = QLabel(); self._title.setObjectName('panel_title')
        close = QPushButton('✕'); close.setObjectName('panel_close')
        close.setFixedSize(28, 28); close.setCursor(Qt.PointingHandCursor)
        close.clicked.connect(self.hide)
        hl.addWidget(self._title, 1); hl.addWidget(close)
        vb.addWidget(hdr)

        self._stack = QStackedWidget()

        self._activity_panel = ActivityPanel()
        self._saved_panel    = SavedPanel()
        self._pinned_panel   = PinnedPanel()
        self._members_panel  = MembersPanel()
        self._thread_panel   = ThreadPanel()

        for p in (self._activity_panel, self._saved_panel, self._pinned_panel,
                  self._members_panel, self._thread_panel):
            self._stack.addWidget(p)

        vb.addWidget(self._stack, 1)

    def show_page(self, page: int) -> None:
        self._title.setText(_PAGE_TITLES[page])
        self._stack.setCurrentIndex(page)
        self.show()

    def toggle_page(self, page: int) -> None:
        if self.isVisible() and self._stack.currentIndex() == page:
            self.hide()
        else:
            self.show_page(page)

    @property
    def activity(self) -> 'ActivityPanel':  return self._activity_panel
    @property
    def saved(self)    -> 'SavedPanel':     return self._saved_panel
    @property
    def pinned(self)   -> 'PinnedPanel':    return self._pinned_panel
    @property
    def members(self)  -> 'MembersPanel':   return self._members_panel
    @property
    def thread(self)   -> 'ThreadPanel':    return self._thread_panel


def _make_scroll_panel(parent=None):
    """Returns (outer_widget, content_layout)."""
    outer = QWidget(parent)
    vb = QVBoxLayout(outer); vb.setContentsMargins(0, 0, 0, 0)
    scroll = QScrollArea(); scroll.setObjectName('panel_scroll')
    scroll.setWidgetResizable(True)
    content = QWidget()
    cl = QVBoxLayout(content)
    cl.setContentsMargins(12, 8, 12, 12); cl.setSpacing(4)
    scroll.setWidget(content)
    vb.addWidget(scroll)
    return outer, cl


class ActivityPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        outer, self._layout = _make_scroll_panel()
        vb = QVBoxLayout(self); vb.setContentsMargins(0, 0, 0, 0)
        vb.addWidget(outer)
        self._layout.addStretch()

    def load(self, messages_by_channel: dict) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        rows: list[tuple[str, dict]] = []
        for cid, msgs in messages_by_channel.items():
            for msg in msgs:
                rows.append((cid, msg))
        for cid, msg in rows[-20:]:
            self._layout.addWidget(self._make_row(cid, msg))
        self._layout.addStretch()

    def _make_row(self, cid: str, msg: dict) -> QFrame:
        row = QFrame()
        row.setStyleSheet("QFrame{border-radius:8px;}QFrame:hover{background:#F8F9FB;}")
        vb = QVBoxLayout(row); vb.setContentsMargins(8, 6, 8, 6); vb.setSpacing(2)
        top = QHBoxLayout(); top.setSpacing(6)
        badge = QLabel(f'#{cid}')
        badge.setStyleSheet("font-size:10px;font-weight:600;color:#3B68F1;"
                            "background:#EEF4FF;border-radius:4px;padding:1px 5px;")
        ts = QLabel(str(msg.get('ts', '')))
        ts.setStyleSheet("font-size:10px;color:#94A3B8;")
        top.addWidget(badge); top.addStretch(); top.addWidget(ts)
        author = QLabel(str(msg.get('author', '')))
        author.setStyleSheet("font-size:12px;font-weight:600;color:#0F172A;")
        text = str(msg.get('text') or '')
        if not text and msg.get('parts'):
            text = f"부품 {len(msg['parts'])}개"
        elif not text:
            text = "첨부 메시지"
        preview = QLabel(text[:60] + ('…' if len(text) > 60 else ''))
        preview.setStyleSheet("font-size:12px;color:#475569;"); preview.setWordWrap(True)
        vb.addLayout(top); vb.addWidget(author); vb.addWidget(preview)
        return row


class SavedPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        outer, self._layout = _make_scroll_panel()
        vb = QVBoxLayout(self); vb.setContentsMargins(0, 0, 0, 0)
        vb.addWidget(outer)
        self._layout.addStretch()

    def load(self, messages_by_channel: dict) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        found = False
        for cid, msgs in messages_by_channel.items():
            for msg in msgs:
                if msg.get('saved'):
                    self._layout.addWidget(self._make_row(cid, msg)); found = True
        if not found:
            empty = QLabel('저장된 메시지가 없습니다')
            empty.setStyleSheet('font-size:13px;color:#94A3B8;')
            empty.setAlignment(Qt.AlignCenter)
            self._layout.addWidget(empty)
        self._layout.addStretch()

    def _make_row(self, cid: str, msg: dict) -> QFrame:
        row = QFrame()
        row.setStyleSheet("QFrame{border:1px solid #E4E7EC;border-radius:8px;background:white;}")
        vb = QVBoxLayout(row); vb.setContentsMargins(10, 8, 10, 8); vb.setSpacing(3)
        top = QHBoxLayout()
        badge = QLabel(f'#{cid}')
        badge.setStyleSheet("font-size:10px;font-weight:600;color:#3B68F1;"
                            "background:#EEF4FF;border-radius:4px;padding:1px 5px;")
        top.addWidget(badge); top.addStretch()
        text = str(msg.get('text') or '')
        if not text and msg.get('parts'):
            text = f"부품 {len(msg['parts'])}개"
        elif not text:
            text = "첨부 메시지"
        preview = QLabel(text[:80] + ('…' if len(text) > 80 else ''))
        preview.setStyleSheet("font-size:13px;color:#0F172A;"); preview.setWordWrap(True)
        vb.addLayout(top); vb.addWidget(preview)
        return row


class PinnedPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        outer, self._layout = _make_scroll_panel()
        vb = QVBoxLayout(self); vb.setContentsMargins(0, 0, 0, 0)
        vb.addWidget(outer)
        self._layout.addStretch()

    def load(self, messages: list) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        pinned = [m for m in messages if m.get('pinned')]
        if not pinned:
            empty = QLabel('고정된 메시지가 없습니다')
            empty.setStyleSheet('font-size:13px;color:#94A3B8;')
            empty.setAlignment(Qt.AlignCenter)
            self._layout.addWidget(empty)
        else:
            for msg in pinned:
                self._layout.addWidget(self._make_row(msg))
        self._layout.addStretch()

    def _make_row(self, msg: dict) -> QFrame:
        row = QFrame()
        row.setStyleSheet("QFrame{border-left:3px solid #3B68F1;background:#F8F9FB;"
                          "border-radius:0 6px 6px 0;}")
        vb = QVBoxLayout(row); vb.setContentsMargins(10, 6, 8, 6); vb.setSpacing(2)
        author = QLabel(str(msg.get('author', '')))
        author.setStyleSheet("font-size:11px;font-weight:600;color:#475569;")
        text = str(msg.get('text') or '')
        if not text and msg.get('parts'):
            text = f"부품 {len(msg['parts'])}개 첨부"
        elif not text:
            text = "첨부 메시지"
        preview = QLabel(text[:100] + ('…' if len(text) > 100 else ''))
        preview.setStyleSheet("font-size:13px;color:#0F172A;"); preview.setWordWrap(True)
        vb.addWidget(author); vb.addWidget(preview)
        return row


_PRESENCE_COLORS = {'online': '#10B981', 'away': '#F59E0B', 'offline': '#CBD5E1'}


class MembersPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        outer, self._layout = _make_scroll_panel()
        vb = QVBoxLayout(self); vb.setContentsMargins(0, 0, 0, 0)
        vb.addWidget(outer)
        self._layout.addStretch()

    def load(self, dms: list) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self._layout.addWidget(self._make_row('나', 'ME', 'online'))
        for d in dms:
            self._layout.addWidget(
                self._make_row(
                    str(d.get('name', d.get('id', ''))),
                    str(d.get('initials', '??')),
                    str(d.get('presence', 'offline')),
                )
            )
        self._layout.addStretch()

    def _make_row(self, name: str, initials: str, presence: str) -> QFrame:
        row = QFrame()
        row.setStyleSheet("QFrame{border-radius:6px;}QFrame:hover{background:#F8F9FB;}")
        hl = QHBoxLayout(row); hl.setContentsMargins(6, 6, 6, 6); hl.setSpacing(10)
        avatar = QLabel(initials)
        avatar.setFixedSize(28, 28); avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet("background:#E4E7EC;color:#475569;"
                             "font-weight:700;font-size:11px;border-radius:14px;")
        info = QVBoxLayout(); info.setSpacing(1)
        info.addWidget(QLabel(name, styleSheet="font-size:13px;color:#0F172A;"))
        info.addWidget(QLabel(presence, styleSheet="font-size:11px;color:#94A3B8;"))
        dot = QLabel('●')
        dot.setStyleSheet(f"color:{_PRESENCE_COLORS.get(presence, '#CBD5E1')};font-size:8px;")
        hl.addWidget(avatar); hl.addLayout(info, 1); hl.addWidget(dot)
        return row


class ThreadPanel(QWidget):
    reply_submitted = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._msg_id = ''
        outer, self._layout = _make_scroll_panel()
        vb = QVBoxLayout(self); vb.setContentsMargins(0, 0, 0, 0); vb.setSpacing(0)
        vb.addWidget(outer, 1)
        self._layout.addStretch()

        composer_frame = QFrame()
        composer_frame.setStyleSheet("QFrame{border-top:1px solid #E4E7EC;background:white;}")
        cl = QVBoxLayout(composer_frame); cl.setContentsMargins(12, 8, 12, 12); cl.setSpacing(6)
        self._input = QLineEdit()
        self._input.setPlaceholderText("답글 입력…")
        self._input.setStyleSheet(
            "QLineEdit{border:1px solid #D0D5DD;border-radius:8px;"
            "padding:8px 12px;font-size:13px;color:#0F172A;}"
            "QLineEdit:focus{border-color:#3B68F1;}"
        )
        send = QPushButton("답글 보내기")
        send.setCursor(Qt.PointingHandCursor)
        send.setStyleSheet(
            "QPushButton{background:#3B68F1;color:white;border:none;"
            "border-radius:8px;font-size:12px;font-weight:600;padding:7px 14px;}"
            "QPushButton:hover{background:#2952D6;}"
        )
        send.clicked.connect(self._on_send)
        self._input.returnPressed.connect(self._on_send)
        cl.addWidget(self._input); cl.addWidget(send, 0, Qt.AlignRight)
        vb.addWidget(composer_frame)

    def load(self, msg: dict) -> None:
        self._msg_id = str(msg.get('id', ''))
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        root_frame = QFrame()
        root_frame.setStyleSheet(
            "QFrame{background:#F8F9FB;border-radius:8px;border:1px solid #E4E7EC;}"
        )
        rvb = QVBoxLayout(root_frame); rvb.setContentsMargins(10, 8, 10, 8); rvb.setSpacing(3)
        rvb.addWidget(QLabel(str(msg.get('author', '')),
                             styleSheet="font-size:12px;font-weight:700;color:#0F172A;"))
        body_lbl = QLabel(str(msg.get('text') or '(첨부 메시지)'))
        body_lbl.setWordWrap(True)
        body_lbl.setStyleSheet("font-size:13px;color:#0F172A;")
        rvb.addWidget(body_lbl)
        self._layout.addWidget(root_frame)
        count = (msg.get('thread') or {}).get('count', 0)
        div = QLabel(f"답글 {count}개")
        div.setStyleSheet("font-size:11px;font-weight:600;color:#94A3B8;"
                          "border-bottom:1px solid #E4E7EC;padding-bottom:4px;")
        self._layout.addWidget(div)
        for reply in (msg.get('replies') or []):
            self._layout.addWidget(self._make_reply(reply))
        self._layout.addStretch()
        self._input.clear()

    def _make_reply(self, reply: dict) -> QWidget:
        w = QWidget()
        hl = QHBoxLayout(w); hl.setContentsMargins(0, 2, 0, 2); hl.setSpacing(8)
        av = QLabel(str(reply.get('author', '?'))[:2].upper())
        av.setFixedSize(24, 24); av.setAlignment(Qt.AlignCenter)
        av.setStyleSheet("background:#E4E7EC;color:#475569;font-weight:700;"
                         "font-size:10px;border-radius:12px;")
        info = QVBoxLayout(); info.setSpacing(1)
        info.addWidget(QLabel(str(reply.get('author', '')),
                              styleSheet="font-size:12px;font-weight:600;color:#0F172A;"))
        info.addWidget(QLabel(str(reply.get('text', '')),
                              styleSheet="font-size:12px;color:#475569;"))
        hl.addWidget(av); hl.addLayout(info, 1)
        return w

    def _on_send(self) -> None:
        text = self._input.text().strip()
        if not text or not self._msg_id:
            return
        self.reply_submitted.emit(self._msg_id, text)
        self._input.clear()
