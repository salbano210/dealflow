"""Screening engine: evaluate a company against the investment thesis.

Steps:
1. Hard filters (pure Python, no LLM) — instant reject if violated
2. Per-dimension scoring (LLM or builtin)
3. Weighted aggregate (0-100)
4. Output: pass/fail, score, rationale, evidence
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from dealflow.config import AppConfig
from dealflow.db.models import Screening, ScreeningDimension
from dealflow.llm import get_client
from dealflow.steps.attributes import current_attributes


@dataclass
class DimensionScore:
    key: str
    score: float  # 0-100
    weight: float
    rationale: str
    evidence_source_ids: list[int]
    llm_call_id: int | None = None


@dataclass
class ScreenResult:
    company_id: int
    total_score: float
    passed_hard_filters: bool
    hard_filter_failures: list[str]
    dimensions: list[DimensionScore]
    total_cost_usd: float
    screening_id: int


def apply_hard_filters(
    config: AppConfig, attrs: dict[str, Any]
) -> tuple[bool, list[str]]:
    """Check hard filters from thesis.yaml. Returns (passed, failures)."""
    failures: list[str] = []
    hf = config.thesis.hard_filters

    # Revenue range check
    rev = attrs.get("estimated_revenue_usd")
    rev_val = rev.value if rev and rev.state != "unknown" else None
    if rev_val is not None:
        if hf.min_revenue_usd and rev_val < hf.min_revenue_usd:
            failures.append(
                f"Revenue ${rev_val:,.0f} below minimum ${hf.min_revenue_usd:,.0f}"
            )
        if hf.max_revenue_usd and rev_val > hf.max_revenue_usd:
            failures.append(
                f"Revenue ${rev_val:,.0f} above maximum ${hf.max_revenue_usd:,.0f}"
            )
    else:
        if hf.min_revenue_usd or hf.max_revenue_usd:
            failures.append("Revenue unknown — cannot verify range filter")

    # Founder-led check
    founder = attrs.get("founder_led")
    founder_val = founder.value if founder and founder.state != "unknown" else None
    if hf.founder_led_required:
        if founder_val is not True:
            failures.append("Founder-led required but not confirmed")

    passed = len(failures) == 0
    return passed, failures


def score_dimension_llm(
    config: AppConfig,
    dim_config: dict,
    attrs: dict[str, Any],
    company_id: int,
) -> DimensionScore:
    """Score one dimension using an LLM."""
    client = get_client(config)
    step = f"score_dimension_{dim_config['key']}"

    # Build input summary
    inputs_summary = []
    evidence_ids = []
    for inp in dim_config.get("inputs", []):
        if inp in attrs:
            a = attrs[inp]
            inputs_summary.append(f"{inp}: {a.value} (state={a.state})")
            if a.source_id:
                evidence_ids.append(a.source_id)
        else:
            inputs_summary.append(f"{inp}: unknown")

    system_prompt = f"""You are an investment analyst scoring a company on one dimension.
Score 0-100 based on the rubric below. Be strict — unknown data should lower the score.

Rubric:
{dim_config['rubric']}

Thesis guidance:
{config.thesis.notes}
"""

    user_prompt = f"""Company data for dimension '{dim_config['key']}':

{chr(10).join(inputs_summary)}

Score this dimension 0-100. Respond with JSON:
{{
  "score": <integer 0-100>,
  "rationale": "<2-3 sentence explanation referencing the evidence>"
}}"""

    from pydantic import BaseModel

    class ScoreResponse(BaseModel):
        score: int
        rationale: str

    resp = client.complete(
        step=step,
        system=system_prompt,
        user=user_prompt,
        schema=ScoreResponse,
        company_id=company_id,
    )

    parsed = resp.parsed
    return DimensionScore(
        key=dim_config["key"],
        score=max(0, min(100, parsed.score)),
        weight=dim_config["weight"],
        rationale=parsed.rationale,
        evidence_source_ids=evidence_ids,
        llm_call_id=resp.llm_call_id,
    )


def score_dimension_builtin(
    config: AppConfig,
    dim_config: dict,
    attrs: dict[str, Any],
) -> DimensionScore:
    """Score one dimension using a deterministic builtin scorer."""
    scorer = dim_config["scorer"]
    cfg = dim_config.get("config", {})

    if scorer == "builtin.threshold":
        field = cfg["field"]
        if field not in attrs or attrs[field].state == "unknown":
            score = 0.0
        else:
            val = float(attrs[field].value)
            min_v = float(cfg["min"])
            target_v = float(cfg["target"])
            invert = cfg.get("invert", False)

            if invert:
                # Lower is better (e.g., employee count)
                if val <= min_v:
                    score = 100.0
                elif val >= target_v:
                    score = 0.0
                else:
                    score = 100.0 * (target_v - val) / (target_v - min_v)
            else:
                # Higher is better (e.g., revenue)
                if val >= target_v:
                    score = 100.0
                elif val <= min_v:
                    score = 0.0
                else:
                    score = 100.0 * (val - min_v) / (target_v - min_v)

        return DimensionScore(
            key=dim_config["key"],
            score=score,
            weight=dim_config["weight"],
            rationale=f"Threshold scorer: {field}={attrs.get(field, 'unknown')}",
            evidence_source_ids=[attrs[field].source_id] if field in attrs else [],
        )

    elif scorer == "builtin.completeness":
        required = config.required_kpi_keys()
        if not required:
            score = 100.0
        else:
            known = sum(
                1 for k in required
                if k in attrs and attrs[k].state == "known"
            )
            inferred = sum(
                1 for k in required
                if k in attrs and attrs[k].state == "inferred"
            )
            count_inferred = cfg.get("count_inferred_as_half", True)
            effective = known + (inferred * 0.5 if count_inferred else 0)
            score = 100.0 * effective / len(required)

        return DimensionScore(
            key=dim_config["key"],
            score=score,
            weight=dim_config["weight"],
            rationale=f"Completeness: {known}/{len(required)} required KPIs known",
            evidence_source_ids=[],
        )

    else:
        raise ValueError(f"Unknown builtin scorer: {scorer}")


def screen_company(
    session: Session, config: AppConfig, company_id: int
) -> ScreenResult:
    """Run full screening pipeline for one company."""
    from dealflow.db.models import Company

    company = session.get(Company, company_id)
    if company is None:
        raise ValueError(f"Company {company_id} not found")

    # Get current merged attributes
    attrs = current_attributes(session, company_id)

    # Step 1: Hard filters
    passed, failures = apply_hard_filters(config, attrs)

    # Step 2: Score dimensions (only if hard filters passed)
    dimensions: list[DimensionScore] = []
    total_cost = 0.0

    if passed:
        for dim in config.weights.dimensions:
            if dim.scorer == "llm":
                score = score_dimension_llm(config, dim.model_dump(), attrs, company_id)
            else:
                score = score_dimension_builtin(config, dim.model_dump(), attrs)
            dimensions.append(score)

            # Track cost (from llm_calls if applicable)
            if score.llm_call_id:
                from dealflow.db.models import LlmCall
                call = session.get(LlmCall, score.llm_call_id)
                if call and call.cost_usd:
                    total_cost += call.cost_usd

    # Step 3: Weighted aggregate
    if dimensions:
        total_score = sum(d.score * d.weight for d in dimensions)
    else:
        total_score = 0.0

    # Step 4: Persist
    screening = Screening(
        company_id=company_id,
        thesis_version=config.thesis.version,
        total_score=total_score,
        passed_hard_filters=passed,
        hard_filter_failures=failures,
        model_config_snapshot=config.models.model_dump(),
        total_cost_usd=total_cost,
    )
    session.add(screening)
    session.flush()

    for dim in dimensions:
        session.add(
            ScreeningDimension(
                screening_id=screening.id,
                dim_key=dim.key,
                score=dim.score,
                max_score=100.0,
                weight=dim.weight,
                rationale=dim.rationale,
                evidence_source_ids=dim.evidence_source_ids,
                llm_call_id=dim.llm_call_id,
            )
        )

    return ScreenResult(
        company_id=company_id,
        total_score=total_score,
        passed_hard_filters=passed,
        hard_filter_failures=failures,
        dimensions=dimensions,
        total_cost_usd=total_cost,
        screening_id=screening.id,
    )