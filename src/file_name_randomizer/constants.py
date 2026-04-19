"""Shared constants across shuffle, runner, and analysis flows."""

from __future__ import annotations

RUBRIC_KEYS = (
    "accuracy",
    "completeness",
    "clarity",
    "faithfulness_to_source_prompt",
    "actionability",
)

SUMMARY_FILENAME_PATTERN = r"^(?P<prefix>.+)_summary__(?P<model>.+)\.md$"

ANALYSIS_FAMILIES = {
    "control_vs_deranged": "control_vs_deranged",
    "criterion_control_vs_deranged": "criterion_control_vs_deranged",
    "displayed_model_effects": "displayed_model_effects",
}
