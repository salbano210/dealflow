"""Coerce and validate raw LLM-extracted KPI values against kpis.yaml.

The dynamic schema (steps/schema.py) guarantees the *shape* of the
response. This module enforces the *semantics*:

- enum values must be in the allowed set (else downgraded to unknown)
- percent/number values are coerced to float
- boolean values are coerced from common string forms
- a value with state != 'unknown' but value is None is downgraded to unknown

Nothing here calls an LLM. It's pure, deterministic, and unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dealflow.config.schemas import KpiDefinition


@dataclass
class NormalizedValue:
    value: Any
    state: str            # known | inferred | unknown
    confidence: float | None
    evidence: str | None


_TRUE = {"true", "yes", "y", "1"}
_FALSE = {"false", "no", "n", "0"}


def _coerce_number(raw: Any) -> float | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        cleaned = raw.replace(",", "").replace("$", "").replace("%", "").strip()
        try:
            v = float(cleaned)
        except ValueError:
            return None
        # If the source expressed a percent as e.g. "38", callers using
        # percent KPIs may want 0.38. We do NOT guess here -- the extraction
        # prompt asks for decimals. Leave as-is; the prompt owns that contract.
        return v
    return None


def _coerce_boolean(raw: Any) -> bool | None:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        low = raw.strip().lower()
        if low in _TRUE:
            return True
        if low in _FALSE:
            return False
    return None


def normalize_value(kpi: KpiDefinition, raw_envelope: Any) -> NormalizedValue:
    """Normalize one KPI envelope. `raw_envelope` is a KpiValue-like object
    (or None if the model omitted the field entirely).
    """
    if raw_envelope is None:
        return NormalizedValue(value=None, state="unknown", confidence=None, evidence=None)

    value = getattr(raw_envelope, "value", None)
    state = getattr(raw_envelope, "state", "unknown") or "unknown"
    confidence = getattr(raw_envelope, "confidence", None)
    evidence = getattr(raw_envelope, "evidence", None)

    if state == "unknown" or value is None:
        return NormalizedValue(value=None, state="unknown", confidence=confidence, evidence=evidence)

    coerced: Any = value
    if kpi.type in ("number", "percent"):
        coerced = _coerce_number(value)
    elif kpi.type == "boolean":
        coerced = _coerce_boolean(value)
    elif kpi.type == "enum":
        text = str(value).strip()
        allowed = kpi.enum_values or []
        match = next((a for a in allowed if a.lower() == text.lower()), None)
        coerced = match  # None if not in the allowed set
    elif kpi.type == "string":
        coerced = str(value).strip() or None

    if coerced is None:
        # Coercion failed -> we can't trust the value; mark unknown but keep evidence.
        return NormalizedValue(value=None, state="unknown", confidence=confidence, evidence=evidence)

    # Preserve inferred vs known as reported by the model.
    final_state = "inferred" if state == "inferred" else "known"
    return NormalizedValue(value=coerced, state=final_state, confidence=confidence, evidence=evidence)
