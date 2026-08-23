"""Read the 'current' KPI picture for a company from the EAV history.

We never overwrite ExtractedAttribute rows. Each extraction appends new
rows. The current value for a (company, kpi_key) pair is chosen by:

    1. highest trust_tier of the originating source (cim > website > news)
    2. then most recent extracted_at
    3. 'known' beats 'inferred' beats 'unknown' at the same tier+recency

A conflict is recorded when two DIFFERENT non-unknown values exist at the
same top trust tier -- surfaced so the analyst (and Airtable) can flag it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from dealflow.db.models import ExtractedAttribute, RawSource

_STATE_RANK = {"known": 2, "inferred": 1, "unknown": 0}


@dataclass
class CurrentAttribute:
    kpi_key: str
    value: Any
    state: str
    confidence: float | None
    evidence: str | None
    source_id: int | None
    trust_tier: int
    conflict: bool


def current_attributes(session: Session, company_id: int) -> dict[str, CurrentAttribute]:
    """Return {kpi_key: CurrentAttribute} representing the merged picture."""
    rows = session.execute(
        select(ExtractedAttribute).where(ExtractedAttribute.company_id == company_id)
    ).scalars().all()

    # Preload trust tiers for the sources referenced.
    source_ids = {r.source_id for r in rows if r.source_id is not None}
    tiers: dict[int, int] = {}
    if source_ids:
        for src in session.execute(
            select(RawSource).where(RawSource.id.in_(source_ids))
        ).scalars().all():
            tiers[src.id] = src.trust_tier

    grouped: dict[str, list[ExtractedAttribute]] = {}
    for r in rows:
        grouped.setdefault(r.kpi_key, []).append(r)

    result: dict[str, CurrentAttribute] = {}
    for key, attrs in grouped.items():
        def sort_key(a: ExtractedAttribute):
            tier = tiers.get(a.source_id, 0) if a.source_id else 0
            state = (a.value_json or {}).get("state", "unknown")
            return (tier, a.extracted_at, _STATE_RANK.get(state, 0))

        attrs_sorted = sorted(attrs, key=sort_key, reverse=True)
        winner = attrs_sorted[0]
        wtier = tiers.get(winner.source_id, 0) if winner.source_id else 0
        wval = (winner.value_json or {}).get("value")
        wstate = (winner.value_json or {}).get("state", "unknown")

        # Conflict detection: any other row at the same top tier with a
        # different non-unknown value.
        conflict = False
        for other in attrs_sorted[1:]:
            otier = tiers.get(other.source_id, 0) if other.source_id else 0
            oval = (other.value_json or {}).get("value")
            ostate = (other.value_json or {}).get("state", "unknown")
            if otier == wtier and ostate != "unknown" and wstate != "unknown" and oval != wval:
                conflict = True
                break

        result[key] = CurrentAttribute(
            kpi_key=key,
            value=wval,
            state=wstate,
            confidence=(winner.value_json or {}).get("confidence"),
            evidence=(winner.value_json or {}).get("evidence"),
            source_id=winner.source_id,
            trust_tier=wtier,
            conflict=conflict,
        )
    return result
