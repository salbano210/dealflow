"""SQLite engine + session factory."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from jackryan.db.models import Base


def _db_path() -> Path:
    raw = os.environ.get("JACKRYAN_DB_PATH", "data/jackryan.sqlite")
    p = Path(raw)
    if not p.is_absolute():
        # Resolve relative to repo root (three parents up from this file).
        p = Path(__file__).resolve().parents[3] / p
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


_engine: Engine | None = None
_SessionFactory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine, _SessionFactory
    if _engine is None:
        _engine = create_engine(f"sqlite:///{_db_path()}", future=True)
        _SessionFactory = sessionmaker(_engine, expire_on_commit=False, future=True)
    return _engine


@contextmanager
def get_session() -> Iterator[Session]:
    get_engine()  # ensure factory built
    assert _SessionFactory is not None
    session = _SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> Path:
    """Create all tables. Idempotent."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    return _db_path()
