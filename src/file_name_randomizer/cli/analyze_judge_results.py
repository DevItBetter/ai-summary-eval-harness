"""CLI for analysis."""

from __future__ import annotations

import argparse
from pathlib import Path

from ..analysis.correction import apply_bh_fdr
from ..analysis.loader import index_mapping_sets, load_joined_rows, load_mapping
from ..analysis.reporting import build_markdown_report, prepare_output_dir, write_flat_csv, write_json, write_table_csv
from ..analysis.stats import comparison_table, control_vs_deranged, criterion_control_vs_deranged, descriptive_summary, judge_agreement, label_effects


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze judge outputs against the model-shuffle mapping.")
    parser.add_argument("mapping_file", type=Path, help="JSON mapping produced by shuffle_model_names.py")
    parser.add_argument("results_dir", type=Path, help="Directory containing per-judge JSON results")
    parser.add_argument("--output-dir", type=Path, default=Path("analysis_output"), help="Directory for CSV and JSON analysis artifacts.")
    parser.add_argument("--permutations", type=int, default=5000, help="Number of random permutations for Monte Carlo tests.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible permutation tests.")
    parser.add_argument("--alpha", type=float, default=0.05, help="Significance threshold for raw and FDR-adjusted hypothesis flags.")
    parser.add_argument("--force", action="store_true", help="Overwrite output directory if it exists.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    mapping_payload = load_mapping(args.mapping_file.resolve())
    mapping_index = index_mapping_sets(mapping_payload)
    rows = load_joined_rows(mapping_index, args.results_dir.resolve())
    output_dir = args.output_dir.resolve()
    prepare_output_dir(output_dir, args.force)
    write_flat_csv(rows, output_dir / "joined_results.csv")

    control_results = apply_bh_fdr(control_vs_deranged(rows, args.permutations, args.seed), args.alpha)
    criterion_results = apply_bh_fdr(criterion_control_vs_deranged(rows, args.permutations, args.seed), args.alpha)
    label_results = apply_bh_fdr(label_effects(rows, args.permutations, args.seed), args.alpha)
    summary_table = apply_bh_fdr(comparison_table(control_results, label_results, criterion_results), args.alpha)
    agreement = judge_agreement(rows)

    summary = {
        "mapping_file": str(args.mapping_file.resolve()),
        "results_dir": str(args.results_dir.resolve()),
        "permutations": args.permutations,
        "seed": args.seed,
        "alpha": args.alpha,
        "descriptive_summary": descriptive_summary(rows),
        "control_vs_deranged": control_results,
        "criterion_control_vs_deranged": criterion_results,
        "displayed_model_effects": label_results,
        "comparison_table": summary_table,
        "judge_agreement": agreement,
    }
    write_json(output_dir / "analysis_summary.json", summary)
    write_table_csv(control_results, output_dir / "control_vs_deranged.csv")
    write_table_csv(criterion_results, output_dir / "criterion_control_vs_deranged.csv")
    write_table_csv(label_results, output_dir / "displayed_model_effects.csv")
    write_table_csv(summary_table, output_dir / "comparison_table.csv")
    write_table_csv(agreement["pairwise"], output_dir / "judge_agreement_pairwise.csv")
    (output_dir / "analysis_report.md").write_text(build_markdown_report(summary), encoding="utf-8")
    print(f"Wrote joined CSV to: {output_dir / 'joined_results.csv'}")
    print(f"Wrote analysis summary to: {output_dir / 'analysis_summary.json'}")
    return 0
