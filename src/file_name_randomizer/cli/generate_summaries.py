"""CLI for isolated summary generation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..generator_runner import load_generators, run_all_generators


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate blinded summary candidates in isolated workspaces.")
    parser.add_argument("input_dir", type=Path, help="Directory containing exactly one .txt source file.")
    parser.add_argument("--generators-config", type=Path, required=True, help="JSON file describing the generator commands to run.")
    parser.add_argument("--rubric-file", type=Path, required=True, help="Markdown or text file containing the shared generation rubric.")
    parser.add_argument("--prompt-template", type=Path, default=Path(__file__).resolve().parents[1] / "templates" / "generator_prompt.txt", help="Prompt template file.")
    parser.add_argument("--outputs-dir", type=Path, default=Path("generated_summaries"), help="Directory where generated markdown files will be written.")
    parser.add_argument("--work-root", type=Path, default=Path(".generator_runs"), help="Root for temporary per-generator workspaces.")
    parser.add_argument("--timeout-seconds", type=int, default=900, help="Per-generator timeout in seconds.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing output and work directories.")
    if len(sys.argv) == 1:
        parser.print_help()
        raise SystemExit(0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    generators = load_generators(args.generators_config.resolve())
    run_log = run_all_generators(
        args.input_dir.resolve(),
        generators,
        args.rubric_file.resolve(),
        args.prompt_template.resolve(),
        args.outputs_dir.resolve(),
        args.work_root.resolve(),
        args.timeout_seconds,
        args.force,
    )
    print(f"Wrote generation run log to: {Path(run_log['outputs_dir']) / 'run_log.json'}")
    return 0
