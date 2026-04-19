"""Core shuffle and sanitization logic."""

from __future__ import annotations

import json
import math
import random
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .constants import SUMMARY_FILENAME_PATTERN
from .types import SummaryFile


SUMMARY_PATTERN = re.compile(SUMMARY_FILENAME_PATTERN)


@dataclass(frozen=True)
class ShuffleConfig:
    input_dir: Path
    count: int
    seed: int | None
    clean_dir_name: str
    sets_dir_name: str
    mapping_file: Path | None
    force: bool


def find_source_files(input_dir: Path) -> tuple[Path, str, list[SummaryFile]]:
    if not input_dir.is_dir():
        raise ValueError(f"Input directory does not exist or is not a directory: {input_dir}")

    txt_files = sorted(input_dir.glob("*.txt"))
    if len(txt_files) != 1:
        raise ValueError(f"Expected exactly one .txt file in {input_dir}, found {len(txt_files)}.")

    txt_file = txt_files[0]
    prefix = txt_file.stem
    summaries: list[SummaryFile] = []
    for path in sorted(input_dir.glob("*.md")):
        match = SUMMARY_PATTERN.match(path.name)
        if not match:
            raise ValueError(f"Markdown file does not match '<prefix>_summary__<model>.md': {path.name}")
        if match.group("prefix") != prefix:
            raise ValueError(f"Markdown file prefix does not match {txt_file.name}: {path.name}")
        summaries.append(SummaryFile(path=path, filename=path.name, model_name=match.group("model")))

    if len(summaries) < 2:
        raise ValueError("At least two markdown summary files are required to build derangements.")
    return txt_file, prefix, summaries


def prepare_directory(path: Path, force: bool) -> None:
    if path.exists():
        if not force:
            raise ValueError(f"Output path already exists: {path}. Re-run with --force to overwrite it.")
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def sequential_pattern(tokens: Iterable[str]) -> str:
    escaped = [re.escape(token) for token in tokens]
    separator = r"(?:[\s\-_./]+)"
    return rf"(?<!\w){separator.join(escaped)}(?!\w)"


def tokenized_model_patterns(model_name: str) -> list[re.Pattern[str]]:
    raw_tokens = [token for token in re.split(r"[-_]+", model_name) if token]
    alpha_tokens = [token for token in raw_tokens if re.search(r"[A-Za-z]", token)]
    patterns: list[str] = []
    if raw_tokens:
        patterns.append(sequential_pattern(raw_tokens))
    if alpha_tokens and alpha_tokens != raw_tokens:
        patterns.append(sequential_pattern(alpha_tokens))
    return [re.compile(pattern, re.IGNORECASE) for pattern in dict.fromkeys(patterns)]


def sanitize_text(text: str, model_name: str) -> str:
    # Remove only sequential model-token mentions derived from the filename suffix
    for pattern in tokenized_model_patterns(model_name):
        text = pattern.sub("", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r" +([,.;:!?])", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def build_clean_dir(clean_dir: Path, txt_file: Path, summaries: list[SummaryFile]) -> dict[str, Path]:
    shutil.copy2(txt_file, clean_dir / txt_file.name)
    clean_paths: dict[str, Path] = {}
    for summary in summaries:
        cleaned_text = sanitize_text(summary.path.read_text(encoding="utf-8"), summary.model_name)
        clean_path = clean_dir / summary.filename
        clean_path.write_text(cleaned_text, encoding="utf-8")
        clean_paths[summary.filename] = clean_path
    return clean_paths


def derangement_count(size: int) -> int:
    return int(round(math.factorial(size) / math.e))


def sample_derangements(items: list[str], count: int, seed: int | None) -> list[tuple[str, ...]]:
    if count < 0:
        raise ValueError("--count must be non-negative.")
    all_possible = derangement_count(len(items))
    if count > all_possible:
        raise ValueError(f"Requested {count} derangements, but only {all_possible} exist for {len(items)} files.")

    rng = random.Random(seed)
    wanted: set[tuple[str, ...]] = set()
    original = tuple(items)
    while len(wanted) < count:
        candidate = tuple(rng.sample(items, len(items)))
        if candidate == original:
            continue
        if any(candidate[index] == items[index] for index in range(len(items))):
            continue
        wanted.add(candidate)
    return sorted(wanted)


def write_review_set(
    output_dir: Path,
    txt_file: Path,
    prefix: str,
    summaries: list[SummaryFile],
    clean_paths: dict[str, Path],
    assigned_models: tuple[str, ...],
) -> list[dict[str, str]]:
    shutil.copy2(txt_file, output_dir / txt_file.name)
    rows: list[dict[str, str]] = []
    for summary, displayed_model in zip(summaries, assigned_models):
        source_clean_path = clean_paths[summary.filename]
        destination_name = f"{prefix}_summary__{displayed_model}.md"
        shutil.copy2(source_clean_path, output_dir / destination_name)
        rows.append(
            {
                "source_file": summary.filename,
                "source_clean_file": source_clean_path.name,
                "true_model": summary.model_name,
                "displayed_model": displayed_model,
                "output_file": destination_name,
            }
        )
    return rows


def default_mapping_path(input_dir: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path.cwd() / f"{input_dir.name}_model_shuffle_mapping_{stamp}.json"


def run_shuffle(config: ShuffleConfig) -> dict[str, object]:
    input_dir = config.input_dir.resolve()
    txt_file, prefix, summaries = find_source_files(input_dir)
    clean_dir = input_dir / config.clean_dir_name
    sets_root = input_dir / config.sets_dir_name
    mapping_path = config.mapping_file.resolve() if config.mapping_file else default_mapping_path(input_dir)

    prepare_directory(clean_dir, config.force)
    prepare_directory(sets_root, config.force)
    clean_paths = build_clean_dir(clean_dir, txt_file, summaries)

    model_names = [summary.model_name for summary in summaries]
    sampled_derangements = sample_derangements(model_names, config.count, config.seed)
    original_assignment = tuple(model_names)
    all_assignments = [original_assignment, *sampled_derangements]

    review_sets: list[dict[str, object]] = []
    for index, assignment in enumerate(all_assignments):
        set_dir = sets_root / f"{index:03d}"
        set_dir.mkdir(parents=True, exist_ok=False)
        rows = write_review_set(set_dir, txt_file, prefix, summaries, clean_paths, assignment)
        review_sets.append(
            {
                "set_name": set_dir.name,
                "set_path": str(set_dir),
                "internal_label": "original" if assignment == original_assignment else f"deranged_{index:03d}",
                "condition": "original" if assignment == original_assignment else "deranged",
                "fixed_points": sum(1 for expected, displayed in zip(model_names, assignment) if expected == displayed),
                "files": rows,
            }
        )

    mapping = {
        "input_directory": str(input_dir),
        "text_file": txt_file.name,
        "prefix": prefix,
        "clean_directory": str(clean_dir.resolve()),
        "review_sets_directory": str(sets_root.resolve()),
        "mapping_generated_at": datetime.now().isoformat(timespec="seconds"),
        "seed": config.seed,
        "requested_deranged_set_count": config.count,
        "summary_files": [{"filename": summary.filename, "model_name": summary.model_name} for summary in summaries],
        "review_sets": review_sets,
    }
    mapping_path.write_text(json.dumps(mapping, indent=2), encoding="utf-8")
    return {
        "clean_dir": clean_dir,
        "sets_root": sets_root,
        "mapping_path": mapping_path,
        "mapping": mapping,
    }
