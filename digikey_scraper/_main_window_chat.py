from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget

from ._circuitkit_chat_design import CircuitKitChatWindow as ChatDialog
from .models import ProductResult


class MainWindowChatMixin:
    def open_chat(self):
        if self.chat_dialog is None:
            self.chat_dialog = ChatDialog(self)
            self.chat_dialog.setWindowFlags(Qt.Widget)
            self.chat_dialog.set_embedded_mode(True)
            self.chat_dialog.search_requested.connect(self.show_search_page)
            if hasattr(self, "app_stack"):
                self.app_stack.addWidget(self.chat_dialog)
        if hasattr(self, "app_stack"):
            self.app_stack.setCurrentWidget(self.chat_dialog)
        self.chat_open_btn.setObjectName("ChatSideBtnActive")
        self.chat_open_btn.style().unpolish(self.chat_open_btn)
        self.chat_open_btn.style().polish(self.chat_open_btn)

    def share_text_to_chat(self, text: str):
        self.open_chat()
        if self.chat_dialog is not None:
            self.chat_dialog.attach_share_text(text)
        self.set_status(self._tr("chat_share_ready"))

    def share_part_to_chat(self, result: ProductResult):
        self.open_chat()
        if self.chat_dialog is not None and hasattr(self.chat_dialog, "attach_part_card"):
            self.chat_dialog.attach_part_card(result)
        self.set_status(self._tr("chat_share_ready"))

    def _setup_ai_chat_dock(self) -> None:
        from ._ai_chat_panel import AiChatPanel

        self._ai_chat_panel = AiChatPanel(self.container.ai_chat, parent=self)
        dock = QDockWidget("AI 채팅", self)
        dock.setObjectName("AiChatDock")
        dock.setWidget(self._ai_chat_panel)
        dock.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        dock.hide()
        self._ai_chat_dock = dock

    def toggle_ai_chat_dock(self) -> None:
        if hasattr(self, "_ai_chat_dock"):
            if self._ai_chat_dock.isVisible():
                self._ai_chat_dock.hide()
            else:
                self._ai_chat_dock.show()
