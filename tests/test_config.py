"""Smoke tests for config loading & cross-validation."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from jackryan.config import load_all
from jackryan.config.loader import ConfigError


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_shipped_config_is_valid() -> None:
    cfg = load_all(REPO_ROOT / "config")
    assert cfg.thesis.name
    assert cfg.kpis
    assert cfg.weights.dimensions
    # weights sum to 1.0 exactly (validated in schema)
    assert abs(sum(d.weight for d in cfg.weights.dimensions) - 1.0) < 1e-6


def test_dimension_input_must_reference_real_kpi(tmp_path: Path) -> None:
    # Copy shipped config, then poison weights.yaml with a bad input.
    cdir = tmp_path / "config"
    cdir.mkdir()
    for name in ("thesis.yaml", "kpis.yaml", "weights.yaml", "models.yaml"):
        (cdir / name).write_text((REPO_ROOT / "config" / name).read_text())

    weights = yaml.safe_load((cdir / "weights.yaml").read_text())
    weights["dimensions"][0]["inputs"] = ["not_a_real_kpi"]
    (cdir / "weights.yaml").write_text(yaml.safe_dump(weights))

    with pytest.raises(ConfigError, match="unknown KPI"):
        load_all(cdir)


def test_weights_must_sum_to_one(tmp_path: Path) -> None:
    cdir = tmp_path / "config"
    cdir.mkdir()
    for name in ("thesis.yaml", "kpis.yaml", "weights.yaml", "models.yaml"):
        (cdir / name).write_text((REPO_ROOT / "config" / name).read_text())

    weights = yaml.safe_load((cdir / "weights.yaml").read_text())
    weights["dimensions"][0]["weight"] = 0.99  # break the sum
    (cdir / "weights.yaml").write_text(yaml.safe_dump(weights))

    with pytest.raises(ConfigError, match="sum to 1.0"):
        load_all(cdir)
