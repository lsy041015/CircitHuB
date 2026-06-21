from __future__ import annotations

import json
from collections.abc import Callable


class OllamaTextGenerator:
    """TextGenerator port implementation backed by a local Ollama server."""

    def __init__(
        self,
        model: str = "gemma4:e4b",
        base_url: str = "http://localhost:11434",
    ) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")

    def generate(self, prompt: str) -> str:
        import httpx

        url = f"{self._base_url}/api/generate"
        payload = {"model": self._model, "prompt": prompt, "stream": False}
        resp = httpx.post(url, json=payload, timeout=60.0)
        resp.raise_for_status()
        return resp.json().get("response", "")

    def stream_chat(
        self,
        messages: list[dict],
        on_chunk: Callable[[str], None],
    ) -> str:
        import httpx

        url = f"{self._base_url}/api/chat"
        payload = {"model": self._model, "messages": messages, "stream": True}
        full: list[str] = []
        with httpx.stream("POST", url, json=payload, timeout=120.0) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                data = json.loads(line)
                chunk = data.get("message", {}).get("content", "")
                if chunk:
                    on_chunk(chunk)
                    full.append(chunk)
                if data.get("done"):
                    break
        return "".join(full)

    def is_available(self) -> bool:
        import httpx

        try:
            resp = httpx.get(f"{self._base_url}/api/tags", timeout=2.0)
            resp.raise_for_status()
            names = [m.get("name", "") for m in resp.json().get("models", [])]
            return any(self._model in name for name in names)
        except Exception:
            return False
