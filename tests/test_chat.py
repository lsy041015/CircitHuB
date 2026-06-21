import socket
import threading
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QStackedWidget, QWidget

from digikey_scraper._main_window import ChatDialog
from digikey_scraper._main_window_chat import MainWindowChatMixin
from digikey_scraper.chat import (
    ChatClient,
    ChatMessage,
    ChatServer,
    build_message,
    receive_frame,
    send_frame,
)
from digikey_scraper.models import ProductResult
from digikey_scraper.qt_gui import MainWindow


class ChatTests(unittest.TestCase):
    class _FakeSignal:
        def __init__(self) -> None:
            self._callbacks = []

        def connect(self, callback) -> None:
            self._callbacks.append(callback)

        def emit(self) -> None:
            for callback in list(self._callbacks):
                callback()

    class _FakeChatDialog(QWidget):
        def __init__(self, parent=None) -> None:
            super().__init__(parent)
            self.search_requested = ChatTests._FakeSignal()
            self.embedded_mode = None
            self.shared_texts: list[str] = []
            self.shared_parts: list[ProductResult] = []

        def set_embedded_mode(self, enabled: bool) -> None:
            self.embedded_mode = enabled

        def attach_share_text(self, text: str) -> None:
            self.shared_texts.append(text)

        def attach_part_card(self, result: ProductResult) -> None:
            self.shared_parts.append(result)

    class _ChatHost(MainWindowChatMixin, QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.chat_dialog = None
            self.app_stack = QStackedWidget()
            self.chat_open_btn = QPushButton()
            self.search_page = QWidget()
            self.status_messages: list[str] = []
            self.search_page_hits = 0

        def show_search_page(self) -> None:
            self.search_page_hits += 1

        def set_status(self, text: str) -> None:
            self.status_messages.append(text)

        def _tr(self, key: str, **_kw) -> str:
            return key

    def _free_port(self) -> int:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])
        finally:
            sock.close()

    def test_chat_server_broadcasts_group_messages(self) -> None:
        port = self._free_port()
        server = ChatServer("127.0.0.1", port)
        received: list[tuple[str, str]] = []
        event = threading.Event()
        joined = threading.Event()

        def on_message(message):
            received.append((message.sender, message.text))
            if message.sender == "server" and message.text == "bob joined":
                joined.set()
            if message.sender == "alice" and message.text == "hello group":
                event.set()

        server.start()
        client_a = ChatClient("127.0.0.1", port, "alice", "parts", lambda _msg: None)
        client_b = ChatClient("127.0.0.1", port, "bob", "parts", on_message)
        try:
            client_a.connect()
            client_b.connect()
            self.assertTrue(joined.wait(5))
            client_a.send("hello group")

            self.assertTrue(event.wait(5))
            self.assertIn(("alice", "hello group"), received)
        finally:
            client_a.close()
            client_b.close()
            server.stop()

    def test_chat_server_rejects_invalid_token(self) -> None:
        port = self._free_port()
        server = ChatServer("127.0.0.1", port, token="secret")
        try:
            server.start()
            with socket.create_connection(("127.0.0.1", port), timeout=2) as client:
                send_frame(client, build_message("join", "parts", "alice", "", "wrong"))
                with self.assertRaises(ConnectionError):
                    receive_frame(client)
        finally:
            server.stop()

    def test_chat_server_requires_token_when_configured(self) -> None:
        port = self._free_port()
        server = ChatServer("127.0.0.1", port, require_token=True)

        with self.assertRaises(ValueError):
            server.start()

    def test_chat_server_rejects_disallowed_peer(self) -> None:
        port = self._free_port()
        statuses: list[str] = []
        server = ChatServer("127.0.0.1", port, status_callback=statuses.append, allowed_hosts={"192.0.2.1"})
        try:
            server.start()
            with socket.create_connection(("127.0.0.1", port), timeout=2) as client:
                try:
                    send_frame(client, build_message("join", "parts", "alice", ""))
                    with self.assertRaises(ConnectionError):
                        receive_frame(client)
                except OSError:
                    pass

            self.assertTrue(any("rejected peer" in item for item in statuses))
        finally:
            server.stop()

    def test_main_window_inherits_chat_mixin(self) -> None:
        self.assertTrue(issubclass(MainWindow, MainWindowChatMixin))

    def test_chat_mixin_bridges_dialog_creation_and_shares(self) -> None:
        app = QApplication.instance() or QApplication([])
        host = self._ChatHost()
        result = ProductResult(query="NE5532P", title="Dual op amp")

        try:
            with patch(
                "digikey_scraper._main_window_chat.ChatDialog", self._FakeChatDialog
            ):
                host.open_chat()

                self.assertIsInstance(host.chat_dialog, self._FakeChatDialog)
                self.assertTrue(host.chat_dialog.embedded_mode)
                self.assertEqual(host.app_stack.count(), 1)
                self.assertIs(host.app_stack.currentWidget(), host.chat_dialog)
                self.assertEqual(host.chat_open_btn.objectName(), "ChatSideBtnActive")

                first_dialog = host.chat_dialog
                host.open_chat()
                self.assertIs(host.chat_dialog, first_dialog)
                self.assertEqual(host.app_stack.count(), 1)

                host.chat_dialog.search_requested.emit()
                self.assertEqual(host.search_page_hits, 1)

                host.share_text_to_chat("shared text")
                self.assertEqual(host.chat_dialog.shared_texts, ["shared text"])
                self.assertEqual(host.status_messages[-1], "chat_share_ready")

                host.share_part_to_chat(result)
                self.assertEqual(host.chat_dialog.shared_parts, [result])
                self.assertEqual(host.status_messages[-1], "chat_share_ready")
        finally:
            host.close()
            app.processEvents()

    def test_sidebar_chat_button_opens_dialog(self) -> None:
        app = QApplication.instance() or QApplication([])
        window = MainWindow()
        try:
            window.stop_receiver()
            window.open_chat()

            self.assertIsNotNone(window.chat_dialog)
            self.assertEqual(window.chat_open_btn.text(), window._tr("chat_open"))
        finally:
            if window.chat_dialog is not None:
                window.chat_dialog.close()
            window.close()
            app.processEvents()

    def test_chat_dialog_formats_message_transcript(self) -> None:
        app = QApplication.instance() or QApplication([])
        window = MainWindow()
        try:
            window.stop_receiver()
            dialog = ChatDialog(window)
            dialog.nickname_input.setText("alice")
            dialog.append_message(ChatMessage("message", "parts", "alice", "line 1\nline 2", 1716883200.0))
            dialog.append_status("connected")

            transcript = dialog.transcript.toPlainText()
            self.assertIn("17:00", transcript)
            self.assertIn("[parts]", transcript)
            self.assertIn("나", transcript)
            self.assertIn("line 1", transcript)
            self.assertIn("line 2", transcript)
            self.assertIn("상태: connected", transcript)
        finally:
            dialog.close()
            window.close()
            app.processEvents()
