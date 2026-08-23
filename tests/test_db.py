"""Smoke test: init_db creates all tables."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import inspect

from dealflow.db import init_db
from dealflow.db.session import get_engine


def test_init_creates_all_tables(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DEALFLOW_DB_PATH", str(tmp_path / "test.sqlite"))
    # Reset module-level engine cache so the new env var takes effect.
    import dealflow.db.session as s
    s._engine = None
    s._SessionFactory = None

    init_db()
    tables = set(inspect(get_engine()).get_table_names())
    assert {
        "companies", "raw_sources", "extracted_attributes",
        "screenings", "screening_dimensions", "research_questions",
        "outreach_drafts", "decisions", "llm_calls",
    } <= tables
