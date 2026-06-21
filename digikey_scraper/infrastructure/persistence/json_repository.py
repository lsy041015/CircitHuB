"""Default ResultRepository backed by JSON files under the app data dir.

Used when no database is configured. Stores one JSON file per search in
``<data_dir>/search_history/`` so the existing zero-config deployment keeps
working with no external services (graceful degradation, P0 acceptance).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from ..._helpers import runtime_path
from ...domain.models import ProductResult
from .serialization import result_to_dict

HISTORY_DIR = "search_history"


class JsonResultRepository:
    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or runtime_path(HISTORY_DIR)

    def save_search(
        self, queries: list[str], results: list[ProductResult], language: str = "ko"
    ) -> int | None:
        ts = int(time.time() * 1000)
        record = {
            "id": ts,
            "created_at": ts,
            "language": language,
            "queries": list(queries),
            "results": [result_to_dict(r) for r in results],
        }
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            path = self.directory / f"{ts}.json"
            path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
            return ts
        except Exception:
            return None

    def recent_searches(self, limit: int = 20) -> list[dict]:
        if not self.directory.exists():
            return []
        files = sorted(self.directory.glob("*.json"), reverse=True)[:limit]
        out: list[dict] = []
        for f in files:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                out.append(
                    {
                        "id": data.get("id"),
                        "created_at": data.get("created_at"),
                        "language": data.get("language", "ko"),
                        "query_count": len(data.get("queries", [])),
                        "queries": data.get("queries", []),
                    }
                )
            except Exception:
                continue
        return out
