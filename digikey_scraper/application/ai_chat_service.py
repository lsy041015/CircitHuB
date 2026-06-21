from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import TYPE_CHECKING

from ..domain.chat_models import AiChatMessage, AiChatSession

if TYPE_CHECKING:
    from ..domain.ports import AiChatRepository
    from ..infrastructure.llm.ollama_text_generator import OllamaTextGenerator
    from .rag_service import RagService

MAX_HISTORY_MESSAGES = 10


class AiChatService:
    def __init__(
        self,
        llm: OllamaTextGenerator,
        repo: AiChatRepository,
        rag_service: RagService | None = None,
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
                context = "\n".join(f"[{c.chunk.id}] {c.chunk.text}" for c in chunks)
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
