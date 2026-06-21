# 로컬 LLM 채팅 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ollama + Gemma4:e4b 로컬 LLM을 활용한 AI 채팅 기능을 메인 윈도우 사이드 패널과 데이터시트 뷰어에 추가한다.

**Architecture:** 기존 헥사고날 아키텍처를 그대로 따른다. `TextGenerator` 포트 구현체로 `OllamaTextGenerator`를 추가하고, `AiChatService` (application layer)가 세션/컨텍스트/스트리밍을 오케스트레이션한다. Qt 레이어는 기존 `SearchWorker` 패턴을 그대로 따르는 `AiChatWorker`로 스트리밍을 처리한다.

**Tech Stack:** Python 3, PySide6, httpx>=0.27 (Ollama HTTP + 스트리밍), Ollama (`gemma4:e4b`)

## Global Constraints

- 이모지 사용 금지 — 버튼 텍스트, 레이블, 주석, 문자열 리터럴 모두
- `QT_QPA_PLATFORM=offscreen` 필수 — 모든 테스트 실행 시
- 레이어 의존성 규칙 준수: `domain` <- `application` <- `infrastructure` / `digikey_scraper`
- 기존 `container.py` 패턴 유지: `@dataclass Container` + factory 함수
- `runtime_path()` 사용 — 절대 경로 하드코딩 금지
- 테스트 임포트 경로: `from digikey_scraper.<module> import <class>`

---

### Task 1: Domain 데이터 모델 + AiChatRepository 포트

**Files:**
- Create: `digikey_scraper/domain/chat_models.py`
- Modify: `digikey_scraper/domain/ports.py`
- Test: `tests/test_ai_chat_models.py`

**Interfaces:**
- Produces:
  - `AiChatMessage(role: str, content: str, timestamp: float)`
  - `AiChatSession(id: str, title: str, context_mode: str, messages: list[AiChatMessage], created_at: float, updated_at: float)`
  - `AiChatRepository` Protocol — `save_session / load_sessions / delete_session`

- [ ] **Step 1: `domain/chat_models.py` 생성**

```python
# digikey_scraper/domain/chat_models.py
from __future__ import annotations

import time
from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class AiChatMessage:
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class AiChatSession:
    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = "새 대화"
    context_mode: str = "general"
    messages: list[AiChatMessage] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
```

- [ ] **Step 2: `domain/ports.py`에 `AiChatRepository` 포트 추가**

`ports.py` 상단 임포트 블록에 추가:
```python
from .chat_models import AiChatSession
```

파일 끝에 추가:
```python
@runtime_checkable
class AiChatRepository(Protocol):
    """Persists AI chat sessions. JSON adapter is the default."""

    def save_session(self, session: AiChatSession) -> None: ...

    def load_sessions(self) -> list[AiChatSession]: ...

    def delete_session(self, session_id: str) -> None: ...
```

- [ ] **Step 3: 테스트 작성**

```python
# tests/test_ai_chat_models.py
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
```

- [ ] **Step 4: 테스트 실행 — PASS 확인**

```bash
QT_QPA_PLATFORM=offscreen pytest tests/test_ai_chat_models.py -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 5: 커밋**

```bash
git add digikey_scraper/domain/chat_models.py digikey_scraper/domain/ports.py tests/test_ai_chat_models.py
git commit -m "feat: add AiChatMessage, AiChatSession domain models and AiChatRepository port"
```

---

### Task 2: httpx 의존성 + Ollama 어댑터

**Files:**
- Modify: `requirements.txt`
- Create: `digikey_scraper/infrastructure/llm/__init__.py`
- Create: `digikey_scraper/infrastructure/llm/ollama_text_generator.py`
- Test: `tests/test_ollama_text_generator.py`

**Interfaces:**
- Consumes: `TextGenerator` Protocol from `domain/ports.py`
- Produces: `OllamaTextGenerator(model: str = "gemma4:e4b", base_url: str = "http://localhost:11434")`
  - `.generate(prompt: str) -> str`
  - `.stream_chat(messages: list[dict], on_chunk: Callable[[str], None]) -> str`
  - `.is_available() -> bool`

- [ ] **Step 1: `requirements.txt`에 httpx 추가**

기존 `requirements.txt` 끝에 추가:
```
httpx>=0.27
```

- [ ] **Step 2: `infrastructure/llm/__init__.py` 생성 (빈 파일)**

```python
# digikey_scraper/infrastructure/llm/__init__.py
```

- [ ] **Step 3: `OllamaTextGenerator` 구현**

```python
# digikey_scraper/infrastructure/llm/ollama_text_generator.py
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
```

- [ ] **Step 4: 테스트 작성**

```python
# tests/test_ollama_text_generator.py
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
```

- [ ] **Step 5: 의존성 설치 + 테스트 실행**

```bash
pip install httpx
QT_QPA_PLATFORM=offscreen pytest tests/test_ollama_text_generator.py -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 6: 커밋**

```bash
git add requirements.txt digikey_scraper/infrastructure/llm/ tests/test_ollama_text_generator.py
git commit -m "feat: add OllamaTextGenerator adapter with streaming and availability check"
```

---

### Task 3: JSON AI 채팅 세션 저장소

**Files:**
- Create: `digikey_scraper/infrastructure/persistence/json_ai_chat_repository.py`
- Test: `tests/test_json_ai_chat_repository.py`

**Interfaces:**
- Consumes: `AiChatSession`, `AiChatMessage` from `domain.chat_models`, `runtime_path` from `_helpers`
- Produces: `JsonAiChatRepository(path: Path | None = None)` — implements `AiChatRepository`
  - 저장 위치: `runtime_path("ai_chat_sessions.json")`

- [ ] **Step 1: 구현 작성**

```python
# digikey_scraper/infrastructure/persistence/json_ai_chat_repository.py
from __future__ import annotations

import json
from pathlib import Path

from ..._helpers import runtime_path
from ...domain.chat_models import AiChatMessage, AiChatSession

SESSIONS_FILE = "ai_chat_sessions.json"


def _session_to_dict(session: AiChatSession) -> dict:
    return {
        "id": session.id,
        "title": session.title,
        "context_mode": session.context_mode,
        "messages": [
            {"role": m.role, "content": m.content, "timestamp": m.timestamp}
            for m in session.messages
        ],
        "created_at": session.created_at,
        "updated_at": session.updated_at,
    }


def _session_from_dict(data: dict) -> AiChatSession:
    messages = [
        AiChatMessage(
            role=m["role"],
            content=m["content"],
            timestamp=m.get("timestamp", 0.0),
        )
        for m in data.get("messages", [])
    ]
    return AiChatSession(
        id=data["id"],
        title=data.get("title", "새 대화"),
        context_mode=data.get("context_mode", "general"),
        messages=messages,
        created_at=data.get("created_at", 0.0),
        updated_at=data.get("updated_at", 0.0),
    )


class JsonAiChatRepository:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or runtime_path(SESSIONS_FILE)

    def _read(self) -> dict:
        if not self._path.exists():
            return {"sessions": []}
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:
            return {"sessions": []}

    def _write(self, data: dict) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def save_session(self, session: AiChatSession) -> None:
        data = self._read()
        sessions = data.get("sessions", [])
        updated = False
        for i, s in enumerate(sessions):
            if s.get("id") == session.id:
                sessions[i] = _session_to_dict(session)
                updated = True
                break
        if not updated:
            sessions.append(_session_to_dict(session))
        data["sessions"] = sessions
        self._write(data)

    def load_sessions(self) -> list[AiChatSession]:
        data = self._read()
        out: list[AiChatSession] = []
        for raw in data.get("sessions", []):
            try:
                out.append(_session_from_dict(raw))
            except Exception:
                continue
        return sorted(out, key=lambda s: s.updated_at, reverse=True)

    def delete_session(self, session_id: str) -> None:
        data = self._read()
        data["sessions"] = [
            s for s in data.get("sessions", []) if s.get("id") != session_id
        ]
        self._write(data)
```

- [ ] **Step 2: 테스트 작성**

```python
# tests/test_json_ai_chat_repository.py
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
```

- [ ] **Step 3: 테스트 실행 — PASS 확인**

```bash
QT_QPA_PLATFORM=offscreen pytest tests/test_json_ai_chat_repository.py -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 4: 커밋**

```bash
git add digikey_scraper/infrastructure/persistence/json_ai_chat_repository.py tests/test_json_ai_chat_repository.py
git commit -m "feat: add JsonAiChatRepository with save/load/delete and round-trip persistence"
```

---

### Task 4: AiChatService

**Files:**
- Create: `digikey_scraper/application/ai_chat_service.py`
- Test: `tests/test_ai_chat_service.py`

**Interfaces:**
- Consumes:
  - `OllamaTextGenerator.stream_chat(messages: list[dict], on_chunk: Callable[[str], None]) -> str`
  - `AiChatRepository.save_session / load_sessions / delete_session`
  - `RagService.retrieve(question: str, top_k: int) -> list[RetrievedChunk]` (optional)
- Produces: `AiChatService`
  - `.new_session(context_mode: str = "general") -> AiChatSession`
  - `.send_message(session, text, on_chunk, parts_context, rag_query) -> str`
  - `.load_sessions() -> list[AiChatSession]`
  - `.save_session(session) -> None`
  - `.delete_session(session_id) -> None`

- [ ] **Step 1: 구현 작성**

```python
# digikey_scraper/application/ai_chat_service.py
from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import TYPE_CHECKING

from ..domain.chat_models import AiChatMessage, AiChatSession

if TYPE_CHECKING:
    from ..infrastructure.llm.ollama_text_generator import OllamaTextGenerator
    from ..domain.ports import AiChatRepository
    from .rag_service import RagService

MAX_HISTORY_MESSAGES = 10


class AiChatService:
    def __init__(
        self,
        llm: "OllamaTextGenerator",
        repo: "AiChatRepository",
        rag_service: "RagService | None" = None,
    ) -> None:
        self._llm = llm
        self._repo = repo
        self._rag = rag_service

    def new_session(self, context_mode: str = "general") -> AiChatSession:
        return AiChatSession(context_mode=context_mode)

    def send_message(
        self,
        session: AiChatSession,
        text: str,
        on_chunk: Callable[[str], None],
        parts_context: list[dict] | None = None,
        rag_query: str | None = None,
    ) -> str:
        now = time.time()
        session.messages.append(AiChatMessage(role="user", content=text, timestamp=now))

        ollama_messages = self._build_messages(session, text, parts_context, rag_query)
        response = self._llm.stream_chat(ollama_messages, on_chunk)

        session.messages.append(
            AiChatMessage(role="assistant", content=response, timestamp=time.time())
        )
        session.updated_at = time.time()

        if len(session.messages) == 2:
            session.title = text[:30]

        self._repo.save_session(session)
        return response

    def load_sessions(self) -> list[AiChatSession]:
        return self._repo.load_sessions()

    def save_session(self, session: AiChatSession) -> None:
        self._repo.save_session(session)

    def delete_session(self, session_id: str) -> None:
        self._repo.delete_session(session_id)

    def _build_messages(
        self,
        session: AiChatSession,
        text: str,
        parts_context: list[dict] | None,
        rag_query: str | None,
    ) -> list[dict]:
        messages: list[dict] = []

        if session.context_mode == "parts" and parts_context:
            system = (
                "사용자의 부품 검색 결과입니다:\n"
                + json.dumps(parts_context, ensure_ascii=False, indent=2)
                + "\n\n이 데이터를 참고해서 답변하세요."
            )
            messages.append({"role": "system", "content": system})
        elif session.context_mode == "rag" and self._rag is not None:
            query = rag_query or text
            chunks = self._rag.retrieve(query, top_k=3)
            if chunks:
                context = "\n".join(
                    f"[{c.chunk.id}] {c.chunk.text}" for c in chunks
                )
                system = (
                    "다음은 데이터시트에서 검색된 내용입니다:\n"
                    + context
                    + "\n\n이 내용을 바탕으로 답변하세요."
                )
                messages.append({"role": "system", "content": system})
        elif session.context_mode == "datasheet":
            if parts_context and parts_context[0].get("title"):
                system = (
                    f"현재 보고 있는 데이터시트: {parts_context[0]['title']}. "
                    "이 데이터시트에 관한 질문에 답해주세요."
                )
                messages.append({"role": "system", "content": system})

        history = session.messages[:-1]
        for msg in history[-MAX_HISTORY_MESSAGES:]:
            messages.append({"role": msg.role, "content": msg.content})

        messages.append({"role": "user", "content": text})
        return messages
```

- [ ] **Step 2: 테스트 작성**

```python
# tests/test_ai_chat_service.py
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
```

- [ ] **Step 3: 테스트 실행 — PASS 확인**

```bash
QT_QPA_PLATFORM=offscreen pytest tests/test_ai_chat_service.py -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 4: 커밋**

```bash
git add digikey_scraper/application/ai_chat_service.py tests/test_ai_chat_service.py
git commit -m "feat: add AiChatService with context injection, history, and session persistence"
```

---

### Task 5: Qt 스트리밍 워커 + Container 연결

**Files:**
- Modify: `digikey_scraper/workers.py`
- Modify: `digikey_scraper/container.py`
- Test: `tests/test_ai_chat_worker.py`

**Interfaces:**
- Consumes: `AiChatService` (Task 4), `AiChatSession` (Task 1)
- Produces:
  - `AiChatSignals(QObject)` — `chunk_received: Signal(str)`, `finished: Signal(str)`, `failed: Signal(str)`
  - `AiChatWorker(service, session, text, signals, parts_context, rag_query)` — `.run()`
  - `Container.ai_chat: AiChatService`

- [ ] **Step 1: `workers.py` 임포트 추가**

`workers.py` 상단 기존 임포트 블록 끝에 추가:
```python
from .application.ai_chat_service import AiChatService
from .domain.chat_models import AiChatSession
```

- [ ] **Step 2: `workers.py` 끝에 클래스 추가**

```python
class AiChatSignals(QObject):
    chunk_received = Signal(str)
    finished = Signal(str)
    failed = Signal(str)


class AiChatWorker:
    """Thin Qt adapter that runs AiChatService.send_message in a background thread."""

    def __init__(
        self,
        service: AiChatService,
        session: AiChatSession,
        text: str,
        signals: AiChatSignals,
        parts_context: list[dict] | None = None,
        rag_query: str | None = None,
    ) -> None:
        self._service = service
        self._session = session
        self._text = text
        self._signals = signals
        self._parts_context = parts_context
        self._rag_query = rag_query

    def run(self) -> None:
        try:
            response = self._service.send_message(
                session=self._session,
                text=self._text,
                on_chunk=self._signals.chunk_received.emit,
                parts_context=self._parts_context,
                rag_query=self._rag_query,
            )
            self._signals.finished.emit(response)
        except Exception as exc:
            self._signals.failed.emit(str(exc))
```

- [ ] **Step 3: `container.py` 전체 교체**

```python
# digikey_scraper/container.py
from __future__ import annotations

from dataclasses import dataclass

from .application.ai_chat_service import AiChatService
from .application.settings_service import FileSettingsStore
from .domain.ports import ResultRepository, SettingsStore
from .infrastructure.llm.ollama_text_generator import OllamaTextGenerator
from .infrastructure.persistence.json_ai_chat_repository import JsonAiChatRepository
from .infrastructure.persistence.json_repository import JsonResultRepository


@dataclass
class Container:
    results: ResultRepository
    settings: SettingsStore
    ai_chat: AiChatService


def _build_result_repository() -> ResultRepository:
    try:
        from .infrastructure.persistence.db import db_available, make_engine

        if db_available():
            from .infrastructure.persistence.pg_repository import PgResultRepository

            return PgResultRepository(make_engine())
    except Exception:
        pass
    return JsonResultRepository()


def build_container() -> Container:
    ollama = OllamaTextGenerator()
    chat_repo = JsonAiChatRepository()
    return Container(
        results=_build_result_repository(),
        settings=FileSettingsStore(),
        ai_chat=AiChatService(llm=ollama, repo=chat_repo),
    )
```

- [ ] **Step 4: 테스트 작성**

```python
# tests/test_ai_chat_worker.py
import sys
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6.QtWidgets import QApplication

from digikey_scraper.application.ai_chat_service import AiChatService
from digikey_scraper.infrastructure.persistence.json_ai_chat_repository import (
    JsonAiChatRepository,
)
from digikey_scraper.workers import AiChatSignals, AiChatWorker

_app = None


def setUpModule():
    global _app
    _app = QApplication.instance() or QApplication(sys.argv)


class FakeLlm:
    def stream_chat(self, messages, on_chunk):
        on_chunk("청크1")
        on_chunk("청크2")
        return "청크1청크2"


class BrokenLlm:
    def stream_chat(self, messages, on_chunk):
        raise RuntimeError("connection refused")


class TestAiChatWorker(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        path = Path(self._tmp.name) / "sessions.json"
        repo = JsonAiChatRepository(path=path)
        self._service = AiChatService(llm=FakeLlm(), repo=repo)

    def tearDown(self):
        self._tmp.cleanup()

    def test_worker_emits_chunks_and_finished(self):
        session = self._service.new_session()
        signals = AiChatSignals()
        chunks_received: list[str] = []
        finished_received: list[str] = []
        signals.chunk_received.connect(chunks_received.append)
        signals.finished.connect(finished_received.append)

        worker = AiChatWorker(self._service, session, "테스트", signals)
        t = threading.Thread(target=worker.run)
        t.start()
        t.join(timeout=5)

        self.assertEqual(chunks_received, ["청크1", "청크2"])
        self.assertEqual(finished_received, ["청크1청크2"])

    def test_worker_emits_failed_on_error(self):
        tmp = TemporaryDirectory()
        repo = JsonAiChatRepository(path=Path(tmp.name) / "s.json")
        service = AiChatService(llm=BrokenLlm(), repo=repo)
        session = service.new_session()
        signals = AiChatSignals()
        errors: list[str] = []
        signals.failed.connect(errors.append)

        worker = AiChatWorker(service, session, "hi", signals)
        t = threading.Thread(target=worker.run)
        t.start()
        t.join(timeout=5)

        self.assertEqual(len(errors), 1)
        self.assertIn("connection refused", errors[0])
        tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 5: 테스트 실행 — PASS 확인**

```bash
QT_QPA_PLATFORM=offscreen pytest tests/test_ai_chat_worker.py -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 6: 기존 테스트 회귀 확인**

```bash
QT_QPA_PLATFORM=offscreen pytest tests/test_p0_layers.py -v
```

Expected: 기존 테스트 모두 PASS

- [ ] **Step 7: 커밋**

```bash
git add digikey_scraper/workers.py digikey_scraper/container.py tests/test_ai_chat_worker.py
git commit -m "feat: add AiChatWorker/Signals, wire AiChatService into Container"
```

---

### Task 6: AI 채팅 패널 위젯

**Files:**
- Create: `digikey_scraper/_ai_chat_panel.py`
- Test: `tests/test_ai_chat_panel.py`

**Interfaces:**
- Consumes: `AiChatService` (Task 4), `AiChatWorker`/`AiChatSignals` (Task 5), `AiChatSession` (Task 1)
- Produces: `AiChatPanel(QWidget)`
  - `.set_parts_context(parts: list[dict]) -> None`
  - `._session: AiChatSession | None`
  - `._context_combo: QComboBox`
  - `._msgs_layout: QVBoxLayout`

- [ ] **Step 1: 패널 위젯 구현**

```python
# digikey_scraper/_ai_chat_panel.py
from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .application.ai_chat_service import AiChatService
from .domain.chat_models import AiChatSession
from .workers import AiChatSignals, AiChatWorker

if TYPE_CHECKING:
    pass

_CONTEXT_OPTIONS = [
    ("일반", "general"),
    ("현재 부품 결과", "parts"),
    ("데이터시트 RAG", "rag"),
    ("데이터시트", "datasheet"),
]


class _MessageLabel(QLabel):
    def __init__(self, role: str, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setWordWrap(True)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        if role == "user":
            self.setStyleSheet(
                "QLabel { background:#2D3149; color:#FFFFFF; border-radius:6px;"
                " padding:8px 12px; margin:4px 40px 4px 8px; }"
            )
        else:
            self.setStyleSheet(
                "QLabel { background:#1E2130; color:#E0E4FF; border-radius:6px;"
                " padding:8px 12px; margin:4px 8px 4px 40px; }"
            )


class AiChatPanel(QWidget):
    def __init__(self, service: AiChatService, parent=None) -> None:
        super().__init__(parent)
        self._service = service
        self._session: AiChatSession | None = None
        self._sessions: list[AiChatSession] = []
        self._worker: AiChatWorker | None = None
        self._thread: threading.Thread | None = None
        self._signals: AiChatSignals | None = None
        self._current_ai_label: _MessageLabel | None = None
        self._parts_context: list[dict] | None = None
        self._build_ui()
        self._load_sessions()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        header = QHBoxLayout()
        self._session_combo = QComboBox()
        self._session_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._session_combo.currentIndexChanged.connect(self._on_session_changed)
        self._new_btn = QPushButton("새 대화")
        self._new_btn.setFixedWidth(70)
        self._new_btn.clicked.connect(self._new_session)
        self._del_btn = QPushButton("삭제")
        self._del_btn.setFixedWidth(50)
        self._del_btn.clicked.connect(self._delete_current_session)
        header.addWidget(self._session_combo)
        header.addWidget(self._new_btn)
        header.addWidget(self._del_btn)
        root.addLayout(header)

        ctx_row = QHBoxLayout()
        ctx_row.addWidget(QLabel("컨텍스트:"))
        self._context_combo = QComboBox()
        for label, mode in _CONTEXT_OPTIONS:
            self._context_combo.addItem(label, userData=mode)
        ctx_row.addWidget(self._context_combo)
        root.addLayout(ctx_row)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._msgs_widget = QWidget()
        self._msgs_layout = QVBoxLayout(self._msgs_widget)
        self._msgs_layout.setAlignment(Qt.AlignTop)
        self._msgs_layout.setSpacing(4)
        self._scroll.setWidget(self._msgs_widget)
        root.addWidget(self._scroll, 1)

        input_row = QHBoxLayout()
        self._input = QTextEdit()
        self._input.setFixedHeight(60)
        self._input.setPlaceholderText("메시지 입력 (Ctrl+Enter 전송)")
        self._send_btn = QPushButton("전송")
        self._send_btn.setFixedWidth(60)
        self._send_btn.setFixedHeight(60)
        self._send_btn.clicked.connect(self._send)
        input_row.addWidget(self._input)
        input_row.addWidget(self._send_btn)
        root.addLayout(input_row)

        self._input.installEventFilter(self)

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent

        if obj is self._input and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter) and event.modifiers() & Qt.ControlModifier:
                self._send()
                return True
        return super().eventFilter(obj, event)

    def set_parts_context(self, parts: list[dict]) -> None:
        self._parts_context = parts

    def _load_sessions(self) -> None:
        self._sessions = self._service.load_sessions()
        self._refresh_session_combo()
        if self._sessions:
            self._load_session(self._sessions[0])
        else:
            self._new_session()

    def _refresh_session_combo(self) -> None:
        self._session_combo.blockSignals(True)
        self._session_combo.clear()
        for s in self._sessions:
            self._session_combo.addItem(s.title, userData=s.id)
        self._session_combo.blockSignals(False)

    def _new_session(self) -> None:
        mode = self._context_combo.currentData() or "general"
        self._session = self._service.new_session(context_mode=mode)
        self._sessions.insert(0, self._session)
        self._refresh_session_combo()
        self._session_combo.setCurrentIndex(0)
        self._clear_messages()

    def _delete_current_session(self) -> None:
        if self._session is None:
            return
        self._service.delete_session(self._session.id)
        self._sessions = [s for s in self._sessions if s.id != self._session.id]
        self._refresh_session_combo()
        if self._sessions:
            self._load_session(self._sessions[0])
        else:
            self._new_session()

    def _on_session_changed(self, index: int) -> None:
        if index < 0 or index >= len(self._sessions):
            return
        self._load_session(self._sessions[index])

    def _load_session(self, session: AiChatSession) -> None:
        self._session = session
        idx = self._context_combo.findData(session.context_mode)
        if idx >= 0:
            self._context_combo.blockSignals(True)
            self._context_combo.setCurrentIndex(idx)
            self._context_combo.blockSignals(False)
        self._clear_messages()
        for msg in session.messages:
            lbl = _MessageLabel(msg.role, msg.content)
            self._msgs_layout.addWidget(lbl)
        self._scroll_to_bottom()

    def _clear_messages(self) -> None:
        while self._msgs_layout.count():
            item = self._msgs_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _append_bubble(self, role: str, text: str = "") -> _MessageLabel:
        lbl = _MessageLabel(role, text)
        self._msgs_layout.addWidget(lbl)
        self._scroll_to_bottom()
        return lbl

    def _scroll_to_bottom(self) -> None:
        self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        )

    def _send(self) -> None:
        text = self._input.toPlainText().strip()
        if not text or self._worker is not None or self._session is None:
            return
        self._input.clear()

        self._append_bubble("user", text)
        self._current_ai_label = self._append_bubble("assistant", "")

        mode = self._context_combo.currentData() or "general"
        self._session.context_mode = mode
        parts_context = self._parts_context if mode in ("parts", "datasheet") else None

        signals = AiChatSignals()
        signals.chunk_received.connect(self._on_chunk)
        signals.finished.connect(self._on_finished)
        signals.failed.connect(self._on_failed)
        self._signals = signals

        worker = AiChatWorker(
            self._service,
            self._session,
            text,
            signals,
            parts_context=parts_context,
        )
        self._worker = worker
        self._send_btn.setEnabled(False)

        self._thread = threading.Thread(target=worker.run, daemon=True)
        self._thread.start()

    def _on_chunk(self, chunk: str) -> None:
        if self._current_ai_label is not None:
            self._current_ai_label.setText(self._current_ai_label.text() + chunk)
            self._scroll_to_bottom()

    def _on_finished(self, response: str) -> None:
        self._worker = None
        self._thread = None
        self._send_btn.setEnabled(True)
        if self._session is not None:
            idx = self._session_combo.findData(self._session.id)
            if idx >= 0:
                self._session_combo.setItemText(idx, self._session.title)

    def _on_failed(self, error: str) -> None:
        self._worker = None
        self._thread = None
        self._send_btn.setEnabled(True)
        if self._current_ai_label is not None:
            self._current_ai_label.setText(f"오류: {error}")
```

- [ ] **Step 2: 테스트 작성**

```python
# tests/test_ai_chat_panel.py
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6.QtWidgets import QApplication

from digikey_scraper.application.ai_chat_service import AiChatService
from digikey_scraper.infrastructure.persistence.json_ai_chat_repository import (
    JsonAiChatRepository,
)
from digikey_scraper._ai_chat_panel import AiChatPanel

_app = None


def setUpModule():
    global _app
    _app = QApplication.instance() or QApplication(sys.argv)


class FakeLlm:
    def stream_chat(self, messages, on_chunk):
        on_chunk("테스트")
        return "테스트"


class TestAiChatPanel(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        path = Path(self._tmp.name) / "s.json"
        repo = JsonAiChatRepository(path=path)
        service = AiChatService(llm=FakeLlm(), repo=repo)
        self._panel = AiChatPanel(service)

    def tearDown(self):
        self._panel.deleteLater()
        self._tmp.cleanup()

    def test_panel_creates_new_session_on_init(self):
        self.assertIsNotNone(self._panel._session)

    def test_new_session_clears_messages(self):
        self._panel._new_session()
        self.assertEqual(self._panel._msgs_layout.count(), 0)

    def test_set_parts_context(self):
        parts = [{"name": "LM358P", "price": "100"}]
        self._panel.set_parts_context(parts)
        self.assertEqual(self._panel._parts_context, parts)

    def test_context_combo_has_four_options(self):
        self.assertEqual(self._panel._context_combo.count(), 4)

    def test_session_combo_updated_on_new_session(self):
        initial_count = self._panel._session_combo.count()
        self._panel._new_session()
        self.assertEqual(self._panel._session_combo.count(), initial_count + 1)

    def test_delete_session_reduces_combo_count(self):
        self._panel._new_session()
        count_before = self._panel._session_combo.count()
        self._panel._delete_current_session()
        self.assertEqual(self._panel._session_combo.count(), count_before - 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: 테스트 실행 — PASS 확인**

```bash
QT_QPA_PLATFORM=offscreen pytest tests/test_ai_chat_panel.py -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 4: 커밋**

```bash
git add digikey_scraper/_ai_chat_panel.py tests/test_ai_chat_panel.py
git commit -m "feat: add AiChatPanel widget with session management, context modes, and streaming display"
```

---

### Task 7: 메인 윈도우 통합

**Files:**
- Modify: `digikey_scraper/_main_window_chat.py`
- Modify: `digikey_scraper/_main_window.py` (line 152 `_build_ui()` 호출 이후)

**Interfaces:**
- Consumes: `AiChatPanel` (Task 6), `Container.ai_chat` (Task 5)
- Produces: 우측 `QDockWidget` 도크, `toggle_ai_chat_dock()`, `_init_ai_chat_dock()` 메서드

- [ ] **Step 1: `_main_window_chat.py` 업데이트**

`_main_window_chat.py` 상단에 임포트 추가:
```python
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget
```

기존 `MainWindowChatMixin` 클래스 내부에 메서드 추가 (기존 메서드들 다음):
```python
def _init_ai_chat_dock(self) -> None:
    from ._ai_chat_panel import AiChatPanel

    self._ai_chat_panel = AiChatPanel(self.container.ai_chat, parent=self)
    self._ai_chat_dock = QDockWidget("AI 채팅", self)
    self._ai_chat_dock.setWidget(self._ai_chat_panel)
    self._ai_chat_dock.setAllowedAreas(
        Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea
    )
    self._ai_chat_dock.setMinimumWidth(280)
    self.addDockWidget(Qt.RightDockWidgetArea, self._ai_chat_dock)
    self._ai_chat_dock.hide()

def toggle_ai_chat_dock(self) -> None:
    if self._ai_chat_dock.isVisible():
        self._ai_chat_dock.hide()
    else:
        if hasattr(self, "results") and self.results:
            parts_context = [
                {
                    "name": getattr(r, "name", ""),
                    "price": getattr(r, "unit_price", ""),
                }
                for r in self.results
            ]
            self._ai_chat_panel.set_parts_context(parts_context)
        self._ai_chat_dock.show()
```

- [ ] **Step 2: `_main_window.py` 수정**

`_main_window.py` line 152 부근에서 `self._build_ui()` 다음 줄에 추가:

```python
        self._build_ui()
        self._init_ai_chat_dock()
        self._setup_part_completer()
```

같은 파일에서 `_add_ai_chat_menu_action` 메서드 추가 (클래스 내 임의 위치):
```python
def _add_ai_chat_menu_action(self) -> None:
    menu = self.menuBar().addMenu("AI")
    action = self._ai_chat_dock.toggleViewAction()
    action.setText("AI 채팅 패널")
    menu.addAction(action)
```

`_init_ai_chat_dock()` 호출 다음 줄에 추가:
```python
        self._init_ai_chat_dock()
        self._add_ai_chat_menu_action()
        self._setup_part_completer()
```

- [ ] **Step 3: 전체 테스트 실행**

```bash
QT_QPA_PLATFORM=offscreen pytest tests/ -v --tb=short
```

Expected: 모든 테스트 PASS

- [ ] **Step 4: 커밋**

```bash
git add digikey_scraper/_main_window_chat.py digikey_scraper/_main_window.py
git commit -m "feat: integrate AiChatPanel as dock widget in MainWindow with AI menu toggle"
```

---

### Task 8: 데이터시트 뷰어 AI Q&A 패널

**Files:**
- Modify: `digikey_scraper/datasheet_viewer.py`

**Interfaces:**
- Consumes: `AiChatService` (Task 4), `AiChatPanel` (Task 6)
- `DatasheetViewer.__init__` 시그니처 변경:
  ```python
  def __init__(self, url, title="", language="ko", parent=None, ai_chat_service=None)
  ```

- [ ] **Step 1: `datasheet_viewer.py` 임포트 블록 업데이트**

기존 `from PySide6.QtWidgets import (` 블록에 `QSplitter` 추가:
```python
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,        # 추가
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
```

- [ ] **Step 2: `DatasheetViewer.__init__` 시그니처 업데이트**

```python
def __init__(
    self,
    url: str,
    title: str = "",
    language: str = "ko",
    parent=None,
    ai_chat_service=None,
):
    super().__init__(parent)
    # ... 기존 코드 그대로 ...
    self._ai_chat_service = ai_chat_service
    # ... 마지막에 기존 코드:
    self._build_ui()
    self._load_pdf()
```

`self._doc = None` 등 기존 인스턴스 변수 설정 부분 바로 다음에 `self._ai_chat_service = ai_chat_service` 추가.

- [ ] **Step 3: `_build_ui()`에서 scroll area 래핑 변경**

`_build_ui()` 메서드에서 다음 블록 찾기:
```python
        vl.addWidget(toolbar)
        vl.addWidget(self._status)
        vl.addWidget(self._scroll, 1)
        vl.addWidget(self._viewer_status_lbl)
```

다음으로 교체:
```python
        vl.addWidget(toolbar)
        vl.addWidget(self._status)

        if self._ai_chat_service is not None:
            self._viewer_splitter = QSplitter(Qt.Vertical)
            self._viewer_splitter.addWidget(self._scroll)
            self._viewer_splitter.addWidget(self._build_ai_qa_panel())
            self._viewer_splitter.setSizes([700, 200])
            vl.addWidget(self._viewer_splitter, 1)
        else:
            vl.addWidget(self._scroll, 1)

        vl.addWidget(self._viewer_status_lbl)
```

- [ ] **Step 4: `_build_ai_qa_panel()` 메서드 추가**

`DatasheetViewer` 클래스에 메서드 추가 (`_build_ui` 다음):
```python
def _build_ai_qa_panel(self) -> "QWidget":
    from ._ai_chat_panel import AiChatPanel

    panel = AiChatPanel(self._ai_chat_service, parent=self)
    panel.set_parts_context([{"title": self._title}])

    if panel._session is not None:
        panel._session.context_mode = "datasheet"
        idx = panel._context_combo.findData("datasheet")
        if idx >= 0:
            panel._context_combo.setCurrentIndex(idx)

    panel._context_combo.hide()
    for child in panel.children():
        from PySide6.QtWidgets import QLabel
        if isinstance(child, QLabel) and child.text() == "컨텍스트:":
            child.hide()
            break

    return panel
```

- [ ] **Step 5: `DatasheetViewer` 호출부 업데이트**

`DatasheetViewer`를 생성하는 코드 찾기:
```bash
grep -rn "DatasheetViewer(" /home/lsy/pj_ws/digikey_scraper/
```

찾은 각 호출에 `ai_chat_service=self.container.ai_chat` 추가.
예시:
```python
# 변경 전:
viewer = DatasheetViewer(url=url, title=title, language=self.language, parent=self)
# 변경 후:
viewer = DatasheetViewer(
    url=url,
    title=title,
    language=self.language,
    parent=self,
    ai_chat_service=self.container.ai_chat,
)
```

- [ ] **Step 6: 전체 테스트 실행**

```bash
QT_QPA_PLATFORM=offscreen pytest tests/ -v --tb=short
```

Expected: 모든 테스트 PASS

- [ ] **Step 7: 커밋**

```bash
git add digikey_scraper/datasheet_viewer.py
git commit -m "feat: add Ollama Q&A panel to DatasheetViewer via QSplitter with datasheet context"
```

---

### Task 9: 통합 검증

**Files:**
- Read-only verification

- [ ] **Step 1: 전체 테스트 스위트 + 커버리지**

```bash
QT_QPA_PLATFORM=offscreen pytest --cov --cov-report=term-missing -v
```

Expected: 커버리지 ≥85% (layered packages 기준)

- [ ] **Step 2: ruff 린트**

```bash
ruff check digikey_scraper/domain digikey_scraper/application digikey_scraper/infrastructure digikey_scraper/container.py
```

Expected: 오류 없음

- [ ] **Step 3: mypy 타입 체크**

```bash
mypy
```

Expected: 오류 없음

- [ ] **Step 4: Ollama 연결 수동 검증**

Ollama 실행 중인 환경에서:
```bash
python -c "
from digikey_scraper.infrastructure.llm.ollama_text_generator import OllamaTextGenerator
gen = OllamaTextGenerator()
print('available:', gen.is_available())
chunks = []
result = gen.stream_chat([{'role': 'user', 'content': '안녕하세요. 간단히 소개해주세요.'}], on_chunk=chunks.append)
print('chunks:', len(chunks))
print('result preview:', result[:80])
"
```

Expected: `available: True`, `chunks > 0`, result 비어있지 않음

- [ ] **Step 5: 최종 커밋**

```bash
git add .
git commit -m "feat: complete local LLM chat — Ollama/Gemma4:e4b, main window dock, datasheet viewer panel"
```
