"""Postgres ResultRepository (optional).

Schema is created lazily via SQLAlchemy Core to avoid an ORM/Alembic hard
dependency for P0. When SQLAlchemy/Postgres are unavailable the DI container
selects JsonResultRepository instead.
"""

from __future__ import annotations

import json
import time
from typing import Any

from ...domain.models import ProductResult
from .serialization import result_to_dict


class PgResultRepository:
    def __init__(self, engine: Any) -> None:
        self._engine = engine
        self._md: Any = None
        self._searches: Any = None
        self._build_schema()

    def _build_schema(self) -> None:
        from sqlalchemy import (
            Column,
            DateTime,
            Integer,
            MetaData,
            String,
            Table,
            Text,
            func,
        )

        self._md = MetaData()
        self._searches = Table(
            "search",
            self._md,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("created_at", DateTime, server_default=func.now()),
            Column("language", String(8), default="ko"),
            Column("query_count", Integer, default=0),
            Column("queries", Text),
            Column("results", Text),
        )
        self._md.create_all(self._engine)

    def save_search(
        self, queries: list[str], results: list[ProductResult], language: str = "ko"
    ) -> int | None:
        from sqlalchemy import insert

        stmt = insert(self._searches).values(
            language=language,
            query_count=len(queries),
            queries=json.dumps(list(queries), ensure_ascii=False),
            results=json.dumps([result_to_dict(r) for r in results], ensure_ascii=False),
        )
        try:
            with self._engine.begin() as conn:
                res = conn.execute(stmt)
                pk = res.inserted_primary_key
                return int(pk[0]) if pk else None
        except Exception:
            return None

    def recent_searches(self, limit: int = 20) -> list[dict]:
        from sqlalchemy import select

        stmt = (
            select(
                self._searches.c.id,
                self._searches.c.created_at,
                self._searches.c.language,
                self._searches.c.query_count,
                self._searches.c.queries,
            )
            .order_by(self._searches.c.id.desc())
            .limit(limit)
        )
        out: list[dict] = []
        try:
            with self._engine.connect() as conn:
                for row in conn.execute(stmt):
                    created = row.created_at
                    out.append(
                        {
                            "id": row.id,
                            "created_at": int(created.timestamp() * 1000)
                            if created
                            else int(time.time() * 1000),
                            "language": row.language,
                            "query_count": row.query_count,
                            "queries": json.loads(row.queries) if row.queries else [],
                        }
                    )
        except Exception:
            return []
        return out
