import json
import unittest
from unittest.mock import MagicMock, patch

from digikey_scraper.infrastructure.llm.ollama_text_generator import OllamaTextGenerator


def _make_stream_response(chunks: list[str]) -> MagicMock:
    lines = []
    for i, chunk in enumerate(chunks):
        done = i == len(chunks) - 1
        lines.append(json.dumps({"message": {"content": chunk}, "done": done}))
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.raise_for_status = MagicMock()
    mock_resp.iter_lines = MagicMock(return_value=iter(lines))
    return mock_resp


class TestOllamaAvailability(unittest.TestCase):
    def test_is_available_true_when_model_found(self):
        gen = OllamaTextGenerator(model="gemma4:e4b")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value={"models": [{"name": "gemma4:e4b"}]})
        with patch("httpx.get", return_value=mock_resp):
            self.assertTrue(gen.is_available())

    def test_is_available_false_when_model_missing(self):
        gen = OllamaTextGenerator(model="gemma4:e4b")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value={"models": [{"name": "llama3"}]})
        with patch("httpx.get", return_value=mock_resp):
            self.assertFalse(gen.is_available())

    def test_is_available_false_on_connection_error(self):
        gen = OllamaTextGenerator()
        with patch("httpx.get", side_effect=Exception("refused")):
            self.assertFalse(gen.is_available())


class TestOllamaStreamChat(unittest.TestCase):
    def test_stream_chat_calls_on_chunk_for_each_chunk(self):
        gen = OllamaTextGenerator()
        received: list[str] = []
        mock_resp = _make_stream_response(["Hello", " world"])
        with patch("httpx.stream", return_value=mock_resp):
            result = gen.stream_chat(
                [{"role": "user", "content": "hi"}],
                on_chunk=received.append,
            )
        self.assertEqual(received, ["Hello", " world"])
        self.assertEqual(result, "Hello world")

    def test_stream_chat_skips_empty_chunks(self):
        gen = OllamaTextGenerator()
        received: list[str] = []
        lines = [
            json.dumps({"message": {"content": ""}, "done": False}),
            json.dumps({"message": {"content": "hi"}, "done": True}),
        ]
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.raise_for_status = MagicMock()
        mock_resp.iter_lines = MagicMock(return_value=iter(lines))
        with patch("httpx.stream", return_value=mock_resp):
            gen.stream_chat([{"role": "user", "content": "hi"}], on_chunk=received.append)
        self.assertEqual(received, ["hi"])


if __name__ == "__main__":
    unittest.main()
