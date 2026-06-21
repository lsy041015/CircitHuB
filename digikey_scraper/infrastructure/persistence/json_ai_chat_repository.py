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
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

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
        data["sessions"] = [s for s in data.get("sessions", []) if s.get("id") != session_id]
        self._write(data)
