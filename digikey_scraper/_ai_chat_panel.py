from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from .application.ai_chat_service import AiChatService
    from .domain.chat_models import AiChatSession

CONTEXT_MODES = [
    ("일반 대화", "general"),
    ("현재 부품 결과", "parts"),
    ("데이터시트 RAG", "rag"),
]


class _BubbleWidget(QWidget):
    def __init__(self, role: str, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)

        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        prefix = QLabel("AI" if role == "assistant" else "나")
        prefix.setFixedWidth(24)
        prefix.setAlignment(Qt.AlignmentFlag.AlignTop)

        if role == "assistant":
            layout.addWidget(prefix)
            layout.addWidget(label)
        else:
            layout.addWidget(label)
            layout.addWidget(prefix)

        self._label = label

    def append_text(self, chunk: str) -> None:
        self._label.setText(self._label.text() + chunk)


class AiChatPanel(QWidget):
    def __init__(
        self,
        service: "AiChatService",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._session: AiChatSession | None = None
        self._worker = None
        self._streaming_bubble: _BubbleWidget | None = None
        self._parts_context: list[dict] | None = None

        self._build_ui()
        self._load_sessions()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)

        top = QHBoxLayout()
        self._session_combo = QComboBox()
        self._session_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._session_combo.currentIndexChanged.connect(self._on_session_changed)
        btn_new = QPushButton("새 대화")
        btn_new.clicked.connect(self._new_session)
        top.addWidget(self._session_combo)
        top.addWidget(btn_new)
        root.addLayout(top)

        ctx_row = QHBoxLayout()
        ctx_row.addWidget(QLabel("컨텍스트:"))
        self._ctx_combo = QComboBox()
        for label, _ in CONTEXT_MODES:
            self._ctx_combo.addItem(label)
        ctx_row.addWidget(self._ctx_combo)
        root.addLayout(ctx_row)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._chat_container = QWidget()
        self._chat_layout = QVBoxLayout(self._chat_container)
        self._chat_layout.addStretch()
        self._scroll.setWidget(self._chat_container)
        root.addWidget(self._scroll)

        input_row = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setPlaceholderText("메시지 입력...")
        self._input.returnPressed.connect(self._send)
        self._btn_send = QPushButton("전송")
        self._btn_send.clicked.connect(self._send)
        input_row.addWidget(self._input)
        input_row.addWidget(self._btn_send)
        root.addLayout(input_row)

    def _load_sessions(self) -> None:
        sessions = self._service.load_sessions()
        self._session_combo.blockSignals(True)
        self._session_combo.clear()
        self._session_combo.addItem("-- 세션 선택 --", None)
        for s in sessions:
            self._session_combo.addItem(s.title, s.id)
        self._session_combo.blockSignals(False)

    def _new_session(self) -> None:
        mode = CONTEXT_MODES[self._ctx_combo.currentIndex()][1]
        self._session = self._service.new_session(context_mode=mode)
        self._clear_chat()

    def _on_session_changed(self, index: int) -> None:
        session_id = self._session_combo.itemData(index)
        if not session_id:
            return
        sessions = self._service.load_sessions()
        matched = next((s for s in sessions if s.id == session_id), None)
        if matched:
            self._session = matched
            self._redraw_chat()

    def _clear_chat(self) -> None:
        while self._chat_layout.count() > 1:
            item = self._chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _redraw_chat(self) -> None:
        self._clear_chat()
        if self._session:
            for msg in self._session.messages:
                bubble = _BubbleWidget(msg.role, msg.content)
                self._chat_layout.insertWidget(self._chat_layout.count() - 1, bubble)

    def _send(self) -> None:
        text = self._input.text().strip()
        if not self._session:
            self._new_session()
        if not text:
            return

        self._input.clear()
        self._btn_send.setEnabled(False)

        user_bubble = _BubbleWidget("user", text)
        self._chat_layout.insertWidget(self._chat_layout.count() - 1, user_bubble)

        ai_bubble = _BubbleWidget("assistant", "")
        self._chat_layout.insertWidget(self._chat_layout.count() - 1, ai_bubble)
        self._streaming_bubble = ai_bubble

        from .workers import AiChatWorker

        self._worker = AiChatWorker(
            self._service,
            self._session,
            text,
            parts_context=self._parts_context,
        )
        self._worker.signals.chunk.connect(self._on_chunk)
        self._worker.signals.finished.connect(self._on_finished)
        self._worker.signals.failed.connect(self._on_failed)
        self._worker.start()

    def _on_chunk(self, chunk: str) -> None:
        if self._streaming_bubble:
            self._streaming_bubble.append_text(chunk)
        self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        )

    def _on_finished(self, _response: str) -> None:
        self._streaming_bubble = None
        self._btn_send.setEnabled(True)
        self._load_sessions()

    def _on_failed(self, error: str) -> None:
        if self._streaming_bubble:
            self._streaming_bubble.append_text(f"\n[오류: {error}]")
        self._streaming_bubble = None
        self._btn_send.setEnabled(True)

    def set_parts_context(self, parts: list[dict] | None) -> None:
        self._parts_context = parts

    def _new_session_with_mode(self, mode: str) -> None:
        self._session = self._service.new_session(context_mode=mode)
        self._clear_chat()
