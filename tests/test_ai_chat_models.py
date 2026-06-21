import time
import unittest

from digikey_scraper.domain.chat_models import AiChatMessage, AiChatSession
from digikey_scraper.domain.ports import AiChatRepository


class TestAiChatMessage(unittest.TestCase):
    def test_defaults(self):
        msg = AiChatMessage(role="user", content="hello")
        self.assertEqual(msg.role, "user")
        self.assertEqual(msg.content, "hello")
        self.assertAlmostEqual(msg.timestamp, time.time(), delta=1.0)

    def test_explicit_timestamp(self):
        msg = AiChatMessage(role="assistant", content="hi", timestamp=1000.0)
        self.assertEqual(msg.timestamp, 1000.0)


class TestAiChatSession(unittest.TestCase):
    def test_defaults(self):
        session = AiChatSession()
        self.assertEqual(session.title, "새 대화")
        self.assertEqual(session.context_mode, "general")
        self.assertEqual(session.messages, [])
        self.assertTrue(len(session.id) > 0)

    def test_unique_ids(self):
        a = AiChatSession()
        b = AiChatSession()
        self.assertNotEqual(a.id, b.id)

    def test_append_messages(self):
        session = AiChatSession()
        session.messages.append(AiChatMessage(role="user", content="test"))
        self.assertEqual(len(session.messages), 1)


class TestAiChatRepositoryProtocol(unittest.TestCase):
    def test_protocol_methods(self):
        for method in ("save_session", "load_sessions", "delete_session"):
            self.assertTrue(hasattr(AiChatRepository, method))


if __name__ == "__main__":
    unittest.main()
