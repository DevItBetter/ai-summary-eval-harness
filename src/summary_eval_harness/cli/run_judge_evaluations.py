"""CLI for isolated judge execution."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..judge_runner import load_judges, run_all_judges


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run isolated evaluation agents over generated review-set directories.")
    parser.add_argument("review_sets_dir", type=Path, help="Directory containing numbered review-set subdirectories.")
    parser.add_argument("--judges-config", type=Path, required=True, help="JSON file describing the judge commands to run.")
    parser.add_argument("--rubric-file", type=Path, required=True, help="Markdown or text file containing the shared evaluation rubric.")
    parser.add_argument("--prompt-template", type=Path, default=Path(__file__).resolve().parents[1] / "templates" / "judge_prompt.txt", help="Prompt template file.")
    parser.add_argument("--results-dir", type=Path, default=Path("judge_results"), help="Directory where final judge output files will be written.")
    parser.add_argument("--work-root", type=Path, default=Path(".judge_runs"), help="Root for temporary per-judge workspaces. This directory is recreated on each run.")
    parser.add_argument("--timeout-seconds", type=int, default=900, help="Per-judge timeout in seconds.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing work-root and result directories.")
    if len(sys.argv) == 1:
        parser.print_help()
        raise SystemExit(0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    judges = load_judges(args.judges_config.resolve())
    run_log = run_all_judges(args.review_sets_dir.resolve(), judges, args.rubric_file.resolve(), args.prompt_template.resolve(), args.results_dir.resolve(), args.work_root.resolve(), args.timeout_seconds, args.force)
    print(f"Wrote run log to: {Path(run_log['results_dir']) / 'run_log.json'}")
    return 0
