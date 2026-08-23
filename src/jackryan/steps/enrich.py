"""Enrichment orchestration: fetch sources and persist them as raw_sources.

No LLM here. This step only gathers evidence. Extraction (steps/extract.py)
turns that evidence into KPIs.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from jackryan.db.models import Company, RawSource
from jackryan.sources.base import SourceDocument
from jackryan.sources.cim import parse_cim
from jackryan.sources.website import fetch_website


def store_source(session: Session, company_id: int, doc: SourceDocument) -> RawSource:
    """Persist a SourceDocument as a RawSource row."""
    row = RawSource(
        company_id=company_id,
        kind=doc.kind,
        trust_tier=doc.trust_tier,
        url_or_path=doc.url_or_path,
        text_blob=doc.text,
        allow_external_llm=doc.allow_external_llm,
    )
    session.add(row)
    session.flush()
    return row


def enrich_from_website(session: Session, company: Company) -> RawSource | None:
    """Fetch the company website (if set) and store it. Returns the row or None."""
    if not company.website:
        return None
    doc = fetch_website(company.website)
    if not doc.is_usable():
        return None
    return store_source(session, company.id, doc)


def enrich_from_cim(
    session: Session, company_id: int, path: str, *, allow_external_llm: bool = True
) -> RawSource:
    """Parse a CIM PDF and store it as a raw source."""
    doc = parse_cim(path, allow_external_llm=allow_external_llm)
    return store_source(session, company_id, doc)
