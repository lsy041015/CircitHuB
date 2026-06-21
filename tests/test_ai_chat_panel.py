import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6.QtWidgets import QApplication

app = QApplication.instance() or QApplication(sys.argv)


class FakeLlm:
    def stream_chat(self, messages, on_chunk):
        on_chunk("테스트")
        return "테스트"


class TestAiChatPanel(unittest.TestCase):
    def setUp(self):
        from digikey_scraper.application.ai_chat_service import AiChatService
        from digikey_scraper.infrastructure.persistence.json_ai_chat_repository import (
            JsonAiChatRepository,
        )

        self._tmp = TemporaryDirectory()
        path = Path(self._tmp.name) / "s.json"
        repo = JsonAiChatRepository(path=path)
        self._service = AiChatService(llm=FakeLlm(), repo=repo)

    def tearDown(self):
        self._tmp.cleanup()

    def test_panel_creates_without_error(self):
        from digikey_scraper._ai_chat_panel import AiChatPanel

        panel = AiChatPanel(self._service)
        self.assertIsNotNone(panel)

    def test_panel_has_send_button(self):
        from digikey_scraper._ai_chat_panel import AiChatPanel
        from PySide6.QtWidgets import QPushButton

        panel = AiChatPanel(self._service)
        buttons = panel.findChildren(QPushButton)
        labels = [b.text() for b in buttons]
        self.assertIn("전송", labels)

    def test_panel_has_new_session_button(self):
        from digikey_scraper._ai_chat_panel import AiChatPanel
        from PySide6.QtWidgets import QPushButton

        panel = AiChatPanel(self._service)
        buttons = panel.findChildren(QPushButton)
        labels = [b.text() for b in buttons]
        self.assertIn("새 대화", labels)

    def test_set_parts_context(self):
        from digikey_scraper._ai_chat_panel import AiChatPanel

        panel = AiChatPanel(self._service)
        parts = [{"name": "LM358", "price": "100"}]
        panel.set_parts_context(parts)
        self.assertEqual(panel._parts_context, parts)

    def test_context_combo_has_modes(self):
        from digikey_scraper._ai_chat_panel import AiChatPanel

        panel = AiChatPanel(self._service)
        combo = panel._ctx_combo
        self.assertGreaterEqual(combo.count(), 3)


if __name__ == "__main__":
    unittest.main()
