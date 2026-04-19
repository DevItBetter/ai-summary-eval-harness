"""Structured analysis result rows."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class EffectResult:
    judge_name: str
    n: int
    observed_mean_difference: float
    ci_lower: float
    ci_upper: float
    standardized_effect_dz: float
    p_value: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CriterionEffectResult:
    judge_name: str
    criterion: str
    n: int
    observed_mean_difference: float
    ci_lower: float
    ci_upper: float
    standardized_effect_dz: float
    p_value: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LabelEffectResult:
    judge_name: str
    displayed_model: str
    n: int
    mean_centered_score_effect: float
    ci_lower: float
    ci_upper: float
    standardized_effect_d: float
    p_value: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ComparisonRow:
    effect_type: str
    target: str
    estimate: float
    ci_lower: float
    ci_upper: float
    standardized_effect: float
    p_value: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AgreementRow:
    judge_a: str
    judge_b: str
    shared_set_count: int
    mean_score_pearson_r: float
    mean_rank_spearman_rho: float
    top_rank_match_rate: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
