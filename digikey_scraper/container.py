"""Composition root: wires concrete adapters to ports.

GUI/headless entry points build a Container and inject it, so swapping
implementations (e.g. a different supplier or repository) touches only this
file. Selecting Postgres vs JSON degrades gracefully based on availability.
"""

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
        # Any DB setup failure -> fall back to local JSON (no service required).
        pass
    return JsonResultRepository()


def build_container() -> Container:
    llm = OllamaTextGenerator(model="gemma4:e4b")
    repo = JsonAiChatRepository()
    return Container(
        results=_build_result_repository(),
        settings=FileSettingsStore(),
        ai_chat=AiChatService(llm=llm, repo=repo),
    )
