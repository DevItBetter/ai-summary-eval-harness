"""CLI for shuffle workflow."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..shuffle import ShuffleConfig, run_shuffle


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create blinded review sets by removing model mentions and shuffling model labels in summary filenames."
    )
    parser.add_argument("input_dir", type=Path, help="Directory containing one .txt file and summary .md files.")
    parser.add_argument("--count", type=int, default=5, help="Number of deranged review sets to generate in addition to the original control set.")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducible derangement sampling.")
    parser.add_argument("--clean-dir", default="clean", help="Child directory under the input directory that will hold sanitized source copies.")
    parser.add_argument("--sets-dir", default="review_sets", help="Child directory under the input directory that will hold generated review set subdirectories.")
    parser.add_argument("--mapping-file", type=Path, default=None, help="Optional path for the JSON mapping file. Defaults to the current working directory.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing clean and review-set output directories.")
    if len(sys.argv) == 1:
        parser.print_help()
        raise SystemExit(0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_shuffle(ShuffleConfig(args.input_dir, args.count, args.seed, args.clean_dir, args.sets_dir, args.mapping_file, args.force))
    print(f"Wrote sanitized files to: {result['clean_dir']}")
    print(f"Wrote review sets to: {result['sets_root']}")
    print(f"Wrote mapping file to: {result['mapping_path']}")
    return 0
