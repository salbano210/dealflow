"""Load and cross-validate all YAML config files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import ValidationError

from jackryan.config.schemas import (
    Dimension,
    KpiDefinition,
    Models,
    Thesis,
    Weights,
)


class ConfigError(RuntimeError):
    """Raised when a config file is missing or fails validation."""


def _repo_root() -> Path:
    # src/jackryan/config/loader.py  ->  repo root is three parents up
    return Path(__file__).resolve().parents[3]


def _config_dir() -> Path:
    return _repo_root() / "config"


def _read_yaml(path: Path) -> object:
    if not path.exists():
        raise ConfigError(f"Missing config file: {path}")
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in {path}: {e}") from e


@dataclass(frozen=True)
class AppConfig:
    """The fully-loaded, cross-validated application config."""

    thesis: Thesis
    kpis: list[KpiDefinition]
    weights: Weights
    models: Models

    def kpi_keys(self) -> set[str]:
        return {k.key for k in self.kpis}

    def required_kpi_keys(self) -> set[str]:
        return {k.key for k in self.kpis if k.required}


def load_all(config_dir: Path | None = None) -> AppConfig:
    """Load thesis, kpis, weights, and models. Cross-validate consistency.

    Raises ConfigError with a human-readable message on any failure.
    """
    cdir = config_dir or _config_dir()

    def _validate(model_cls, path: Path, data: object):
        try:
            return model_cls.model_validate(data)
        except ValidationError as e:
            raise ConfigError(f"Validation failed for {path.name}:\n{e}") from e

    thesis = _validate(Thesis, cdir / "thesis.yaml", _read_yaml(cdir / "thesis.yaml"))

    kpi_raw = _read_yaml(cdir / "kpis.yaml")
    if not isinstance(kpi_raw, list):
        raise ConfigError("kpis.yaml must be a YAML list.")
    kpis = [_validate(KpiDefinition, cdir / "kpis.yaml", item) for item in kpi_raw]

    # Enforce unique KPI keys
    keys = [k.key for k in kpis]
    if len(keys) != len(set(keys)):
        raise ConfigError("Duplicate KPI keys in kpis.yaml.")

    weights = _validate(Weights, cdir / "weights.yaml", _read_yaml(cdir / "weights.yaml"))
    models = _validate(Models, cdir / "models.yaml", _read_yaml(cdir / "models.yaml"))

    _cross_validate(kpis, weights, models)

    return AppConfig(thesis=thesis, kpis=kpis, weights=weights, models=models)


def _cross_validate(
    kpis: list[KpiDefinition], weights: Weights, models: Models
) -> None:
    """Checks that span multiple config files."""
    kpi_keys = {k.key for k in kpis}

    # Every dimension input must reference a real KPI.
    for dim in weights.dimensions:
        for inp in dim.inputs:
            if inp not in kpi_keys:
                raise ConfigError(
                    f"Dimension '{dim.key}' references unknown KPI '{inp}'. "
                    f"Add it to kpis.yaml or remove it from weights.yaml."
                )

    # Every LLM-scored dimension must have a model routed for it.
    for dim in weights.dimensions:
        if dim.scorer == "llm":
            step = f"score_dimension_{dim.key}"
            try:
                models.for_step(step)
            except KeyError as e:
                raise ConfigError(
                    f"No model routed for dimension '{dim.key}'. "
                    f"Add '{step}' or 'score_dimension_default' to models.yaml."
                ) from e

    _validate_builtin_configs(weights, kpis)


def _validate_builtin_configs(weights: Weights, kpis: list[KpiDefinition]) -> None:
    """Validate the `config` block of each builtin scorer."""
    kpi_by_key = {k.key: k for k in kpis}

    for dim in weights.dimensions:
        if dim.scorer == "builtin.threshold":
            cfg = dim.config
            field = cfg.get("field")
            if not field or field not in kpi_by_key:
                raise ConfigError(
                    f"builtin.threshold dimension '{dim.key}' needs config.field "
                    f"referencing a KPI key."
                )
            if "min" not in cfg or "target" not in cfg:
                raise ConfigError(
                    f"builtin.threshold dimension '{dim.key}' needs config.min and config.target."
                )
        elif dim.scorer == "builtin.completeness":
            # No required config; defaults handled by scorer.
            pass
        elif dim.scorer == "builtin.enum_match":
            if "field" not in dim.config or "allowed" not in dim.config:
                raise ConfigError(
                    f"builtin.enum_match dimension '{dim.key}' needs config.field and config.allowed."
                )


__all__ = ["AppConfig", "ConfigError", "load_all"]
