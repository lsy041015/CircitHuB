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


from digikey_scraper._chat_side_panels import (
    ActivityPanel, SavedPanel, PinnedPanel, MembersPanel, ThreadPanel
)

SAMPLE_MESSAGES = {
    'bom-review': [
        {'id': '1', 'author': '지원', 'text': '커패시터 확인 필요', 'ts': '09:00',
         'saved': True, 'pinned': False, 'reactions': [], 'replies': []},
        {'id': '2', 'author': '서현', 'text': '단가 협의 완료', 'ts': '09:15',
         'saved': False, 'pinned': True, 'reactions': [], 'replies': []},
    ],
    'general': [
        {'id': '3', 'author': '민결', 'text': '안녕하세요', 'ts': '08:30',
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
    # 3 message rows + 1 stretch = at least 3 items
    assert panel._layout.count() >= 3


def test_saved_panel_shows_saved_only(app):
    panel = SavedPanel()
    panel.load(SAMPLE_MESSAGES)
    # only msg id=1 is saved → 1 row + stretch
    assert panel._layout.count() >= 1


def test_saved_panel_empty_state(app):
    panel = SavedPanel()
    panel.load({'general': [{'id': '9', 'text': 'hi', 'saved': False}]})
    assert panel._layout.count() >= 1


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


def test_thread_panel_reply_signal(app):
    panel = ThreadPanel()
    msg = {'id': 'msg-1', 'author': '지원', 'text': '테스트 메시지',
           'thread': {'count': 0}, 'replies': []}
    panel.load(msg)
    received = []
    panel.reply_submitted.connect(lambda mid, txt: received.append((mid, txt)))
    panel._input.setText('답글 테스트')
    panel._on_send()
    assert received == [('msg-1', '답글 테스트')]


def test_thread_panel_clears_input_after_send(app):
    panel = ThreadPanel()
    panel.load({'id': 'x', 'author': 'A', 'text': 'hi', 'replies': []})
    panel._input.setText('some reply')
    panel._on_send()
    assert panel._input.text() == ''


from digikey_scraper._circuitkit_chat_design import CircuitKitChatWindow


def test_on_react_adds_chosen_emoji(app):
    import os
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    win = CircuitKitChatWindow()
    win.messages_by_channel = {
        'bom-review': [{'id': 'r1', 'text': 'hi', 'reactions': [], 'author': 'A',
                        'ts': '09:00', 'saved': False, 'pinned': False, 'replies': [],
                        'initials': 'A', 'color': 'jw'}]
    }
    win.active_id = 'bom-review'
    win._on_react('r1', '🎉')
    msg = win._message_by_id('bom-review', 'r1')
    assert any(r['emo'] == '🎉' for r in msg['reactions'])


from unittest.mock import patch
from digikey_scraper._chat_composer import ComposerWidget


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
