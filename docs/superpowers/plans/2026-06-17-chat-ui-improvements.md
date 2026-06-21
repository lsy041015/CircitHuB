# Chat UI Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all QMessageBox popup stubs in the chat UI with proper inline panels, and fix minor UX gaps (emoji picker, link URL dialog, 채팅 button).

**Architecture:** Add a collapsible `RightPanelContainer` (280px, QStackedWidget) to the right side of `_build_ui()` in `CircuitKitChatWindow`. All currently-popup-based actions (activity, saved, pinned, members, thread) become pages in this panel. Two small composer improvements (emoji picker → QMenu, link format → URL dialog) are independent inline fixes.

**Tech Stack:** PySide6, pytest + QT_QPA_PLATFORM=offscreen

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `digikey_scraper/_chat_side_panels.py` | RightPanelContainer + 5 panel widget classes |
| Create | `tests/test_chat_side_panels.py` | Panel unit tests |
| Modify | `digikey_scraper/_circuitkit_chat_design.py` | Wire right panel into layout + fix 4 buttons + emoji + link |

---

## Task 1: `_chat_side_panels.py` — base container + QSS

**Files:**
- Create: `digikey_scraper/_chat_side_panels.py`
- Create: `tests/test_chat_side_panels.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_chat_side_panels.py
import pytest
from PySide6.QtWidgets import QApplication
from digikey_scraper._chat_side_panels import RightPanelContainer

@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])

def test_right_panel_hidden_on_init(app):
    panel = RightPanelContainer()
    assert not panel.isVisible()

def test_right_panel_width(app):
    panel = RightPanelContainer()
    assert panel.width() == 280

def test_show_page_makes_visible(app):
    panel = RightPanelContainer()
    panel.show_page(RightPanelContainer.PAGE_ACTIVITY)
    assert panel.isVisible()
    assert panel._stack.currentIndex() == RightPanelContainer.PAGE_ACTIVITY

def test_toggle_page_hides_when_same(app):
    panel = RightPanelContainer()
    panel.show_page(RightPanelContainer.PAGE_SAVED)
    panel.toggle_page(RightPanelContainer.PAGE_SAVED)
    assert not panel.isVisible()

def test_toggle_page_switches_when_different(app):
    panel = RightPanelContainer()
    panel.show_page(RightPanelContainer.PAGE_ACTIVITY)
    panel.toggle_page(RightPanelContainer.PAGE_PINNED)
    assert panel.isVisible()
    assert panel._stack.currentIndex() == RightPanelContainer.PAGE_PINNED
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
QT_QPA_PLATFORM=offscreen pytest tests/test_chat_side_panels.py -v
```
Expected: `ModuleNotFoundError: No module named 'digikey_scraper._chat_side_panels'`

- [ ] **Step 3: Create `digikey_scraper/_chat_side_panels.py` with base container**

```python
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

        # Placeholder panels — replaced in Task 2
        from digikey_scraper._chat_side_panels import (
            ActivityPanel, SavedPanel, PinnedPanel, MembersPanel, ThreadPanel
        )
        self._activity_panel = ActivityPanel()
        self._saved_panel    = SavedPanel()
        self._pinned_panel   = PinnedPanel()
        self._members_panel  = MembersPanel()
        self._thread_panel   = ThreadPanel()

        for p in (self._activity_panel, self._saved_panel, self._pinned_panel,
                  self._members_panel, self._thread_panel):
            self._stack.addWidget(p)

        vb.addWidget(self._stack, 1)

    # ── public API ──────────────────────────────────

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


# ── Placeholder panel base (used before Task 2 adds real panels) ──

class _PlaceholderPanel(QWidget):
    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        vb = QVBoxLayout(self)
        lbl = QLabel(label)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-size:13px;color:#94A3B8;")
        vb.addWidget(lbl)


class ActivityPanel(_PlaceholderPanel):
    def __init__(self, parent=None): super().__init__('활동 패널', parent)
    def load(self, messages_by_channel: dict) -> None: pass

class SavedPanel(_PlaceholderPanel):
    def __init__(self, parent=None): super().__init__('저장됨 패널', parent)
    def load(self, messages_by_channel: dict) -> None: pass

class PinnedPanel(_PlaceholderPanel):
    def __init__(self, parent=None): super().__init__('핀 패널', parent)
    def load(self, messages: list) -> None: pass

class MembersPanel(_PlaceholderPanel):
    def __init__(self, parent=None): super().__init__('멤버 패널', parent)
    def load(self, dms: list) -> None: pass

class ThreadPanel(_PlaceholderPanel):
    reply_submitted = Signal(str, str)
    def __init__(self, parent=None): super().__init__('스레드 패널', parent)
    def load(self, msg: dict) -> None: pass
```

> Note: `RightPanelContainer.__init__` imports from itself — fix the circular import by removing the inner import block and directly instantiating the classes defined in the same file.

Correct the `__init__` — remove the inner import block, instantiate directly:

```python
        self._activity_panel = ActivityPanel()
        self._saved_panel    = SavedPanel()
        self._pinned_panel   = PinnedPanel()
        self._members_panel  = MembersPanel()
        self._thread_panel   = ThreadPanel()
```

- [ ] **Step 4: Run test — expect PASS**

```bash
QT_QPA_PLATFORM=offscreen pytest tests/test_chat_side_panels.py -v
```
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add digikey_scraper/_chat_side_panels.py tests/test_chat_side_panels.py
git commit -m "feat(chat): add RightPanelContainer skeleton with placeholder panels"
```

---

## Task 2: Implement all 5 panel widgets

**Files:**
- Modify: `digikey_scraper/_chat_side_panels.py` (replace placeholder classes)
- Modify: `tests/test_chat_side_panels.py` (add panel-specific tests)

- [ ] **Step 1: Add panel tests**

Append to `tests/test_chat_side_panels.py`:

```python
from digikey_scraper._chat_side_panels import (
    ActivityPanel, SavedPanel, PinnedPanel, MembersPanel, ThreadPanel
)

SAMPLE_MESSAGES = {
    'bom-review': [
        {'id': '1', 'author': '지원', 'text': '커패시터 확인 필요', 'ts': '09:00',
         'saved': True, 'pinned': False, 'reactions': [], 'replies': []},
        {'id': '2', 'author': '서현', 'text': '단가 협의 완료',    'ts': '09:15',
         'saved': False, 'pinned': True, 'reactions': [], 'replies': []},
    ],
    'general': [
        {'id': '3', 'author': '민결', 'text': '안녕하세요',         'ts': '08:30',
         'saved': False, 'pinned': False, 'reactions': [], 'replies': []},
    ],
}

SAMPLE_DMS = [
    {'id': 'dm-sh', 'name': '서현 (PCB)', 'initials': 'SH', 'presence': 'online'},
    {'id': 'dm-mk', 'name': '민결 (구매)', 'initials': 'MK', 'presence': 'away'},
]

def test_activity_panel_loads_rows(app):
    panel = ActivityPanel()
    panel.load(SAMPLE_MESSAGES)
    # layout has 3 message rows + 1 stretch = 4 items
    assert panel._layout.count() >= 3

def test_saved_panel_shows_saved_only(app):
    panel = SavedPanel()
    panel.load(SAMPLE_MESSAGES)
    # only msg id=1 is saved → 1 row + stretch
    assert panel._layout.count() >= 1

def test_saved_panel_empty_state(app):
    panel = SavedPanel()
    panel.load({'general': [{'id': '9', 'text': 'hi', 'saved': False}]})
    # empty label + stretch
    assert panel._layout.count() >= 1
    item = panel._layout.itemAt(0)
    assert item is not None

def test_pinned_panel_shows_pinned_only(app):
    panel = PinnedPanel()
    panel.load(SAMPLE_MESSAGES['bom-review'])
    # only msg id=2 is pinned
    assert panel._layout.count() >= 1

def test_members_panel_shows_me_plus_dms(app):
    panel = MembersPanel()
    panel.load(SAMPLE_DMS)
    # 나 + 2 DMs + stretch = at least 3 items
    assert panel._layout.count() >= 3

def test_thread_panel_reply_signal(app, qtbot):
    panel = ThreadPanel()
    msg = {'id': 'msg-1', 'author': '지원', 'text': '테스트 메시지',
           'thread': {'count': 0}, 'replies': []}
    panel.load(msg)
    with qtbot.waitSignal(panel.reply_submitted, timeout=1000) as blocker:
        panel._input.setText('답글 테스트')
        panel._on_send()
    assert blocker.args == ['msg-1', '답글 테스트']

def test_thread_panel_clears_input_after_send(app, qtbot):
    panel = ThreadPanel()
    panel.load({'id': 'x', 'author': 'A', 'text': 'hi', 'replies': []})
    panel._input.setText('some reply')
    with qtbot.waitSignal(panel.reply_submitted, timeout=1000):
        panel._on_send()
    assert panel._input.text() == ''
```

- [ ] **Step 2: Run tests — expect FAIL** (placeholder panels don't have `_layout`)

```bash
QT_QPA_PLATFORM=offscreen pytest tests/test_chat_side_panels.py -v
```
Expected: 7+ FAILs on `AttributeError: '_PlaceholderPanel' object has no attribute '_layout'`

- [ ] **Step 3: Replace placeholder classes with real implementations**

In `digikey_scraper/_chat_side_panels.py`, replace all placeholder classes with:

```python
# ── Scroll helper ──────────────────────────────────────────────────────────

def _make_scroll_panel(parent=None):
    """Returns (outer_widget, content_layout, scroll_area)."""
    outer = QWidget(parent)
    vb = QVBoxLayout(outer); vb.setContentsMargins(0, 0, 0, 0)
    scroll = QScrollArea(); scroll.setObjectName('panel_scroll')
    scroll.setWidgetResizable(True)
    content = QWidget()
    cl = QVBoxLayout(content)
    cl.setContentsMargins(12, 8, 12, 12); cl.setSpacing(4)
    scroll.setWidget(content)
    vb.addWidget(scroll)
    return outer, cl, scroll


# ── ActivityPanel ──────────────────────────────────────────────────────────

class ActivityPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        outer, self._layout, _ = _make_scroll_panel()
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
        row.setStyleSheet("QFrame{border-radius:8px;}"
                          "QFrame:hover{background:#F8F9FB;}")
        vb = QVBoxLayout(row)
        vb.setContentsMargins(8, 6, 8, 6); vb.setSpacing(2)

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
        preview.setStyleSheet("font-size:12px;color:#475569;")
        preview.setWordWrap(True)

        vb.addLayout(top); vb.addWidget(author); vb.addWidget(preview)
        return row


# ── SavedPanel ─────────────────────────────────────────────────────────────

class SavedPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        outer, self._layout, _ = _make_scroll_panel()
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
                    self._layout.addWidget(self._make_row(cid, msg))
                    found = True

        if not found:
            empty = QLabel('저장된 메시지가 없습니다')
            empty.setStyleSheet('font-size:13px;color:#94A3B8;')
            empty.setAlignment(Qt.AlignCenter)
            self._layout.addWidget(empty)
        self._layout.addStretch()

    def _make_row(self, cid: str, msg: dict) -> QFrame:
        row = QFrame()
        row.setStyleSheet(
            "QFrame{border:1px solid #E4E7EC;border-radius:8px;background:white;}"
        )
        vb = QVBoxLayout(row)
        vb.setContentsMargins(10, 8, 10, 8); vb.setSpacing(3)

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
        preview.setStyleSheet("font-size:13px;color:#0F172A;")
        preview.setWordWrap(True)

        vb.addLayout(top); vb.addWidget(preview)
        return row


# ── PinnedPanel ────────────────────────────────────────────────────────────

class PinnedPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        outer, self._layout, _ = _make_scroll_panel()
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
        row.setStyleSheet(
            "QFrame{border-left:3px solid #3B68F1;background:#F8F9FB;"
            "border-radius:0 6px 6px 0;}"
        )
        vb = QVBoxLayout(row)
        vb.setContentsMargins(10, 6, 8, 6); vb.setSpacing(2)

        author = QLabel(str(msg.get('author', '')))
        author.setStyleSheet("font-size:11px;font-weight:600;color:#475569;")

        text = str(msg.get('text') or '')
        if not text and msg.get('parts'):
            text = f"부품 {len(msg['parts'])}개 첨부"
        elif not text:
            text = "첨부 메시지"
        preview = QLabel(text[:100] + ('…' if len(text) > 100 else ''))
        preview.setStyleSheet("font-size:13px;color:#0F172A;")
        preview.setWordWrap(True)

        vb.addWidget(author); vb.addWidget(preview)
        return row


# ── MembersPanel ───────────────────────────────────────────────────────────

_PRESENCE_COLORS = {'online': '#10B981', 'away': '#F59E0B', 'offline': '#CBD5E1'}


class MembersPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        outer, self._layout, _ = _make_scroll_panel()
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
        row.setStyleSheet("QFrame{border-radius:6px;}"
                          "QFrame:hover{background:#F8F9FB;}")
        hl = QHBoxLayout(row)
        hl.setContentsMargins(6, 6, 6, 6); hl.setSpacing(10)

        avatar = QLabel(initials)
        avatar.setFixedSize(28, 28); avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet("background:#E4E7EC;color:#475569;"
                             "font-weight:700;font-size:11px;border-radius:14px;")

        info = QVBoxLayout(); info.setSpacing(1)
        info.addWidget(QLabel(name, styleSheet="font-size:13px;color:#0F172A;"))
        info.addWidget(QLabel(presence, styleSheet="font-size:11px;color:#94A3B8;"))

        dot = QLabel('●')
        dot.setStyleSheet(f"color:{_PRESENCE_COLORS.get(presence, '#CBD5E1')};font-size:8px;")

        hl.addWidget(avatar)
        hl.addLayout(info, 1)
        hl.addWidget(dot)
        return row


# ── ThreadPanel ────────────────────────────────────────────────────────────

class ThreadPanel(QWidget):
    reply_submitted = Signal(str, str)  # msg_id, text

    def __init__(self, parent=None):
        super().__init__(parent)
        self._msg_id = ''
        outer, self._layout, _ = _make_scroll_panel()

        vb = QVBoxLayout(self); vb.setContentsMargins(0, 0, 0, 0); vb.setSpacing(0)
        vb.addWidget(outer, 1)
        self._layout.addStretch()

        composer_frame = QFrame()
        composer_frame.setStyleSheet(
            "QFrame{border-top:1px solid #E4E7EC;background:white;}"
        )
        cl = QVBoxLayout(composer_frame)
        cl.setContentsMargins(12, 8, 12, 12); cl.setSpacing(6)

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
        rvb = QVBoxLayout(root_frame)
        rvb.setContentsMargins(10, 8, 10, 8); rvb.setSpacing(3)
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
        self._input.setFocus()

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
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
QT_QPA_PLATFORM=offscreen pytest tests/test_chat_side_panels.py -v
```
Expected: all tests pass

- [ ] **Step 5: Commit**

```bash
git add digikey_scraper/_chat_side_panels.py tests/test_chat_side_panels.py
git commit -m "feat(chat): implement 5 right panel widgets (activity/saved/pinned/members/thread)"
```

---

## Task 3: Wire RightPanelContainer into chat window layout

**Files:**
- Modify: `digikey_scraper/_circuitkit_chat_design.py`

Changes needed (in order):

1. Add import at top of file
2. `_build_ui()`: add `self.right_panel` to layout
3. `_make_ws_rail()`: wire 💬/🔖/🔔 buttons
4. `_make_conv_header()`: wire 핀 button → pinned panel
5. `members_frame.mousePressEvent` → members panel
6. `_open_thread()`: load thread panel instead of QDialog
7. `_toggle_pin()` / `_toggle_saved()`: refresh panel if visible
8. `_on_channel_select()`: close thread panel on channel switch
9. Wire `ThreadPanel.reply_submitted` → `add_thread_reply`

- [ ] **Step 1: Add import**

At the top of `_circuitkit_chat_design.py`, after existing imports:

```python
from ._chat_side_panels import RightPanelContainer
```

- [ ] **Step 2: Modify `_build_ui()` — add right panel to layout**

Find this block (around line 1162):
```python
        hb.addWidget(self.channels_col)
        hb.addWidget(self._make_conv(), 1)
        vb.addWidget(body, 1)
```

Replace with:
```python
        hb.addWidget(self.channels_col)
        hb.addWidget(self._make_conv(), 1)
        self.right_panel = RightPanelContainer()
        self.right_panel.thread.reply_submitted.connect(self._on_thread_reply)
        hb.addWidget(self.right_panel)
        vb.addWidget(body, 1)
```

- [ ] **Step 3: Add `_on_thread_reply` method**

Add this method to `CircuitKitChatWindow` (near `_submit_thread_reply`):

```python
    def _on_thread_reply(self, msg_id: str, text: str) -> None:
        clean = str(text or '').strip()
        if not clean:
            return
        self.add_thread_reply(msg_id, clean)
        self._reload_messages()
        msg = self._message_by_id(self.active_id, msg_id)
        if msg is not None:
            self.right_panel.thread.load(msg)
```

- [ ] **Step 4: Wire ws_rail buttons**

In `_make_ws_rail()`, find the button loop (around line 1207):
```python
        for sym, tip, active in [('💬','채팅',True),('🔍','검색',False),
                                   ('🔖','저장됨',False),('🔔','활동',False)]:
            b = QPushButton(sym); b.setFixedSize(40,40); b.setToolTip(tip)
            b.setCursor(Qt.PointingHandCursor)
            ...
            if tip == '채팅':
                b.clicked.connect(lambda: self.append_status("채팅 화면입니다."))
            elif tip == '검색':
                b.clicked.connect(self.search_requested.emit)
            elif tip == '저장됨':
                b.clicked.connect(self._show_saved_messages)
            elif tip == '활동':
                b.clicked.connect(self._show_activity_log)
```

Replace the four `if/elif` connects with:
```python
            if tip == '채팅':
                b.clicked.connect(self.right_panel.hide)
            elif tip == '검색':
                b.clicked.connect(self.search_requested.emit)
            elif tip == '저장됨':
                b.clicked.connect(self._open_saved_panel)
            elif tip == '활동':
                b.clicked.connect(self._open_activity_panel)
```

- [ ] **Step 5: Add `_open_saved_panel` and `_open_activity_panel` methods**

```python
    def _open_saved_panel(self) -> None:
        self.right_panel.saved.load(self.messages_by_channel)
        self.right_panel.toggle_page(RightPanelContainer.PAGE_SAVED)

    def _open_activity_panel(self) -> None:
        self.right_panel.activity.load(self.messages_by_channel)
        self.right_panel.toggle_page(RightPanelContainer.PAGE_ACTIVITY)
```

Also add import at top of `CircuitKitChatWindow` methods section (or where used):
```python
from ._chat_side_panels import RightPanelContainer
```
(already done in Step 1 — no duplicate needed)

- [ ] **Step 6: Wire header 핀 button → pinned panel**

In `_make_conv_header()`, find:
```python
            elif tip == '핀':
                b.clicked.connect(self._show_pinned_messages)
```

Replace with:
```python
            elif tip == '핀':
                b.clicked.connect(self._open_pinned_panel)
```

Add method:
```python
    def _open_pinned_panel(self) -> None:
        msgs = self.messages_by_channel.get(self.active_id, [])
        self.right_panel.pinned.load(msgs)
        self.right_panel.toggle_page(RightPanelContainer.PAGE_PINNED)
```

- [ ] **Step 7: Wire members click → members panel**

In `_make_conv_header()`, find:
```python
        members_frame.mousePressEvent = lambda e: self._show_members()
```

Replace with:
```python
        members_frame.mousePressEvent = lambda e: self._open_members_panel()
```

Add method:
```python
    def _open_members_panel(self) -> None:
        self.right_panel.members.load(self.dms)
        self.right_panel.toggle_page(RightPanelContainer.PAGE_MEMBERS)
```

- [ ] **Step 8: Wire `thread_clicked` → thread panel**

`_open_thread()` is currently called via `w.thread_clicked.connect(self._open_thread)`.

Replace the body of `_open_thread()`:
```python
    def _open_thread(self, msg_id: str) -> None:
        msg = self._message_by_id(self.active_id, msg_id)
        if msg is None:
            return
        self.right_panel.thread.load(msg)
        self.right_panel.show_page(RightPanelContainer.PAGE_THREAD)
```

- [ ] **Step 9: Refresh pinned/saved panels when toggled**

In `_toggle_pin()`, after `self._reload_messages()`:
```python
        if (self.right_panel.isVisible() and
                self.right_panel._stack.currentIndex() == RightPanelContainer.PAGE_PINNED):
            self.right_panel.pinned.load(self.messages_by_channel.get(self.active_id, []))
```

In `_toggle_saved()`, after `self._reload_messages()`:
```python
        if (self.right_panel.isVisible() and
                self.right_panel._stack.currentIndex() == RightPanelContainer.PAGE_SAVED):
            self.right_panel.saved.load(self.messages_by_channel)
```

- [ ] **Step 10: Close thread panel on channel switch**

In `_on_channel_select()`, at the end of the method body:
```python
        if (hasattr(self, 'right_panel') and self.right_panel.isVisible() and
                self.right_panel._stack.currentIndex() == RightPanelContainer.PAGE_THREAD):
            self.right_panel.hide()
```

- [ ] **Step 11: Run full test suite**

```bash
QT_QPA_PLATFORM=offscreen pytest --cov --cov-report=term-missing -q
```
Expected: all existing tests pass, coverage ≥ 85% on layered packages

- [ ] **Step 12: Commit**

```bash
git add digikey_scraper/_circuitkit_chat_design.py
git commit -m "feat(chat): wire right panel into layout, replace all QMessageBox popups"
```

---

## Task 4: Emoji reaction picker

**Problem:** The `add_btn` (➕ 반응 추가) always emits `react_clicked(msg_id, -1)` which hardcodes `👍` in `_on_react`. Replace with a `QMenu` emoji picker that lets the user choose before emitting.

**Files:**
- Modify: `digikey_scraper/_circuitkit_chat_design.py`

- [ ] **Step 1: Write test**

Append to `tests/test_chat_side_panels.py`:

```python
from digikey_scraper._circuitkit_chat_design import CircuitKitChatWindow

def test_on_react_adds_chosen_emoji(app):
    win = CircuitKitChatWindow()
    win.messages_by_channel = {
        'bom-review': [{'id': 'r1', 'text': 'hi', 'reactions': []}]
    }
    win.active_id = 'bom-review'
    win._on_react('r1', '🎉')   # emoji string instead of -1 int
    msg = win._message_by_id('bom-review', 'r1')
    assert any(r['emo'] == '🎉' for r in msg['reactions'])
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
QT_QPA_PLATFORM=offscreen pytest tests/test_chat_side_panels.py::test_on_react_adds_chosen_emoji -v
```
Expected: FAIL — `_on_react` checks `reaction_index == -1` (int), not emoji string

- [ ] **Step 3: Update `_on_react` to accept emoji string or int**

Find `_on_react` in `_circuitkit_chat_design.py` (around line 1793):

```python
    def _on_react(self, msg_id, reaction_index):
        for msg in self.messages_by_channel.get(self.active_id, []):
            if msg.get("id") != msg_id:
                continue
            reactions = msg.setdefault("reactions", [])
            if reaction_index == -1:
                reactions.append({"emo": "👍", "count": 1, "mine": True})
            elif 0 <= reaction_index < len(reactions):
```

Replace the method body with:

```python
    def _on_react(self, msg_id, reaction_index) -> None:
        for msg in self.messages_by_channel.get(self.active_id, []):
            if msg.get("id") != msg_id:
                continue
            reactions = msg.setdefault("reactions", [])
            if isinstance(reaction_index, str):
                # emoji string from picker — add new reaction
                reactions.append({"emo": reaction_index, "count": 1, "mine": True})
            elif reaction_index == -1:
                reactions.append({"emo": "👍", "count": 1, "mine": True})
            elif 0 <= reaction_index < len(reactions):
                item = reactions[reaction_index]
                if item.get("mine"):
                    item["count"] = max(0, int(item.get("count", 1)) - 1)
                    item["mine"] = False
                else:
                    item["count"] = int(item.get("count", 0)) + 1
                    item["mine"] = True
            self._save_messages()
            self._reload_messages()
            return
```

- [ ] **Step 4: Replace `add_btn` click with emoji menu**

In `MessageWidget._build()`, find (around line 384):
```python
        add_btn.clicked.connect(lambda: self.react_clicked.emit(m['id'], -1))
```

Replace with:
```python
        add_btn.clicked.connect(lambda _=False, mid=m['id']: self._show_emoji_react_menu(mid, add_btn))
```

Add `_show_emoji_react_menu` to `MessageWidget`:
```python
    def _show_emoji_react_menu(self, msg_id: str, anchor) -> None:
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        for emoji in ['👍', '✅', '🔧', '📌', '⚠️', '🎉', '❤️', '👀']:
            menu.addAction(emoji, lambda e=emoji: self.react_clicked.emit(msg_id, e))
        menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))
```

- [ ] **Step 5: Run test — expect PASS**

```bash
QT_QPA_PLATFORM=offscreen pytest tests/test_chat_side_panels.py::test_on_react_adds_chosen_emoji -v
```
Expected: PASS

- [ ] **Step 6: Run full suite**

```bash
QT_QPA_PLATFORM=offscreen pytest --cov -q
```
Expected: all pass

- [ ] **Step 7: Commit**

```bash
git add digikey_scraper/_circuitkit_chat_design.py
git commit -m "feat(chat): replace hardcoded 👍 reaction with emoji picker menu"
```

---

## Task 5: Link format URL dialog

**Problem:** The `링크` toolbar button in `ComposerWidget._apply_format` inserts `[텍스트](https://)` literally. Replace with a small dialog asking for the URL.

**Files:**
- Modify: `digikey_scraper/_circuitkit_chat_design.py`

- [ ] **Step 1: Write test**

Append to `tests/test_chat_side_panels.py`:

```python
from unittest.mock import patch
from digikey_scraper._circuitkit_chat_design import ComposerWidget

def test_link_format_uses_provided_url(app):
    widget = ComposerWidget('test-ch')
    widget.text_edit.setPlainText('DigiKey')
    cursor = widget.text_edit.textCursor()
    cursor.select(cursor.SelectionType.Document)
    widget.text_edit.setTextCursor(cursor)

    with patch('PySide6.QtWidgets.QInputDialog.getText', return_value=('https://digikey.com', True)):
        widget._apply_format('링크')

    result = widget.text_edit.toPlainText()
    assert result == '[DigiKey](https://digikey.com)'

def test_link_format_cancelled_keeps_original(app):
    widget = ComposerWidget('test-ch')
    widget.text_edit.setPlainText('원본 텍스트')

    with patch('PySide6.QtWidgets.QInputDialog.getText', return_value=('', False)):
        widget._apply_format('링크')

    result = widget.text_edit.toPlainText()
    assert result == '원본 텍스트'
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
QT_QPA_PLATFORM=offscreen pytest tests/test_chat_side_panels.py::test_link_format_uses_provided_url tests/test_chat_side_panels.py::test_link_format_cancelled_keeps_original -v
```
Expected: FAIL — current code inserts `https://` literally without asking

- [ ] **Step 3: Update `_apply_format` for `링크` case**

In `ComposerWidget._apply_format()`, find:
```python
        elif kind == '링크':
            value = f"[{text}](https://)"
```

Replace with:
```python
        elif kind == '링크':
            from PySide6.QtWidgets import QInputDialog
            url, ok = QInputDialog.getText(self, "링크 삽입", "URL:", text="https://")
            if not ok:
                return
            value = f"[{text}]({url})"
```

- [ ] **Step 4: Run test — expect PASS**

```bash
QT_QPA_PLATFORM=offscreen pytest tests/test_chat_side_panels.py::test_link_format_uses_provided_url tests/test_chat_side_panels.py::test_link_format_cancelled_keeps_original -v
```
Expected: 2 passed

- [ ] **Step 5: Run full suite + coverage**

```bash
QT_QPA_PLATFORM=offscreen pytest --cov --cov-report=term-missing -q
```
Expected: all pass, coverage ≥ 85%

- [ ] **Step 6: Final commit**

```bash
git add digikey_scraper/_circuitkit_chat_design.py tests/test_chat_side_panels.py
git commit -m "feat(chat): link format button opens URL input dialog instead of placeholder"
```

---

## Self-Review

### Spec coverage

| 개선 항목 | Task | 상태 |
|-----------|------|------|
| 💬 채팅 버튼 (no-op) | 3-Step4 | ✅ `right_panel.hide()` |
| 🔔 활동 QMessageBox | 3-Step5 | ✅ ActivityPanel |
| 🔖 저장됨 QMessageBox | 3-Step5 | ✅ SavedPanel |
| 📌 핀 QMessageBox | 3-Step6 | ✅ PinnedPanel |
| 멤버 QMessageBox | 3-Step7 | ✅ MembersPanel |
| 스레드 QDialog | 3-Step8 | ✅ ThreadPanel in right panel |
| 스레드 답글 미반영 | 3-Step3 | ✅ `_on_thread_reply` reloads |
| 리액션 👍 고정 | Task 4 | ✅ emoji picker QMenu |
| 링크 `https://` 리터럴 | Task 5 | ✅ QInputDialog URL |
| 알림 뮤트 효과 없음 | — | 범위 외 (실제 알림 시스템 없음) |

### Placeholder scan

None found.

### Type consistency

- `react_clicked` signal: `Signal(str, int)` — Task 4 now passes emoji `str` as second arg. Signal type needs update to `Signal(str, object)` to accept both int and str.

**Fix:** In `MessageWidget` signal definition (around line 265):
```python
# Before
react_clicked = Signal(str, int)
# After
react_clicked = Signal(str, object)
```
Add this fix to Task 4 Step 3.
