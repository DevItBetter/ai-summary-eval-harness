"""Output rendering for analysis artifacts."""

from __future__ import annotations

import csv
import json
import math
import shutil
from pathlib import Path
from typing import Any

from ..types import JoinedRow


def prepare_output_dir(path: Path, force: bool) -> None:
    if path.exists():
        if not force:
            raise ValueError(f"Output directory already exists: {path}. Re-run with --force.")
        for child in sorted(path.iterdir(), reverse=True):
            if child.is_file() or child.is_symlink():
                child.unlink()
            else:
                shutil.rmtree(child)
    path.mkdir(parents=True, exist_ok=True)


def write_flat_csv(rows: list[JoinedRow], output_path: Path) -> None:
    fieldnames = ["judge_name", "set_name", "condition", "fixed_points", "filename", "source_file", "true_model", "displayed_model", "rank", "overall_score", *rows[0].scores.keys()] if rows else []
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({"judge_name": row.judge_name, "set_name": row.set_name, "condition": row.condition, "fixed_points": row.fixed_points, "filename": row.filename, "source_file": row.source_file, "true_model": row.true_model, "displayed_model": row.displayed_model, "rank": row.rank, "overall_score": row.overall_score, **row.scores})


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_table_csv(rows: list[dict[str, Any]], path: Path) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def fmt_number(value: Any, digits: int = 3) -> str:
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return "NA"
        return f"{value:.{digits}f}"
    return str(value)


def format_effect_row(row: dict[str, Any], estimate_key: str) -> str:
    return f"{fmt_number(row.get(estimate_key))} [{fmt_number(row.get('ci_lower'))}, {fmt_number(row.get('ci_upper'))}], p={fmt_number(row.get('p_value'))}, q={fmt_number(row.get('p_value_fdr'))}"


def render_dataset_section(summary: dict[str, Any]) -> list[str]:
    desc = summary["descriptive_summary"]
    return [
        "# Judge Analysis Report",
        "",
        "## Dataset",
        "",
        f"- Rows analyzed: {desc['row_count']}",
        f"- Judges: {', '.join(desc['judges']) if desc['judges'] else 'none'}",
        f"- Review sets: {', '.join(desc['sets']) if desc['sets'] else 'none'}",
        f"- Permutations: {summary['permutations']}",
        f"- Seed: {summary['seed']}",
        f"- Alpha: {fmt_number(summary['alpha'])}",
        "",
    ]


def render_key_findings_section(summary: dict[str, Any]) -> list[str]:
    control_rows = summary["control_vs_deranged"]
    label_rows = summary["displayed_model_effects"]
    pooled_control = next((row for row in control_rows if row["judge_name"] == "__pooled__"), None)
    pooled_label_rows = [row for row in label_rows if row["judge_name"] == "__pooled__"]
    strongest_label = max(
        pooled_label_rows,
        key=lambda row: abs(row["mean_centered_score_effect"]) if not math.isnan(row["mean_centered_score_effect"]) else -1,
        default=None,
    )
    pooled_agreement = summary["judge_agreement"]["pooled_summary"]
    lines = [
        "## Key Findings",
        "",
    ]
    if pooled_control is not None:
        lines.append(f"- Pooled control-vs-deranged overall effect: {format_effect_row(pooled_control, 'observed_mean_difference')}")
    if strongest_label is not None:
        lines.append(f"- Strongest pooled displayed-label effect: `{strongest_label['displayed_model']}` -> {format_effect_row(strongest_label, 'mean_centered_score_effect')}")
    lines.append(f"- Mean pairwise score agreement (Pearson r): {fmt_number(pooled_agreement['mean_pairwise_score_pearson_r'])}")
    lines.append(f"- Mean pairwise rank agreement (Spearman rho): {fmt_number(pooled_agreement['mean_pairwise_rank_spearman_rho'])}")
    lines.append(f"- Mean top-rank match rate: {fmt_number(pooled_agreement['mean_pairwise_top_rank_match_rate'])}")
    lines.append("")
    return lines


def render_mean_scores_section(summary: dict[str, Any]) -> list[str]:
    desc = summary["descriptive_summary"]
    lines = ["## Mean Overall Score By Judge And Condition", "", "| Judge | Condition | N | Mean Overall Score |", "| --- | --- | ---: | ---: |"]
    for row in desc["mean_overall_score_by_judge_and_condition"]:
        lines.append(f"| {row['judge_name']} | {row['condition']} | {row['n']} | {fmt_number(row['mean_overall_score'])} |")
    lines.append("")
    return lines


def render_pooled_criterion_section(summary: dict[str, Any]) -> list[str]:
    lines = [
        "## Pooled Criterion Effects",
        "",
        "| Criterion | Mean Difference | 95% CI | Std Effect | P Value | FDR Q | Raw Sig | FDR Sig |",
        "| --- | ---: | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for row in summary["criterion_control_vs_deranged"]:
        if row["judge_name"] != "__pooled__":
            continue
        lines.append(
            f"| {row['criterion']} | {fmt_number(row['observed_mean_difference'])} | "
            f"[{fmt_number(row['ci_lower'])}, {fmt_number(row['ci_upper'])}] | "
            f"{fmt_number(row['standardized_effect_dz'])} | {fmt_number(row['p_value'])} | "
            f"{fmt_number(row['p_value_fdr'])} | {row['is_significant_raw']} | {row['is_significant_fdr']} |"
        )
    lines.append("")
    return lines


def render_pooled_label_section(summary: dict[str, Any]) -> list[str]:
    lines = [
        "## Pooled Displayed-Model Effects",
        "",
        "| Displayed Model | Mean Centered Effect | 95% CI | Std Effect | P Value | FDR Q | Raw Sig | FDR Sig |",
        "| --- | ---: | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for row in summary["displayed_model_effects"]:
        if row["judge_name"] != "__pooled__":
            continue
        lines.append(
            f"| {row['displayed_model']} | {fmt_number(row['mean_centered_score_effect'])} | "
            f"[{fmt_number(row['ci_lower'])}, {fmt_number(row['ci_upper'])}] | "
            f"{fmt_number(row['standardized_effect_d'])} | {fmt_number(row['p_value'])} | "
            f"{fmt_number(row['p_value_fdr'])} | {row['is_significant_raw']} | {row['is_significant_fdr']} |"
        )
    lines.append("")
    return lines


def render_agreement_section(summary: dict[str, Any]) -> list[str]:
    lines = [
        "## Judge Agreement",
        "",
        "| Judge A | Judge B | Shared Sets | Score r | Rank rho | Top-Rank Match |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["judge_agreement"]["pairwise"]:
        lines.append(
            f"| {row['judge_a']} | {row['judge_b']} | {row['shared_set_count']} | "
            f"{fmt_number(row['mean_score_pearson_r'])} | {fmt_number(row['mean_rank_spearman_rho'])} | "
            f"{fmt_number(row['top_rank_match_rate'])} |"
        )
    lines.append("")
    return lines


def render_comparison_section(summary: dict[str, Any]) -> list[str]:
    lines = [
        "## Comparison Table",
        "",
        "| Effect Type | Target | Estimate | 95% CI | Std Effect | P Value | FDR Q | Raw Sig | FDR Sig |",
        "| --- | --- | ---: | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for row in summary["comparison_table"]:
        lines.append(
            f"| {row['effect_type']} | {row['target']} | {fmt_number(row['estimate'])} | "
            f"[{fmt_number(row['ci_lower'])}, {fmt_number(row['ci_upper'])}] | "
            f"{fmt_number(row['standardized_effect'])} | {fmt_number(row['p_value'])} | "
            f"{fmt_number(row.get('p_value_fdr'))} | {row.get('is_significant_raw')} | {row.get('is_significant_fdr')} |"
        )
    lines.append("")
    return lines


def build_markdown_report(summary: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.extend(render_dataset_section(summary))
    lines.extend(render_key_findings_section(summary))
    lines.extend(render_mean_scores_section(summary))
    lines.extend(render_pooled_criterion_section(summary))
    lines.extend(render_pooled_label_section(summary))
    lines.extend(render_agreement_section(summary))
    lines.extend(render_comparison_section(summary))
    return "\n".join(lines)
