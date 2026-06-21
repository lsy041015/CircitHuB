import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from digikey_scraper.application.ai_chat_service import AiChatService
from digikey_scraper.infrastructure.persistence.json_ai_chat_repository import (
    JsonAiChatRepository,
)
from digikey_scraper.workers import AiChatSignals, AiChatWorker


class FakeLlm:
    def __init__(self, response: str = "응답"):
        self._response = response

    def stream_chat(self, messages, on_chunk):
        on_chunk(self._response)
        return self._response


class TestAiChatWorker(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        path = Path(self._tmp.name) / "sessions.json"
        repo = JsonAiChatRepository(path=path)
        self._service = AiChatService(llm=FakeLlm(), repo=repo)

    def tearDown(self):
        self._tmp.cleanup()

    def test_worker_emits_chunk_and_finished(self):
        import sys

        from PySide6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication(sys.argv)

        session = self._service.new_session()
        worker = AiChatWorker(self._service, session, "안녕")

        chunks: list[str] = []
        finished: list[str] = []
        worker.signals.chunk.connect(chunks.append)
        worker.signals.finished.connect(finished.append)

        worker.start()
        if worker._thread:
            worker._thread.join(timeout=3.0)
        import time
        for _ in range(20):
            app.processEvents()
            if chunks:
                break
            time.sleep(0.01)

        self.assertEqual(chunks, ["응답"])
        self.assertEqual(finished, ["응답"])

    def test_worker_signals_attributes(self):
        session = self._service.new_session()
        worker = AiChatWorker(self._service, session, "test")
        self.assertIsInstance(worker.signals, AiChatSignals)

    def test_container_has_ai_chat(self):
        from digikey_scraper.application.ai_chat_service import AiChatService
        from digikey_scraper.container import build_container

        container = build_container()
        self.assertIsNotNone(container.ai_chat)
        self.assertIsInstance(container.ai_chat, AiChatService)


if __name__ == "__main__":
    unittest.main()
