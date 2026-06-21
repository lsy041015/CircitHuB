import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from digikey_scraper.domain.chat_models import AiChatMessage, AiChatSession
from digikey_scraper.infrastructure.persistence.json_ai_chat_repository import (
    JsonAiChatRepository,
)


def _make_session(title: str = "test", context: str = "general") -> AiChatSession:
    s = AiChatSession(title=title, context_mode=context)
    s.messages.append(AiChatMessage(role="user", content="hello", timestamp=1000.0))
    s.messages.append(AiChatMessage(role="assistant", content="hi", timestamp=1001.0))
    return s


class TestJsonAiChatRepository(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self._path = Path(self._tmp.name) / "ai_chat_sessions.json"
        self._repo = JsonAiChatRepository(path=self._path)

    def tearDown(self):
        self._tmp.cleanup()

    def test_load_empty_when_file_missing(self):
        self.assertEqual(self._repo.load_sessions(), [])

    def test_save_and_load_round_trip(self):
        s = _make_session("부품 문의", "parts")
        self._repo.save_session(s)
        loaded = self._repo.load_sessions()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].id, s.id)
        self.assertEqual(loaded[0].title, "부품 문의")
        self.assertEqual(loaded[0].context_mode, "parts")
        self.assertEqual(len(loaded[0].messages), 2)
        self.assertEqual(loaded[0].messages[0].role, "user")
        self.assertEqual(loaded[0].messages[1].content, "hi")

    def test_save_updates_existing_session(self):
        s = _make_session()
        self._repo.save_session(s)
        s.title = "수정된 제목"
        self._repo.save_session(s)
        loaded = self._repo.load_sessions()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].title, "수정된 제목")

    def test_delete_session(self):
        s1 = _make_session("A")
        s2 = _make_session("B")
        self._repo.save_session(s1)
        self._repo.save_session(s2)
        self._repo.delete_session(s1.id)
        loaded = self._repo.load_sessions()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].id, s2.id)

    def test_delete_nonexistent_is_noop(self):
        s = _make_session()
        self._repo.save_session(s)
        self._repo.delete_session("does-not-exist")
        self.assertEqual(len(self._repo.load_sessions()), 1)

    def test_load_sessions_sorted_by_updated_at_desc(self):
        s1 = AiChatSession(title="old")
        s1.updated_at = 1000.0
        s2 = AiChatSession(title="new")
        s2.updated_at = 2000.0
        self._repo.save_session(s1)
        self._repo.save_session(s2)
        loaded = self._repo.load_sessions()
        self.assertEqual(loaded[0].title, "new")

    def test_corrupted_file_returns_empty(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text("not-json", encoding="utf-8")
        self.assertEqual(self._repo.load_sessions(), [])


if __name__ == "__main__":
    unittest.main()
