"""Test the EAV merge logic in steps/attributes.current_attributes.

Trust tier wins; conflicts flagged; history preserved.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dealflow.steps.attributes import current_attributes


@pytest.fixture()
def session(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DEALFLOW_DB_PATH", str(tmp_path / "merge.sqlite"))
    import dealflow.db.session as s
    s._engine = None
    s._SessionFactory = None
    from dealflow.db import init_db
    init_db()
    with s.get_session() as sess:
        yield sess


def _add_source(sess, company_id, kind, tier):
    from dealflow.db.models import RawSource
    src = RawSource(company_id=company_id, kind=kind, trust_tier=tier, text_blob="x")
    sess.add(src)
    sess.flush()
    return src.id


def _add_attr(sess, company_id, key, value, state, source_id):
    from dealflow.db.models import ExtractedAttribute
    sess.add(ExtractedAttribute(
        company_id=company_id, kpi_key=key,
        value_json={"value": value, "state": state, "confidence": 0.9, "evidence": "e"},
        source_id=source_id,
    ))
    sess.flush()


def test_higher_trust_tier_wins(session):
    from dealflow.db.models import Company
    c = Company(name="Acme")
    session.add(c)
    session.flush()

    web = _add_source(session, c.id, "website", 2)
    cim = _add_source(session, c.id, "cim", 3)
    _add_attr(session, c.id, "estimated_revenue_usd", 40_000_000, "known", web)
    _add_attr(session, c.id, "estimated_revenue_usd", 45_000_000, "known", cim)

    attrs = current_attributes(session, c.id)
    assert attrs["estimated_revenue_usd"].value == 45_000_000
    assert attrs["estimated_revenue_usd"].trust_tier == 3
    # different values across tiers is NOT a same-tier conflict
    assert attrs["estimated_revenue_usd"].conflict is False


def test_same_tier_disagreement_flags_conflict(session):
    from dealflow.db.models import Company
    c = Company(name="Beta")
    session.add(c)
    session.flush()

    n1 = _add_source(session, c.id, "news", 1)
    n2 = _add_source(session, c.id, "news", 1)
    _add_attr(session, c.id, "growth_rate_yoy", 0.30, "known", n1)
    _add_attr(session, c.id, "growth_rate_yoy", 0.45, "known", n2)

    attrs = current_attributes(session, c.id)
    assert attrs["growth_rate_yoy"].conflict is True
