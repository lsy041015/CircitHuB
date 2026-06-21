"""Centralized settings persistence.

Previously the file read/write was inlined in ``MainWindow._load_settings`` /
``MainWindow.save_settings`` (the widget->dict mapping stays in the GUI as a
presentation concern; only the persistence I/O is centralized here).
"""

from __future__ import annotations

import json
from pathlib import Path

from .._helpers import SETTINGS_FILE, runtime_path


class FileSettingsStore:
    """SettingsStore backed by a JSON file under the app data dir."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or runtime_path(SETTINGS_FILE)

    def load(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def save(self, data: dict) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
