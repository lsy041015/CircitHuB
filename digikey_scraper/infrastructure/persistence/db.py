"""Optional database engine setup.

SQLAlchemy is an optional dependency. If it is not installed or DATABASE_URL is
not set, ``db_available()`` returns False and the app falls back to JSON.
"""

from __future__ import annotations

import os


def database_url() -> str | None:
    url = os.environ.get("DATABASE_URL", "").strip()
    return url or None


def db_available() -> bool:
    if database_url() is None:
        return False
    try:
        import sqlalchemy  # noqa: F401
    except Exception:
        return False
    return True


def make_engine():
    """Create a SQLAlchemy engine. Caller must ensure db_available() first."""
    from sqlalchemy import create_engine

    url = database_url()
    if url is None:
        raise RuntimeError("DATABASE_URL not set")
    return create_engine(url, future=True)
