"""Tests for the deterministic parts of extraction: schema build,
value normalization, and EAV merge logic. No LLM/network involved.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dealflow.config.schemas import KpiDefinition
from dealflow.steps.normalize import normalize_value
from dealflow.steps.schema import KpiValue, build_extraction_model

REPO_ROOT = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------- schema ------

def test_build_extraction_model_has_all_kpi_fields() -> None:
    kpis = [
        KpiDefinition(key="rev", type="number", description="revenue"),
        KpiDefinition(key="founder", type="boolean", description="founder led"),
    ]
    Model = build_extraction_model(kpis)
    inst = Model.model_validate(
        {"rev": {"value": 45.0, "state": "known"}, "founder": {"value": True, "state": "known"}}
    )
    assert inst.rev.value == 45.0
    assert inst.founder.value is True


def test_build_extraction_model_allows_omitted_fields() -> None:
    kpis = [KpiDefinition(key="rev", type="number", description="revenue")]
    Model = build_extraction_model(kpis)
    inst = Model.model_validate({})
    assert inst.rev is None


# ------------------------------------------------------------ normalize ------

def _kpi(**kw) -> KpiDefinition:
    return KpiDefinition(**kw)


def test_normalize_number_from_messy_string() -> None:
    kpi = _kpi(key="rev", type="number", description="revenue")
    env = KpiValue(value="$45,000,000", state="known", confidence=0.9)
    out = normalize_value(kpi, env)
    assert out.value == 45000000.0
    assert out.state == "known"


def test_normalize_percent_passthrough_decimal() -> None:
    kpi = _kpi(key="g", type="percent", description="growth")
    env = KpiValue(value=0.38, state="known")
    out = normalize_value(kpi, env)
    assert out.value == 0.38


def test_normalize_boolean_from_string() -> None:
    kpi = _kpi(key="f", type="boolean", description="founder")
    assert normalize_value(kpi, KpiValue(value="yes", state="known")).value is True
    assert normalize_value(kpi, KpiValue(value="No", state="known")).value is False


def test_normalize_enum_rejects_out_of_set() -> None:
    kpi = _kpi(key="bm", type="enum", description="model", enum_values=["recurring_saas", "other"])
    good = normalize_value(kpi, KpiValue(value="recurring_saas", state="known"))
    assert good.value == "recurring_saas"
    bad = normalize_value(kpi, KpiValue(value="carrier_pigeon", state="known"))
    assert bad.state == "unknown"
    assert bad.value is None


def test_normalize_enum_case_insensitive() -> None:
    kpi = _kpi(key="geo", type="enum", description="geo", enum_values=["US", "CA"])
    out = normalize_value(kpi, KpiValue(value="us", state="known"))
    assert out.value == "US"


def test_normalize_unknown_stays_unknown() -> None:
    kpi = _kpi(key="rev", type="number", description="revenue")
    out = normalize_value(kpi, KpiValue(value=None, state="unknown"))
    assert out.state == "unknown"
    assert out.value is None


def test_normalize_none_envelope() -> None:
    kpi = _kpi(key="rev", type="number", description="revenue")
    out = normalize_value(kpi, None)
    assert out.state == "unknown"
