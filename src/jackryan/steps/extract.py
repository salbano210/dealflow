"""Extraction step: unstructured source text -> structured KPI rows.

One LLM call per source. The response is validated against the dynamic
schema built from kpis.yaml, normalized/coerced, and written as
ExtractedAttribute rows (with provenance: source_id + llm_call_id).

This is the only place in Phase 2 that calls an LLM.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from jackryan.config import AppConfig
from jackryan.db.models import ExtractedAttribute, RawSource
from jackryan.llm import get_client
from jackryan.steps.normalize import normalize_value
from jackryan.steps.schema import build_extraction_model, describe_kpis_for_prompt

_SYSTEM_PROMPT = """You are a meticulous financial-data extraction assistant for an \
investment analyst. You read company source material and extract specific KPIs.

Rules you MUST follow:
- Only report a value when the source actually supports it.
- For each KPI, set `state` to:
    "known"    if the source states the value explicitly,
    "inferred" if you reasonably infer it from indirect evidence,
    "unknown"  if the source does not support any value (set value to null).
- Never guess. "unknown" is the correct answer when evidence is missing.
- Percentages must be decimals (38% -> 0.38). Revenue must be a number in USD.
- Put a short quote or paraphrase supporting each value in `evidence`.
- `confidence` is 0..1 reflecting how sure you are.
"""


def _step_for_kind(kind: str) -> str:
    return "extract_from_cim" if kind == "cim" else "extract_from_website"


def extract_from_source(
    session: Session, config: AppConfig, source: RawSource, company_id: int
) -> int:
    """Run extraction for a single RawSource. Returns count of KPI rows written."""
    if not source.allow_external_llm:
        # Compliance guardrail: never send flagged sources to an external LLM.
        return 0

    ExtractionModel = build_extraction_model(config.kpis)
    catalog = describe_kpis_for_prompt(config.kpis)

    user_prompt = (
        f"Extract the following KPIs from the source text below.\n\n"
        f"KPIs to extract:\n{catalog}\n\n"
        f"--- SOURCE TEXT START ---\n{source.text}\n--- SOURCE TEXT END ---"
    )

    client = get_client(config)
    resp = client.complete(
        step=_step_for_kind(source.kind),
        system=_SYSTEM_PROMPT,
        user=user_prompt,
        schema=ExtractionModel,
        company_id=company_id,
    )
    if resp.parsed is None:
        return 0

    written = 0
    for kpi in config.kpis:
        envelope = getattr(resp.parsed, kpi.key, None)
        norm = normalize_value(kpi, envelope)
        # Only persist rows that carry information; skip pure unknowns to
        # keep the EAV table lean (absence is itself treated as unknown).
        if norm.state == "unknown" and norm.value is None and norm.evidence is None:
            continue
        session.add(
            ExtractedAttribute(
                company_id=company_id,
                kpi_key=kpi.key,
                value_json={
                    "value": norm.value,
                    "state": norm.state,
                    "confidence": norm.confidence,
                    "evidence": norm.evidence,
                },
                confidence=norm.confidence,
                source_id=source.id,
                model=resp.model,
                llm_call_id=resp.llm_call_id,
            )
        )
        written += 1
    return written


def extract_company(session: Session, config: AppConfig, company_id: int) -> dict[str, int]:
    """Run extraction over every stored source for a company.

    Returns {source_kind: rows_written}.
    """
    sources = session.execute(
        select(RawSource).where(RawSource.company_id == company_id)
    ).scalars().all()

    results: dict[str, int] = {}
    for src in sources:
        count = extract_from_source(session, config, src, company_id)
        results[f"{src.kind}#{src.id}"] = count
    return results
