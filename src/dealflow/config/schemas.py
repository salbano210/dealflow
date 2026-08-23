"""Pydantic schemas for every YAML config file.

Editing these schemas is a code change. Editing the YAML that conforms to
them is not.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ------------------------------------------------------------------- thesis --

class HardFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    min_revenue_usd: float | None = None
    max_revenue_usd: float | None = None
    geography_allowlist: list[str] = Field(default_factory=list)
    business_model_blocklist: list[str] = Field(default_factory=list)
    founder_led_required: bool = False


class SoftCriteria(BaseModel):
    model_config = ConfigDict(extra="allow")  # free-form; consumed by prompts
    business_model_preferred: list[str] = Field(default_factory=list)
    founder_ownership: str | None = None
    min_growth_rate: float | None = None
    preferred_markets: list[str] = Field(default_factory=list)


class Thesis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    version: int
    hard_filters: HardFilters
    soft_criteria: SoftCriteria
    notes: str = ""
    max_cost_per_company_usd: float = 0.10


# ---------------------------------------------------------------------- kpis --

KpiType = Literal["number", "percent", "boolean", "string", "enum"]


class KpiDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str
    type: KpiType
    description: str
    required: bool = False
    unit: str | None = None
    enum_values: list[str] | None = None
    extraction_hint: str | None = None

    @model_validator(mode="after")
    def _enum_needs_values(self) -> "KpiDefinition":
        if self.type == "enum" and not self.enum_values:
            raise ValueError(f"KPI '{self.key}' is type=enum but has no enum_values.")
        return self


# ------------------------------------------------------------------- weights --

ScorerType = Literal["llm", "builtin.completeness", "builtin.threshold", "builtin.enum_match"]


class Dimension(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str
    weight: float = Field(gt=0.0, le=1.0)
    scorer: ScorerType
    inputs: list[str] = Field(default_factory=list)
    rubric: str | None = None
    config: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def _llm_needs_rubric(self) -> "Dimension":
        if self.scorer == "llm" and not self.rubric:
            raise ValueError(f"Dimension '{self.key}' uses scorer=llm but has no rubric.")
        return self


class Weights(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dimensions: list[Dimension]

    @field_validator("dimensions")
    @classmethod
    def _unique_keys(cls, v: list[Dimension]) -> list[Dimension]:
        keys = [d.key for d in v]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate dimension keys in weights.yaml.")
        return v

    @model_validator(mode="after")
    def _weights_sum_to_one(self) -> "Weights":
        total = sum(d.weight for d in self.dimensions)
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                f"Dimension weights must sum to 1.0 (got {total:.4f}). "
                f"Edit config/weights.yaml."
            )
        return self


# -------------------------------------------------------------------- models --

class StepModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str
    temp: float = 0.0
    max_tokens: int | None = None


class OpenRouterSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_url: str = "https://openrouter.ai/api/v1"
    timeout_seconds: int = 60
    max_retries: int = 3


class Models(BaseModel):
    model_config = ConfigDict(extra="forbid")
    steps: dict[str, StepModel]
    openrouter: OpenRouterSettings = Field(default_factory=OpenRouterSettings)

    def for_step(self, step: str) -> StepModel:
        """Look up the model for a given step, falling back to the default scorer."""
        if step in self.steps:
            return self.steps[step]
        if step.startswith("score_dimension_") and "score_dimension_default" in self.steps:
            return self.steps["score_dimension_default"]
        raise KeyError(f"No model configured for step '{step}' in config/models.yaml.")
