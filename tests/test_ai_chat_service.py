import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from digikey_scraper.application.ai_chat_service import AiChatService
from digikey_scraper.infrastructure.persistence.json_ai_chat_repository import (
    JsonAiChatRepository,
)


class FakeLlm:
    def __init__(self, response: str = "답변"):
        self._response = response
        self.last_messages: list[dict] = []

    def stream_chat(self, messages, on_chunk):
        self.last_messages = messages
        on_chunk(self._response)
        return self._response


class TestAiChatService(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        path = Path(self._tmp.name) / "sessions.json"
        self._repo = JsonAiChatRepository(path=path)
        self._llm = FakeLlm("테스트 답변")
        self._service = AiChatService(llm=self._llm, repo=self._repo)

    def tearDown(self):
        self._tmp.cleanup()

    def test_new_session_defaults(self):
        s = self._service.new_session()
        self.assertEqual(s.context_mode, "general")
        self.assertEqual(s.messages, [])

    def test_send_message_adds_user_and_assistant(self):
        session = self._service.new_session()
        chunks: list[str] = []
        self._service.send_message(session, "안녕", on_chunk=chunks.append)
        self.assertEqual(len(session.messages), 2)
        self.assertEqual(session.messages[0].role, "user")
        self.assertEqual(session.messages[0].content, "안녕")
        self.assertEqual(session.messages[1].role, "assistant")
        self.assertEqual(session.messages[1].content, "테스트 답변")
        self.assertEqual(chunks, ["테스트 답변"])

    def test_send_message_sets_title_on_first_exchange(self):
        session = self._service.new_session()
        self._service.send_message(session, "부품 추천해줘", on_chunk=lambda c: None)
        self.assertEqual(session.title, "부품 추천해줘")

    def test_send_message_persists_session(self):
        session = self._service.new_session()
        self._service.send_message(session, "test", on_chunk=lambda c: None)
        loaded = self._service.load_sessions()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].id, session.id)

    def test_parts_context_injected_as_system_message(self):
        session = self._service.new_session(context_mode="parts")
        parts = [{"name": "LM358P", "price": "100"}]
        self._service.send_message(
            session, "가장 싼 거?", on_chunk=lambda c: None, parts_context=parts
        )
        msgs = self._llm.last_messages
        self.assertEqual(msgs[0]["role"], "system")
        self.assertIn("LM358P", msgs[0]["content"])

    def test_no_system_message_for_general_mode(self):
        session = self._service.new_session(context_mode="general")
        self._service.send_message(session, "hello", on_chunk=lambda c: None)
        msgs = self._llm.last_messages
        self.assertFalse(any(m["role"] == "system" for m in msgs))

    def test_history_included_in_subsequent_messages(self):
        session = self._service.new_session()
        self._service.send_message(session, "첫 번째", on_chunk=lambda c: None)
        self._service.send_message(session, "두 번째", on_chunk=lambda c: None)
        msgs = self._llm.last_messages
        roles = [m["role"] for m in msgs]
        self.assertIn("user", roles)
        self.assertIn("assistant", roles)

    def test_delete_session(self):
        session = self._service.new_session()
        self._service.send_message(session, "test", on_chunk=lambda c: None)
        self._service.delete_session(session.id)
        self.assertEqual(self._service.load_sessions(), [])

    def test_datasheet_context_injects_title(self):
        session = self._service.new_session(context_mode="datasheet")
        self._service.send_message(
            session,
            "최대 전압은?",
            on_chunk=lambda c: None,
            parts_context=[{"title": "LM358 Datasheet"}],
        )
        msgs = self._llm.last_messages
        self.assertEqual(msgs[0]["role"], "system")
        self.assertIn("LM358 Datasheet", msgs[0]["content"])


if __name__ == "__main__":
    unittest.main()
