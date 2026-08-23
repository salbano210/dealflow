"""Build a Pydantic model dynamically from config/kpis.yaml.

This is the mechanism that lets you add/remove KPIs without touching code:
the extraction LLM is asked to return an object matching this generated
schema, and the same schema validates the response.

Each KPI becomes a nested object so the model can report *state* and
*evidence* alongside the value:

    {
      "estimated_revenue_usd": {
        "value": 45000000,
        "state": "known",            # known | inferred | unknown
        "confidence": 0.9,           # 0..1
        "evidence": "TTM revenue of $45M (page 4)."
      },
      ...
    }

Representing every field as this envelope (rather than a bare value) is
what makes the 'missing data != null' and provenance requirements real.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, create_model

from dealflow.config.schemas import KpiDefinition

FieldState = Literal["known", "inferred", "unknown"]

# Map KPI declared type -> the Python type used for the `value` field.
# Everything is Optional because `state == "unknown"` implies value is None.
_TYPE_MAP: dict[str, Any] = {
    "number": float | None,
    "percent": float | None,
    "boolean": bool | None,
    "string": str | None,
    "enum": str | None,  # enum values validated separately in normalize.py
}


class KpiValue(BaseModel):
    """The envelope returned for every KPI."""

    value: Any = None
    state: FieldState = "unknown"
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence: str | None = None


def build_extraction_model(kpis: list[KpiDefinition]) -> type[BaseModel]:
    """Create a Pydantic model whose fields are the KPI keys, each a KpiValue.

    Returns a subclass of BaseModel named 'ExtractionResult'.
    """
    fields: dict[str, Any] = {}
    for kpi in kpis:
        # Every field is a KpiValue envelope; optional at the top level so the
        # model may omit KPIs it has no information about (we backfill as unknown).
        fields[kpi.key] = (KpiValue | None, Field(default=None, description=kpi.description))

    model = create_model("ExtractionResult", __base__=BaseModel, **fields)
    return model


def describe_kpis_for_prompt(kpis: list[KpiDefinition]) -> str:
    """Human-readable KPI catalog injected into the extraction prompt."""
    lines: list[str] = []
    for k in kpis:
        bits = [f"- {k.key} ({k.type})"]
        if k.unit:
            bits.append(f"[unit: {k.unit}]")
        if k.enum_values:
            bits.append(f"[one of: {', '.join(k.enum_values)}]")
        bits.append(f": {k.description}")
        if k.extraction_hint:
            bits.append(f" Hint: {k.extraction_hint}")
        lines.append(" ".join(bits))
    return "\n".join(lines)
