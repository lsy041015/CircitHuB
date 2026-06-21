"""
CircuitKit — 팀 채팅 (PySide6 버전)
실행: python circuitkit_chat.py
요구사항: pip install PySide6
"""

import re
import sys
import time
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QScrollArea, QFrame, QSizePolicy,
    QTextEdit, QGraphicsDropShadowEffect, QInputDialog, QFileDialog,
    QMenu, QDialog, QMessageBox,
)
from PySide6.QtCore import Qt, QTimer, Signal, QSize, QPoint, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QFont, QTextCursor, QKeyEvent

from ._chat_persistence import ChatPersistenceStore
from .chat import ChatClient, ChatConnectionState, ChatMessage, ChatServer
from ._helpers import extract_unit_price, price_rows
from .models import ProductResult
from ._chat_side_panels import RightPanelContainer

from ._chat_data import (
    AVATAR_COLORS, CHANNELS, DMS, MESSAGES, SHARE_PARTS, PRESENCE_COLORS,
)
from ._chat_widgets import AvatarLabel, PartEmbed, MessageWidget, ChannelsColumn
from ._chat_composer import ComposerWidget, ComposerTextEdit


# ─────────────────────────────────────────────
#  메인 윈도우
# ─────────────────────────────────────────────
class CircuitKitChatWindow(QMainWindow):
    search_requested = Signal()
    message_received = Signal(object)
    status_received = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.active_id = 'bom-review'
        self._persistence = ChatPersistenceStore()
        room_state = self._load_room_state()
        self.channels = room_state.get("channels") or [dict(c) for c in CHANNELS]
        self.dms = room_state.get("dms") or [dict(d) for d in DMS]
        self.messages_by_channel = self._load_messages()
        if not self.messages_by_channel:
            self.messages_by_channel = {"bom-review": [dict(m) for m in MESSAGES]}
        valid_room_ids = [item["id"] for item in self.channels + self.dms]
        if self.active_id not in valid_room_ids:
            self.active_id = valid_room_ids[0] if valid_room_ids else "general"
        for item in self.channels + self.dms:
            item["unread"] = 0
        self.unread_by_channel = {item["id"]: 0 for item in self.channels + self.dms}
        self.muted_by_channel = {
            str(k): bool(v) for k, v in (room_state.get("muted") or {}).items()
        }
        self.messages = self.messages_by_channel.setdefault(self.active_id, [])
        self.server: ChatServer | None = None
        self.client: ChatClient | None = None
        self.connection_state = ChatConnectionState.DISCONNECTED
        self.setWindowTitle('CircuitKit — 팀 채팅')
        self.resize(1200, 800)
        self.setMinimumSize(900, 600)
        self.setStyleSheet(GLOBAL_QSS)
        self._window_control_buttons = []
        self.room_input = QLineEdit(self.active_id)
        self.room_input.hide()
        self.nickname_input = QLineEdit("engineer")
        self.nickname_input.setPlaceholderText("닉네임")
        self.host_input = QLineEdit("127.0.0.1")
        self.host_input.setPlaceholderText("호스트")
        self.port_input = QLineEdit("5100")
        self.port_input.setPlaceholderText("포트")
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("토큰(선택)")
        self.allowed_hosts_input = QLineEdit()
        self.allowed_hosts_input.setPlaceholderText("허용 IP(쉼표)")
        self.transcript = QTextEdit()
        self.transcript.hide()
        self._room_buttons = {}
        self.message_received.connect(self.append_message)
        self.status_received.connect(self.append_status)
        self._build_ui()
        self.message_input = self.composer.text_edit
        QTimer.singleShot(100, self._scroll_to_bottom)

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        vb = QVBoxLayout(root)
        vb.setContentsMargins(0, 0, 0, 0)
        vb.setSpacing(0)
        vb.addWidget(self._make_titlebar())

        body = QWidget()
        hb = QHBoxLayout(body)
        hb.setContentsMargins(0, 0, 0, 0)
        hb.setSpacing(0)
        hb.addWidget(self._make_ws_rail())
        self.channels_col = ChannelsColumn(self.channels, self.dms, self.active_id)
        self.channels_col.channel_selected.connect(self._on_channel_select)
        self.channels_col.room_removed.connect(self._remove_room)
        self.channels_col.room_add_requested.connect(self._prompt_add_room)
        self.channels_col.new_message_requested.connect(lambda: self._prompt_add_room("dm"))
        self._room_buttons = self.channels_col.item_widgets
        hb.addWidget(self.channels_col)
        hb.addWidget(self._make_conv(), 1)
        self.right_panel = RightPanelContainer()
        self.right_panel.thread.reply_submitted.connect(self._on_thread_reply)
        hb.addWidget(self.right_panel)
        vb.addWidget(body, 1)

    # ── 타이틀바
    def _make_titlebar(self):
        bar = QFrame(); bar.setObjectName('titlebar'); bar.setFixedHeight(36)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(12, 0, 12, 0); lay.setSpacing(10)
        lay.addWidget(QLabel('CK', styleSheet='color:#3B68F1;font-size:12px;font-weight:800;'))
        lay.addWidget(QLabel('CircuitKit — 팀 채팅', objectName='titlebar_title'))
        lay.addStretch()
        self.back_btn = QPushButton('부품 검색으로')
        self.back_btn.setObjectName('chat_btn'); self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.clicked.connect(self.search_requested.emit)
        lay.addWidget(self.back_btn)
        for sym, name, slot in [('−','win_min',self.showMinimized),
                                 ('□','win_max',self._toggle_max),
                                 ('✕','win_close',self.close)]:
            b = QPushButton(sym); b.setObjectName(name); b.setFixedSize(28,22)
            b.setCursor(Qt.PointingHandCursor); b.clicked.connect(slot); lay.addWidget(b)
            self._window_control_buttons.append(b)
        return bar

    def set_embedded_mode(self, embedded=True):
        for button in getattr(self, "_window_control_buttons", []):
            button.setVisible(not embedded)

    def _toggle_max(self):
        self.showNormal() if self.isMaximized() else self.showMaximized()

    # ── 워크스페이스 레일 (어두운 좌측)
    def _make_ws_rail(self):
        rail = QFrame(); rail.setObjectName('ws_rail'); rail.setFixedWidth(60)
        rail.setStyleSheet("QFrame#ws_rail{background:#F8F9FB;border-right:1px solid #E4E7EC;}")
        vb = QVBoxLayout(rail); vb.setContentsMargins(0, 12, 0, 12); vb.setSpacing(8)
        vb.setAlignment(Qt.AlignHCenter | Qt.AlignTop)

        logo = QLabel('CK')
        logo.setFixedSize(38, 38); logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet("background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
                           "stop:0 #3B68F1,stop:1 #1E3FAF);"
                           "color:white;font-weight:800;font-size:14px;border-radius:11px;")
        vb.addWidget(logo)
        vb.addSpacing(6)

        for sym, tip, active in [('💬','채팅',True),('🔍','검색',False),
                                   ('🔖','저장됨',False),('🔔','활동',False)]:
            b = QPushButton(sym); b.setFixedSize(40,40); b.setToolTip(tip)
            b.setCursor(Qt.PointingHandCursor)
            style = ("QPushButton{background:#EEF4FF;color:#1E3FAF;"
                     "border-radius:12px;border:none;font-size:14px;font-weight:700;}"
                     if active else
                     "QPushButton{background:transparent;color:#94A3B8;"
                     "border-radius:12px;border:none;font-size:14px;font-weight:700;}"
                     "QPushButton:hover{background:#EEF0F3;color:#475569;}")
            b.setStyleSheet(style)
            if tip == '채팅':
                b.clicked.connect(lambda: self.right_panel.hide())
            elif tip == '검색':
                b.clicked.connect(self.search_requested.emit)
            elif tip == '저장됨':
                b.clicked.connect(self._open_saved_panel)
            elif tip == '활동':
                b.clicked.connect(self._open_activity_panel)
            vb.addWidget(b, 0, Qt.AlignHCenter)

        vb.addStretch()

        settings_btn = QPushButton('⚙')
        settings_btn.setFixedSize(40,40)
        settings_btn.setToolTip('설정')
        settings_btn.setCursor(Qt.PointingHandCursor)
        settings_btn.setStyleSheet("QPushButton{background:transparent;color:#94A3B8;"
                                   "border-radius:12px;border:none;font-size:14px;font-weight:700;}"
                                   "QPushButton:hover{background:#EEF0F3;color:#475569;}")
        settings_btn.clicked.connect(self._toggle_connection_panel)
        vb.addWidget(settings_btn, 0, Qt.AlignHCenter)

        me = QLabel('ME')
        me.setFixedSize(34,34); me.setAlignment(Qt.AlignCenter)
        me.setStyleSheet("background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
                         "stop:0 #E11D48,stop:1 #F59E0B);"
                         "color:white;font-weight:700;font-size:12px;border-radius:10px;")
        vb.addWidget(me, 0, Qt.AlignHCenter)
        return rail

    # ── 대화 영역
    def _make_conv(self):
        frame = QFrame(); frame.setObjectName('conv')
        vb = QVBoxLayout(frame); vb.setContentsMargins(0,0,0,0); vb.setSpacing(0)

        # 대화 헤더
        self.conv_header = self._make_conv_header()
        vb.addWidget(self.conv_header)
        vb.addWidget(self._make_connection_panel())

        # 메시지 스크롤
        self.msg_scroll = QScrollArea()
        self.msg_scroll.setObjectName('msg_scroll_area')
        self.msg_scroll.setWidgetResizable(True)
        self.msg_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.msg_container = QWidget()
        self.msg_layout = QVBoxLayout(self.msg_container)
        self.msg_layout.setContentsMargins(0, 8, 0, 8)
        self.msg_layout.setSpacing(0)
        self.msg_layout.setAlignment(Qt.AlignTop)

        self._build_messages()
        self.msg_layout.addStretch()
        self.msg_scroll.setWidget(self.msg_container)
        vb.addWidget(self.msg_scroll, 1)

        # 작성창
        composer_wrap = QWidget()
        cw_lay = QVBoxLayout(composer_wrap)
        cw_lay.setContentsMargins(24, 0, 24, 22)
        cw_lay.setSpacing(0)
        self.composer = ComposerWidget('bom-review')
        self._sync_composer_mentions()
        self.composer.message_sent.connect(self._on_send)
        cw_lay.addWidget(self.composer)
        vb.addWidget(composer_wrap)
        return frame

    def _make_conv_header(self):
        hdr = QFrame(); hdr.setObjectName('conv_head'); hdr.setFixedHeight(52)
        lay = QHBoxLayout(hdr); lay.setContentsMargins(18,0,18,0); lay.setSpacing(12)

        active_ch = self._channel_meta(self.active_id)
        is_dm = self.active_id.startswith('dm-')
        name = active_ch['name'] if active_ch else self.active_id
        topic = active_ch.get('topic','') if active_ch else ''

        if not is_dm:
            lay.addWidget(QLabel('#', styleSheet="color:#94A3B8;font-weight:600;font-size:15px;"))
        self.ch_name_lbl = QLabel(name)
        self.ch_name_lbl.setStyleSheet("font-size:15px;font-weight:700;color:#0F172A;")
        lay.addWidget(self.ch_name_lbl)

        sep = QFrame(); sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color:#E4E7EC;"); sep.setFixedWidth(1)
        lay.addWidget(sep)

        self.topic_lbl = QLabel(topic or '주제 추가…')
        self.topic_lbl.setStyleSheet("font-size:12px;color:#94A3B8;")
        self.topic_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.topic_lbl.setCursor(Qt.PointingHandCursor)
        self.topic_lbl.mousePressEvent = lambda e: self._edit_topic()
        lay.addWidget(self.topic_lbl, 1)

        # 멤버 아바타들
        members_frame = QFrame()
        members_frame.setCursor(Qt.PointingHandCursor)
        members_frame.setStyleSheet("QFrame{background:white;border:1px solid #E4E7EC;"
                                    "border-radius:8px;}")
        ml = QHBoxLayout(members_frame); ml.setContentsMargins(4,4,8,4); ml.setSpacing(0)
        for init, color in [('JW','jw'),('SH','sh'),('MK','mk')]:
            av = AvatarLabel(init, color, size=20, radius=10, font_size=9)
            av.setStyleSheet(av.styleSheet() + "margin-left:-4px;border:1.5px solid white;")
            ml.addWidget(av)
        ml.addWidget(QLabel(f" {self._member_count()}", styleSheet="font-size:12px;font-weight:600;color:#475569;"))
        members_frame.mousePressEvent = lambda e: self._open_members_panel()
        lay.addWidget(members_frame)

        for sym, tip, width in [('알림','알림',42),('핀','핀',32),('설정','설정',42)]:
            b = QPushButton(sym); b.setFixedSize(width,28); b.setToolTip(tip)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet("QPushButton{border:none;background:transparent;border-radius:6px;"
                            "font-size:11px;font-weight:600;padding:0 6px;}"
                            "QPushButton:hover{background:#F4F5F7;}")
            if tip == '설정':
                b.clicked.connect(self._toggle_connection_panel)
            elif tip == '알림':
                self.notify_btn = b
                b.clicked.connect(self._toggle_mute)
            elif tip == '핀':
                b.clicked.connect(self._open_pinned_panel)
            lay.addWidget(b)
        self._sync_header_buttons()
        return hdr

    def _make_connection_panel(self):
        panel = QFrame()
        panel.setObjectName("conn_panel")
        panel.setStyleSheet(
            "QFrame#conn_panel{background:#FCFCFD;border-bottom:1px solid #EDF0F3;}"
            "QLineEdit{background:white;border:1px solid #D0D5DD;border-radius:7px;padding:0 10px;height:30px;font-size:12px;}"
            "QLineEdit:focus{border-color:#3B68F1;}"
        )
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(18, 8, 18, 8)
        layout.setSpacing(8)

        title = QLabel("연결 설정")
        title.setStyleSheet("font-size:12px;font-weight:700;color:#475569;")
        layout.addWidget(title)

        self.host_input.setFixedWidth(130)
        self.port_input.setFixedWidth(70)
        self.nickname_input.setFixedWidth(120)
        self.token_input.setFixedWidth(120)
        self.allowed_hosts_input.setFixedWidth(140)
        layout.addWidget(self.host_input)
        layout.addWidget(self.port_input)
        layout.addWidget(self.nickname_input)
        layout.addWidget(self.token_input)
        layout.addWidget(self.allowed_hosts_input)

        self.server_btn = QPushButton("서버 시작")
        self.server_btn.setFixedHeight(30)
        self.server_btn.clicked.connect(self.start_server)
        self.server_btn.setStyleSheet(
            "QPushButton{background:white;border:1px solid #D0D5DD;border-radius:7px;padding:0 10px;font-size:12px;font-weight:600;}"
            "QPushButton:hover{background:#F4F5F7;}"
        )
        layout.addWidget(self.server_btn)

        self.connect_btn = QPushButton("접속")
        self.connect_btn.setFixedHeight(30)
        self.connect_btn.clicked.connect(self.connect_client)
        self.connect_btn.setStyleSheet(
            "QPushButton{background:#3B68F1;border:1px solid #2952D6;border-radius:7px;color:white;padding:0 12px;font-size:12px;font-weight:700;}"
            "QPushButton:hover{background:#2952D6;}"
        )
        layout.addWidget(self.connect_btn)

        self.disconnect_btn = QPushButton("해제")
        self.disconnect_btn.setFixedHeight(30)
        self.disconnect_btn.clicked.connect(self.disconnect_chat)
        self.disconnect_btn.setStyleSheet(
            "QPushButton{background:white;border:1px solid #D0D5DD;border-radius:7px;padding:0 10px;font-size:12px;font-weight:600;}"
            "QPushButton:hover{background:#F4F5F7;}"
        )
        layout.addWidget(self.disconnect_btn)

        self.room_hint_lbl = QLabel()
        self.room_hint_lbl.setStyleSheet("font-size:11px;color:#94A3B8;")
        layout.addWidget(self.room_hint_lbl, 1)
        self.connection_panel = panel
        self._sync_connection_panel()
        return panel

    def _build_messages(self):
        # 채널 소개 배너
        intro = QWidget()
        il = QVBoxLayout(intro); il.setContentsMargins(24, 20, 24, 8); il.setSpacing(6)
        icon_box = QLabel('IC')
        icon_box.setFixedSize(52,52); icon_box.setAlignment(Qt.AlignCenter)
        icon_box.setStyleSheet("background:#EEF4FF;color:#2952D6;border-radius:14px;font-size:26px;")
        il.addWidget(icon_box)
        ch = self._channel_meta(self.active_id)
        display_name = ch["name"] if ch else self.active_id
        title = QLabel(f"#{display_name} 채널의 시작")
        title.setStyleSheet("font-size:19px;font-weight:800;color:#0F172A;")
        il.addWidget(title)
        desc = QLabel('BOM 검토 및 승인 요청 — 부품 검색 결과를 바로 공유하고 단가·재고를 함께 검토하세요.')
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size:13px;color:#94A3B8;")
        il.addWidget(desc)
        self.msg_layout.addWidget(intro)

        # 날짜 구분선 + 메시지들
        last_day = None
        for msg in self.messages_by_channel.setdefault(self.active_id, []):
            if msg.get('day') and msg['day'] != last_day:
                last_day = msg['day']
                self.msg_layout.addWidget(self._day_divider(msg['day']))
            w = MessageWidget(msg)
            w.react_clicked.connect(self._on_react)
            w.thread_clicked.connect(self._open_thread)
            w.pin_clicked.connect(self._toggle_pin)
            w.save_clicked.connect(self._toggle_saved)
            self.msg_layout.addWidget(w)

    def _day_divider(self, label):
        w = QWidget()
        lay = QHBoxLayout(w); lay.setContentsMargins(24, 14, 24, 6); lay.setSpacing(12)
        left = QFrame(); left.setFrameShape(QFrame.HLine)
        left.setStyleSheet("color:#EDF0F3;")
        lay.addWidget(left, 1)
        lbl = QLabel(label)
        lbl.setStyleSheet("font-size:11px;font-weight:600;color:#475569;"
                          "border:1px solid #E4E7EC;border-radius:999px;"
                          "padding:2px 12px;background:white;")
        lay.addWidget(lbl)
        right = QFrame(); right.setFrameShape(QFrame.HLine)
        right.setStyleSheet("color:#EDF0F3;")
        lay.addWidget(right, 1)
        return w

    def _scroll_to_bottom(self):
        sb = self.msg_scroll.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_channel_select(self, cid):
        self.active_id = cid
        self.room_input.setText(cid)
        ch = self._channel_meta(cid)
        if ch:
            self.ch_name_lbl.setText(ch['name'])
            self.topic_lbl.setText(ch.get('topic','') or '주제 추가…')
            self.composer.channel_name = ch['name']
            self._sync_composer_mentions()
            self.composer.text_edit.setPlaceholderText(f"#{ch['name']} 에 메시지 보내기")
        else:
            dm = self._dm_meta(cid)
            self.ch_name_lbl.setText(dm["name"] if dm else cid)
            self.topic_lbl.setText("다이렉트 메시지")
            self.composer.channel_name = cid
            self._sync_composer_mentions()
            self.composer.text_edit.setPlaceholderText(f"{self.ch_name_lbl.text()} 에 메시지 보내기")
        self._set_unread(cid, 0)
        self._sync_connection_panel()
        self._sync_header_buttons()
        if self.client is not None and getattr(self.client, "room", "") != self.active_id:
            self._switch_client_room_for_active_room()
        self._reload_messages()
        if (hasattr(self, 'right_panel') and self.right_panel.isVisible() and
                self.right_panel._stack.currentIndex() == RightPanelContainer.PAGE_THREAD):
            self.right_panel.hide()

    def _set_room(self, room: str) -> None:
        self.active_id = room or "bom-review"
        self.room_input.setText(self.active_id)
        if hasattr(self, "channels_col"):
            self.channels_col.active_id = self.active_id
            self.channels_col._update_active()
        self._on_channel_select(self.active_id)

    def _remove_room(self, room_id: str) -> None:
        if self._channel_meta(room_id):
            if len(self.channels) <= 1:
                self.append_status("마지막 채널은 삭제할 수 없습니다.")
                return
            self.channels = [c for c in self.channels if c["id"] != room_id]
            removed_label = "채널"
        elif self._dm_meta(room_id):
            self.dms = [d for d in self.dms if d["id"] != room_id]
            removed_label = "다이렉트 메시지"
        else:
            return

        self.messages_by_channel.pop(room_id, None)
        self.unread_by_channel.pop(room_id, None)
        fallback = self.channels[0]["id"] if self.channels else (self.dms[0]["id"] if self.dms else "general")
        if room_id == self.active_id:
            self.active_id = fallback
        self._rebuild_channel_column()
        self._set_room(self.active_id)
        self._save_room_state()
        self._save_messages()
        self.append_status(f"{removed_label}을 삭제했습니다: {room_id}")

    def _rebuild_channel_column(self) -> None:
        parent_layout = self.channels_col.parentWidget().layout() if self.channels_col.parentWidget() else None
        if parent_layout is None:
            return
        index = parent_layout.indexOf(self.channels_col)
        self.channels_col.deleteLater()
        self.channels_col = ChannelsColumn(self.channels, self.dms, self.active_id)
        self.channels_col.channel_selected.connect(self._on_channel_select)
        self.channels_col.room_removed.connect(self._remove_room)
        self.channels_col.room_add_requested.connect(self._prompt_add_room)
        self.channels_col.new_message_requested.connect(lambda: self._prompt_add_room("dm"))
        self._room_buttons = self.channels_col.item_widgets
        parent_layout.insertWidget(index, self.channels_col)
        for cid, count in self.unread_by_channel.items():
            self.channels_col.set_unread(cid, count)

    def _prompt_add_room(self, kind: str) -> None:
        if kind == "channel":
            name, ok = QInputDialog.getText(self, "채널 만들기", "채널 이름:")
            if ok:
                self._create_channel(name)
            return
        target, ok = QInputDialog.getText(self, "DM 시작", "상대 닉네임:")
        if ok:
            self._create_dm(target)

    def _create_channel(self, name: str) -> str | None:
        clean = str(name or "").strip()
        if not clean:
            return None
        room_id = self._slugify_channel_name(clean)
        existing = self._channel_meta(room_id)
        if existing is not None:
            self._set_room(room_id)
            self.append_status(f"기존 채널로 이동: {room_id}")
            return room_id
        item = {"id": room_id, "name": room_id, "topic": "", "unread": 0}
        self.channels.append(item)
        self.messages_by_channel.setdefault(room_id, [])
        self.unread_by_channel[room_id] = 0
        self._rebuild_channel_column()
        self._set_room(room_id)
        self._save_room_state()
        self._save_messages()
        self.append_status(f"채널 생성: {room_id}")
        return room_id

    def _create_dm(self, target_name: str) -> str | None:
        target = str(target_name or "").strip()
        me = (self.nickname_input.text().strip() or "anonymous").strip()
        if not target or target.lower() == me.lower():
            return None
        room_id = self._dm_room_id(me, target)
        existing = self._dm_meta(room_id)
        if existing is None:
            item = {
                "id": room_id,
                "name": target,
                "initials": self._initials(target),
                "color": self._color_key_for_name(target),
                "presence": "offline",
                "unread": 0,
            }
            self.dms.append(item)
            self.messages_by_channel.setdefault(room_id, [])
            self.unread_by_channel[room_id] = 0
            self._save_room_state()
            self._save_messages()
            self._rebuild_channel_column()
            self.append_status(f"DM 생성: {target}")
        self._set_room(room_id)
        return room_id

    def attach_share_text(self, text: str) -> None:
        clean = str(text or "").strip()
        if not clean:
            return
        self._set_room("bom-review")
        self.composer.text_edit.setPlainText(clean)
        self.composer.text_edit.setFocus()
        self.composer.text_edit.moveCursor(QTextCursor.End)
        self.composer._auto_grow()
        self.append_status(self._tr("chat_share_ready"))

    def attach_part_card(self, part) -> None:
        payload = self._part_payload(part)
        self._set_room("bom-review")
        self.composer._attach_part(payload)
        self.composer.text_edit.setFocus()
        self.append_status(self._tr("chat_share_ready"))

    def _tr(self, key: str, **kw) -> str:
        if self.main_window is not None and hasattr(self.main_window, "_tr"):
            return self.main_window._tr(key, **kw)
        fallback = {
            "chat_share_ready": "공유 내용을 준비했습니다.",
            "chat_status": "상태",
            "chat_me": "나",
        }.get(key, key)
        return fallback.format(**kw) if kw else fallback

    def append_status(self, message: str) -> None:
        lower = str(message).lower()
        if "chat connected" in lower or message == "연결됨":
            self._set_connection_state(ChatConnectionState.CONNECTED)
        elif "chat disconnected" in lower or "연결 실패" in message or "접속 실패" in message:
            self._set_connection_state(ChatConnectionState.ERROR)
        stamp = datetime.now().strftime("%H:%M")
        line = f"{stamp} {self._tr('chat_status')}: {message}"
        self.transcript.append(line)
        self._append_system_message(str(message), self.active_id)

    def append_message(self, message) -> None:
        stamp = datetime.fromtimestamp(message.timestamp).strftime("%H:%M")
        sender = getattr(message, "sender", "")
        room = getattr(message, "room", self.active_id)
        text = getattr(message, "text", "")
        mine = self.nickname_input.text().strip() or "anonymous"
        if sender == mine and self.client is not None:
            return
        label = self._tr("chat_me") if sender == mine else sender
        self.transcript.append(f"{stamp} [{room}] {label}: {text}")
        if getattr(message, "kind", "message") == "system":
            self._append_system_message(text, room)
            return
        msg = {
            "id": f"net-{int(time.time() * 1000)}",
            "author": label,
            "initials": self._initials(label),
            "color": "jw" if sender == mine else "mk",
            "ts": datetime.fromtimestamp(message.timestamp).strftime("%p %I:%M")
                .replace("AM", "오전").replace("PM", "오후").replace(" 0", " "),
            "text": text,
        }
        if isinstance(getattr(message, "payload", None), dict):
            parts = message.payload.get("parts")
            if isinstance(parts, list) and parts:
                msg["parts"] = [self._normalize_part(part) for part in parts if isinstance(part, dict)]
            files = message.payload.get("files")
            if isinstance(files, list) and files:
                msg["files"] = [self._normalize_file(item) for item in files if isinstance(item, dict)]
        self._append_message(room, msg)

    def start_server(self) -> None:
        try:
            if self.server is None:
                # Always bind on all interfaces so peers on the LAN can reach the
                # server. The host field is only the *client* connect target.
                self.server = ChatServer(
                    "0.0.0.0",
                    self._port(),
                    self.status_received.emit,
                    self.token_input.text(),
                    allowed_hosts=self._allowed_hosts(),
                    require_token=bool(self.token_input.text().strip()),
                )
                self.server.start()
            self.append_status(f"서버 준비: {self._port()}")
            # Host also joins its own server so it can chat, not just relay.
            if self.client is None:
                try:
                    self._connect_client_for_active_room(host="127.0.0.1")
                    self.append_status("호스트 자동 접속됨")
                except Exception as exc:
                    self.append_status(f"호스트 자동 접속 실패: {exc}")
            self._sync_connection_panel()
        except Exception as exc:
            self.append_status(f"서버 시작 실패: {exc}")

    def connect_client(self) -> None:
        if self.client is not None:
            return
        try:
            self._set_connection_state(ChatConnectionState.CONNECTING)
            self._connect_client_for_active_room()
            self.append_status("연결됨")
            self._sync_connection_panel()
        except Exception as exc:
            self.client = None
            self._set_connection_state(ChatConnectionState.ERROR)
            self.append_status(f"연결 실패: {exc}")

    def disconnect_chat(self) -> None:
        if self.client is not None:
            self.client.close()
            self.client = None
        self._set_connection_state(ChatConnectionState.DISCONNECTED)
        self.append_status("연결 해제됨")
        self._sync_connection_panel()

    def send_message(self) -> None:
        self.composer._send()

    def _on_send(self, text, attached):
        if isinstance(attached, dict):
            attached_parts = attached.get("parts") or []
            attached_files = attached.get("files") or []
        else:
            attached_parts = attached or []
            attached_files = []
        normalized_parts = [self._normalize_part(p) for p in attached_parts]
        normalized_files = [self._normalize_file(f) for f in attached_files]
        local_msg = self._local_message(text, normalized_parts, normalized_files)
        if self.client is not None:
            try:
                payload = None
                if normalized_parts or normalized_files:
                    payload = {
                        "type": "mixed",
                        "parts": normalized_parts,
                        "files": normalized_files,
                    }
                self.client.send(text, payload=payload)
                self._append_message(self.active_id, local_msg)
                self.transcript.append(f"{datetime.now().strftime('%H:%M')} [{self.active_id}] 나: {text}")
                return
            except Exception as exc:
                self.append_status(f"전송 실패: {exc}")
        if "@" in (text or ""):
            self._append_system_message("멘션 알림을 기록했습니다.", self.active_id)
        self._append_message(self.active_id, local_msg)
        self.transcript.append(f"{datetime.now().strftime('%H:%M')} [{self.active_id}] 나: {text}")

    def _local_message(self, text, parts, files):
        now = datetime.now().strftime('오후 %I:%M').replace(' 0', ' ')
        return {
            'id': f'local-{int(time.time() * 1000)}',
            'author': '나',
            'initials': 'ME',
            'color': 'jw',
            'ts': now,
            'text': text or None,
            'parts': parts if parts else None,
            'files': files if files else None,
        }

    def _append_system_message(self, text: str, channel_id: str | None = None) -> None:
        msg = {
            'id': f'status-{int(time.time() * 1000)}',
            'author': 'CircuitKit',
            'initials': 'CK',
            'color': 'bot',
            'ts': datetime.now().strftime('오후 %I:%M').replace(' 0', ' '),
            'text': text,
            'bot': True,
        }
        self._append_message(channel_id or self.active_id, msg)

    def _append_message(self, channel_id: str, msg: dict) -> None:
        self.messages_by_channel.setdefault(channel_id, []).append(msg)
        self._save_messages()
        if channel_id != self.active_id:
            if not self.muted_by_channel.get(channel_id, False):
                self._set_unread(channel_id, self.unread_by_channel.get(channel_id, 0) + 1)
            return
        if hasattr(self, "msg_layout") and self.msg_layout.count():
            self.msg_layout.takeAt(self.msg_layout.count() - 1)
            w = MessageWidget(msg)
            w.react_clicked.connect(self._on_react)
            w.thread_clicked.connect(self._open_thread)
            w.pin_clicked.connect(self._toggle_pin)
            w.save_clicked.connect(self._toggle_saved)
            self.msg_layout.addWidget(w)
            self.msg_layout.addStretch()
            QTimer.singleShot(50, self._scroll_to_bottom)

    def _reload_messages(self):
        while self.msg_layout.count():
            item = self.msg_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._build_messages()
        self.msg_layout.addStretch()
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _on_react(self, msg_id, reaction_index) -> None:
        for msg in self.messages_by_channel.get(self.active_id, []):
            if msg.get("id") != msg_id:
                continue
            reactions = msg.setdefault("reactions", [])
            if isinstance(reaction_index, str):
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

    def _toggle_pin(self, msg_id):
        msg = self._message_by_id(self.active_id, msg_id)
        if msg is None:
            return
        msg["pinned"] = not bool(msg.get("pinned"))
        self._save_messages()
        self._reload_messages()
        self.append_status("메시지를 고정했습니다." if msg["pinned"] else "메시지 고정을 해제했습니다.")
        if (self.right_panel.isVisible() and
                self.right_panel._stack.currentIndex() == RightPanelContainer.PAGE_PINNED):
            self.right_panel.pinned.load(self.messages_by_channel.get(self.active_id, []))

    def _toggle_saved(self, msg_id):
        msg = self._message_by_id(self.active_id, msg_id)
        if msg is None:
            return
        msg["saved"] = not bool(msg.get("saved"))
        self._save_messages()
        self._reload_messages()
        self.append_status("메시지를 저장했습니다." if msg["saved"] else "저장을 해제했습니다.")
        if (self.right_panel.isVisible() and
                self.right_panel._stack.currentIndex() == RightPanelContainer.PAGE_SAVED):
            self.right_panel.saved.load(self.messages_by_channel)

    def _message_by_id(self, channel_id, msg_id):
        return next(
            (item for item in self.messages_by_channel.get(channel_id, []) if item.get("id") == msg_id),
            None,
        )

    def _open_thread(self, msg_id: str) -> None:
        msg = self._message_by_id(self.active_id, msg_id)
        if msg is None:
            return
        self.right_panel.thread.load(msg)
        self.right_panel.show_page(RightPanelContainer.PAGE_THREAD)

    def _submit_thread_reply(self, dialog, msg_id, text):
        clean = str(text or "").strip()
        if not clean:
            return
        self.add_thread_reply(msg_id, clean)
        dialog.accept()

    def _edit_topic(self):
        if not self._channel_meta(self.active_id):
            return
        current = self.topic_lbl.text()
        if current == "주제 추가…":
            current = ""
        value, ok = QInputDialog.getText(self, "주제 편집", "채널 주제:", text=current)
        if not ok:
            return
        item = self._channel_meta(self.active_id)
        if item is None:
            return
        item["topic"] = str(value).strip()
        self.topic_lbl.setText(item["topic"] or "주제 추가…")
        self._save_room_state()
        self.append_status("채널 주제를 저장했습니다.")

    def _toggle_mute(self):
        self.muted_by_channel[self.active_id] = not self.muted_by_channel.get(self.active_id, False)
        self._save_room_state()
        self._sync_header_buttons()
        self.append_status("알림 꺼짐" if self.muted_by_channel[self.active_id] else "알림 켜짐")

    def _show_pinned_messages(self):
        messages = [
            msg for msg in self.messages_by_channel.get(self.active_id, [])
            if msg.get("pinned")
        ]
        text = "\n".join(self._message_summary(msg) for msg in messages)
        QMessageBox.information(self, "핀", text or "고정된 메시지가 없습니다.")

    def _show_saved_messages(self):
        rows = []
        for cid, messages in self.messages_by_channel.items():
            for msg in messages:
                if msg.get("saved"):
                    rows.append(f"[{cid}] {self._message_summary(msg)}")
        QMessageBox.information(self, "저장됨", "\n".join(rows) or "저장된 메시지가 없습니다.")

    def _show_activity_log(self):
        rows = []
        for msg in self.messages_by_channel.get(self.active_id, [])[-10:]:
            rows.append(f"{msg.get('ts', '')} {msg.get('author', '')}: {self._message_summary(msg)}")
        QMessageBox.information(self, "활동", "\n".join(rows) or "활동이 없습니다.")

    def _member_count(self):
        return max(1, len(self.dms) + 1)

    def _show_members(self):
        names = ["나"] + [str(d.get("name") or d.get("id")) for d in self.dms]
        QMessageBox.information(self, "멤버", "\n".join(names))

    def _on_thread_reply(self, msg_id: str, text: str) -> None:
        clean = str(text or '').strip()
        if not clean:
            return
        self.add_thread_reply(msg_id, clean)
        self._reload_messages()
        msg = self._message_by_id(self.active_id, msg_id)
        if msg is not None:
            self.right_panel.thread.load(msg)

    def _open_saved_panel(self) -> None:
        self.right_panel.saved.load(self.messages_by_channel)
        self.right_panel.toggle_page(RightPanelContainer.PAGE_SAVED)

    def _open_activity_panel(self) -> None:
        self.right_panel.activity.load(self.messages_by_channel)
        self.right_panel.toggle_page(RightPanelContainer.PAGE_ACTIVITY)

    def _open_pinned_panel(self) -> None:
        msgs = self.messages_by_channel.get(self.active_id, [])
        self.right_panel.pinned.load(msgs)
        self.right_panel.toggle_page(RightPanelContainer.PAGE_PINNED)

    def _open_members_panel(self) -> None:
        self.right_panel.members.load(self.dms)
        self.right_panel.toggle_page(RightPanelContainer.PAGE_MEMBERS)

    def _message_summary(self, msg):
        text = str(msg.get("text") or "").strip()
        if text:
            return text[:120]
        if msg.get("parts"):
            return f"부품 {len(msg.get('parts') or [])}개"
        if msg.get("files") or msg.get("file"):
            count = len(msg.get("files") or []) + (1 if msg.get("file") else 0)
            return f"파일 {count}개"
        return "(빈 메시지)"

    def _sync_header_buttons(self):
        btn = getattr(self, "notify_btn", None)
        if btn is None:
            return
        muted = self.muted_by_channel.get(self.active_id, False)
        btn.setText("알림끔" if muted else "알림")

    def _sync_composer_mentions(self):
        if not hasattr(self, "composer"):
            return
        self.composer.mention_names = [d.get("name", "") for d in self.dms if d.get("name")]

    def search_messages(self, text: str) -> list[dict]:
        needle = str(text or "").strip().lower()
        if not needle:
            return []
        hits = []
        for cid, messages in self.messages_by_channel.items():
            for msg in messages:
                if needle in str(msg.get("text", "")).lower():
                    hit = dict(msg)
                    hit["channel_id"] = cid
                    hits.append(hit)
        return hits

    def add_thread_reply(self, msg_id: str, text: str) -> None:
        for msg in self.messages_by_channel.get(self.active_id, []):
            if msg.get("id") == msg_id:
                thread = msg.setdefault("thread", {"count": 0, "avatars": [("ME", "jw")], "last": "방금"})
                thread["count"] = int(thread.get("count", 0)) + 1
                thread["last"] = "방금"
                msg.setdefault("replies", []).append({
                    "author": "나",
                    "text": text,
                    "ts": datetime.now().isoformat(),
                })
                self._save_messages()
                self._reload_messages()
                return

    def _set_unread(self, cid, count):
        self.unread_by_channel[cid] = max(0, int(count))
        if hasattr(self, "channels_col"):
            self.channels_col.set_unread(cid, self.unread_by_channel[cid])

    def _connect_client_for_active_room(self, host: str | None = None):
        self.client = ChatClient(
            host or self.host_input.text().strip() or "127.0.0.1",
            self._port(),
            self.nickname_input.text().strip() or "anonymous",
            self.active_id,
            self.message_received.emit,
            self.status_received.emit,
            self.token_input.text(),
        )
        self.client.connect()
        self._set_connection_state(ChatConnectionState.CONNECTED)

    def _reconnect_client_for_active_room(self):
        try:
            self._set_connection_state(ChatConnectionState.RECONNECTING)
            if self.client is not None:
                self.client.close()
                self.client = None
            self._connect_client_for_active_room()
            self.append_status(f"채널 전환: {self.active_id} room 재접속")
        except Exception as exc:
            self.client = None
            self._set_connection_state(ChatConnectionState.ERROR)
            self.append_status(f"채널 전환 접속 실패: {exc}")
        self._sync_connection_panel()

    def _switch_client_room_for_active_room(self):
        if self.client is None:
            return
        try:
            self.client.switch_room(self.active_id)
            self._set_connection_state(ChatConnectionState.CONNECTED)
            self.append_status(f"채널 전환: {self.active_id} room")
        except Exception as exc:
            self._set_connection_state(ChatConnectionState.ERROR)
            self.append_status(f"채널 전환 실패: {exc}")

    def _toggle_connection_panel(self):
        self.connection_panel.setVisible(not self.connection_panel.isVisible())

    def _sync_connection_panel(self):
        if hasattr(self, "room_hint_lbl"):
            mode = "채널" if self._channel_meta(self.active_id) else "DM"
            state = self._connection_state_label()
            self.room_hint_lbl.setText(f"현재 {mode} room: {self.active_id} · 상태: {state}")

    def _set_connection_state(self, state: ChatConnectionState) -> None:
        self.connection_state = state
        self._sync_connection_panel()

    def _connection_state_label(self) -> str:
        labels = {
            ChatConnectionState.DISCONNECTED: "미연결",
            ChatConnectionState.CONNECTING: "연결 중",
            ChatConnectionState.CONNECTED: "연결됨",
            ChatConnectionState.RECONNECTING: "재연결 중",
            ChatConnectionState.ERROR: "오류",
        }
        return labels.get(self.connection_state, "미연결")

    def _channel_meta(self, cid):
        return next((c for c in self.channels if c["id"] == cid), None)

    def _dm_meta(self, cid):
        return next((d for d in self.dms if d["id"] == cid), None)

    def _slugify_channel_name(self, name: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower())
        slug = slug.strip("-")
        return slug or "new-channel"

    def _dm_room_id(self, left: str, right: str) -> str:
        parts = sorted([(left or "anonymous").strip().lower(), (right or "anonymous").strip().lower()])
        return "dm:" + ":".join(parts)

    def _color_key_for_name(self, name: str) -> str:
        keys = ["jw", "sh", "mk", "yj", "hr"]
        return keys[sum(ord(ch) for ch in str(name)) % len(keys)]

    def _port(self) -> int:
        port = int(self.port_input.text().strip())
        if not 1 <= port <= 65535:
            raise ValueError(self._tr("port_error"))
        return port

    def _allowed_hosts(self) -> set[str] | None:
        hosts = {
            item.strip()
            for item in self.allowed_hosts_input.text().split(",")
            if item.strip()
        }
        return hosts or None

    def _initials(self, name: str) -> str:
        clean = str(name or "?").strip()
        return (clean[:2] if clean.isascii() else clean[:1]).upper() or "?"

    def _normalize_part(self, p):
        out = dict(p)
        datasheet_url = (
            out.get("datasheet_url")
            or out.get("datasheetUrl")
            or out.get("datasheet")
            or out.get("pdf_url")
            or ""
        )
        digikey_url = (
            out.get("digikey_url")
            or out.get("digikeyUrl")
            or out.get("detailUrl")
            or out.get("product_url")
            or out.get("url")
            or ""
        )
        name = str(out.get("name") or out.get("query") or "")
        if not digikey_url and name:
            digikey_url = f"https://www.digikey.com/en/products?keywords={quote_plus(name)}"
        return {
            "name": name,
            "maker": out.get("maker") or out.get("sub") or "DigiKey search result",
            "digikey": out.get("digikey") or out.get("digikey_part_number") or "—",
            "price": out.get("price") or "조회 결과",
            "priceUnit": out.get("priceUnit") or "1개 기준",
            "package": out.get("package") or "N/A",
            "mount": out.get("mount") or "N/A",
            "status": out.get("status") or "Active",
            "stock": out.get("stock") or "재고 확인 필요",
            "datasheet_url": datasheet_url,
            "digikey_url": digikey_url,
            "best": out.get("best", False),
            "cheapest": out.get("cheapest", False),
        }

    def _normalize_file(self, f):
        out = dict(f)
        size = int(out.get("size") or 0)
        meta = out.get("meta") or out.get("size_text") or self._format_size(size)
        return {
            "name": str(out.get("name") or "file"),
            "path": str(out.get("path") or ""),
            "size": size,
            "meta": str(meta),
        }

    def _format_size(self, size):
        if size >= 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        if size >= 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size} B"

    def _part_payload(self, part):
        if isinstance(part, ProductResult):
            rows = price_rows(part.price_rows)
            first_price = rows[0][1] if rows and len(rows[0]) > 1 else "조회 결과"
            unit = extract_unit_price(first_price)
            price = f"${unit:.4f}" if unit > 0 else first_price
            return {
                "name": part.part_number or part.query or part.title,
                "maker": part.specs.get("제조사", part.specs.get("Manufacturer", "")),
                "digikey": part.part_number or "—",
                "price": price,
                "priceUnit": "1개 기준",
                "package": part.specs.get("패키지 / 케이스", part.specs.get("Package / Case", "N/A")),
                "mount": part.specs.get("실장유형", part.specs.get("Mounting Type", "N/A")),
                "status": part.specs.get("제품 상태", part.specs.get("Part Status", "Active")),
                "stock": part.specs.get("재고", part.specs.get("Quantity Available", "재고 확인 필요")),
                "datasheet_url": part.datasheet_url,
                "digikey_url": part.product_url,
            }
        return self._normalize_part(part)

    def _load_messages(self):
        return self._persistence.load_messages()

    def _save_messages(self):
        self._persistence.save_messages(self.messages_by_channel)

    def _load_room_state(self):
        return self._persistence.load_room_state()

    def _save_room_state(self):
        self._persistence.save_room_state(self.channels, self.dms, self.muted_by_channel)

    def closeEvent(self, event):
        self.disconnect_chat()
        if self.server is not None:
            self.server.stop()
            self.server = None
        self._save_room_state()
        self._save_messages()
        event.accept()


# ─────────────────────────────────────────────
#  전역 QSS
# ─────────────────────────────────────────────
GLOBAL_QSS = """
QMainWindow, QWidget {
    font-family:'Malgun Gothic','Apple SD Gothic Neo','Nanum Gothic',sans-serif;
    background:#FFFFFF;
}
/* 타이틀바 */
QFrame#titlebar {
    background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #FBFBFC,stop:1 #F4F5F7);
    border-bottom:1px solid #E4E7EC;
}
QLabel#titlebar_title { font-size:12px;font-weight:500;color:#475569; }
QPushButton#chat_btn {
    font-size:12px;color:#475569;border:1px solid #E4E7EC;
    border-radius:6px;background:transparent;padding:3px 9px;
}
QPushButton#chat_btn:hover { background:#F4F5F7; }
QPushButton#win_min, QPushButton#win_max {
    border:none;background:transparent;color:#94A3B8;border-radius:4px;font-size:13px;
}
QPushButton#win_min:hover, QPushButton#win_max:hover { background:#EEF0F3;color:#0F172A; }
QPushButton#win_close { border:none;background:transparent;color:#94A3B8;border-radius:4px;font-size:13px; }
QPushButton#win_close:hover { background:#FEE2E2;color:#BE123C; }
/* 대화 헤더 */
QFrame#conv_head { background:white;border-bottom:1px solid #EDF0F3; }
/* 메시지 스크롤 */
QScrollArea#msg_scroll_area { border:none;background:white; }
/* 작성창 */
QFrame#composer {
    border:1px solid #D0D5DD;border-radius:12px;background:white;
}
QFrame#composer_toolbar { border-bottom:1px solid #EDF0F3; }
QTextEdit#composer_textarea {
    border:none;background:transparent;font-size:14px;color:#0F172A;
    padding:11px 14px;
}
/* 스크롤바 */
QScrollBar:vertical { width:10px;background:transparent;border:none; }
QScrollBar::handle:vertical {
    background:#D6DAE0;border-radius:5px;min-height:20px;margin:2px 2px;
}
QScrollBar::handle:vertical:hover { background:#B8BFC8; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0;border:none; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background:transparent; }
/* 툴팁 */
QToolTip {
    background:#FFFFFF;
    color:#0F172A;
    border:1px solid #E4E7EC;
    border-radius:6px;
    font-size:12px;
    padding:4px 8px;
}
"""


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    win = CircuitKitChatWindow()
    win.show()
    sys.exit(app.exec())
