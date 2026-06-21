from __future__ import annotations

import json
from pathlib import Path

from ._helpers import AUTO_SAVE_DIR, runtime_path


class ChatPersistenceStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or self._resolve_base_dir()

    def messages_path(self) -> Path:
        return self.base_dir / "team_chat_messages.json"

    def rooms_path(self) -> Path:
        return self.base_dir / "team_chat_rooms.json"

    def load_messages(self) -> dict:
        return self._load_dict(self.messages_path())

    def save_messages(self, payload: dict) -> None:
        self._write_json(self.messages_path(), payload)

    def load_room_state(self) -> dict:
        return self._load_dict(self.rooms_path())

    def save_room_state(
        self,
        channels: list[dict],
        dms: list[dict],
        muted_by_channel: dict[str, bool],
    ) -> None:
        self._write_json(
            self.rooms_path(),
            {"channels": channels, "dms": dms, "muted": muted_by_channel},
        )

    @staticmethod
    def _load_dict(path: Path) -> dict:
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    @staticmethod
    def _write_json(path: Path, payload: dict) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    @staticmethod
    def _resolve_base_dir() -> Path:
        try:
            base_dir = runtime_path(AUTO_SAVE_DIR)
        except Exception:
            base_dir = Path.cwd()
        base_dir.mkdir(parents=True, exist_ok=True)
        return base_dir
