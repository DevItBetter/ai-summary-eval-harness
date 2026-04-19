"""Isolated judge execution."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from string import Template
from typing import Any

from .execution import (
    hash_directory,
    load_config_entries,
    load_prompt_template,
    prepare_directory,
    replace_placeholders,
    run_command,
)
from .judge_schema import parse_judge_stdout, validate_result_payload
from .types import JudgeConfig


def build_input_bundle(set_dir: Path) -> str:
    parts: list[str] = []
    for path in sorted(set_dir.iterdir()):
        if not path.is_file():
            continue
        if path.suffix not in {".txt", ".md"}:
            continue
        parts.append(f"### {path.name}\n")
        parts.append(path.read_text(encoding="utf-8").rstrip())
        parts.append("\n")
    return "\n".join(parts).strip()


def build_allowed_filenames(summary_filenames: list[str]) -> str:
    return "\n".join(f"- {filename}" for filename in summary_filenames)


def load_judges(config_path: Path) -> list[JudgeConfig]:
    return load_config_entries(config_path, "judge", JudgeConfig)


def run_one_judge(
    judge: JudgeConfig,
    set_dir: Path,
    rubric_text: str,
    prompt_template: str,
    results_dir: Path,
    work_root: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    set_name = set_dir.name
    summary_filenames = sorted(path.name for path in set_dir.glob("*.md"))
    final_output_dir = results_dir / judge.name
    final_output_dir.mkdir(parents=True, exist_ok=True)
    final_output_file = final_output_dir / f"{set_name}.json"
    workspace_parent = work_root / judge.name
    workspace_parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(dir=workspace_parent, prefix=f"{set_name}_") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        input_dir = temp_dir / "input"
        shutil.copytree(set_dir, input_dir)
        before_manifest = hash_directory(input_dir)

        prompt_text = Template(prompt_template).substitute(
            rubric_text=rubric_text.strip(),
            judge_name=judge.name,
            set_name=set_name,
            allowed_filenames=build_allowed_filenames(summary_filenames),
            input_bundle=build_input_bundle(input_dir),
        )
        prompt_file = temp_dir / "judge_prompt.txt"
        prompt_file.write_text(prompt_text, encoding="utf-8")

        placeholders = {
            "judge_name": judge.name,
            "set_name": set_name,
            "workspace": str(input_dir),
            "prompt": prompt_text,
            "prompt_file": str(prompt_file),
            "output_file": str(final_output_file),
        }
        command = replace_placeholders(judge.command, placeholders)

        env = os.environ.copy()
        env.update(judge.env)
        env.update({"JUDGE_NAME": judge.name, "REVIEW_SET_NAME": set_name, "JUDGE_PROMPT_FILE": str(prompt_file)})

        started_at = datetime.now().isoformat(timespec="seconds")
        completed = run_command(command, input_dir, env, timeout_seconds)
        finished_at = datetime.now().isoformat(timespec="seconds")

        output_written = False
        output_error: str | None = None
        if completed.returncode == 0 and judge.capture_mode == "stdout_json":
            try:
                parsed = parse_judge_stdout(completed.stdout)
                validate_result_payload(parsed, judge.name, set_name, summary_filenames)
                final_output_file.write_text(json.dumps(parsed, indent=2) + "\n", encoding="utf-8")
                output_written = True
            except (json.JSONDecodeError, ValueError) as exc:
                output_error = str(exc)

        after_manifest = hash_directory(input_dir)
        return {
            "judge_name": judge.name,
            "set_name": set_name,
            "command": command,
            "started_at": started_at,
            "finished_at": finished_at,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "output_file": str(final_output_file),
            "output_exists": final_output_file.exists(),
            "output_written": output_written,
            "output_error": output_error,
            "input_untouched": before_manifest == after_manifest,
        }


def run_all_judges(
    review_sets_dir: Path,
    judges: list[JudgeConfig],
    rubric_file: Path,
    prompt_template_path: Path,
    results_dir: Path,
    work_root: Path,
    timeout_seconds: int,
    force: bool,
) -> dict[str, Any]:
    if not review_sets_dir.is_dir():
        raise ValueError(f"Review sets directory does not exist: {review_sets_dir}")
    if not rubric_file.is_file():
        raise ValueError(f"Rubric file does not exist: {rubric_file}")

    set_dirs = sorted(path for path in review_sets_dir.iterdir() if path.is_dir())
    if not set_dirs:
        raise ValueError(f"No review-set subdirectories found in {review_sets_dir}")

    prepare_directory(work_root, force)
    prepare_directory(results_dir, force)
    rubric_text = rubric_file.read_text(encoding="utf-8")
    prompt_template = load_prompt_template(prompt_template_path)

    run_log: dict[str, Any] = {
        "review_sets_dir": str(review_sets_dir),
        "rubric_file": str(rubric_file),
        "results_dir": str(results_dir),
        "work_root": str(work_root),
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "runs": [],
    }
    for set_dir in set_dirs:
        for judge in judges:
            run_log["runs"].append(
                run_one_judge(judge, set_dir, rubric_text, prompt_template, results_dir, work_root, timeout_seconds)
            )
    run_log["finished_at"] = datetime.now().isoformat(timespec="seconds")
    (results_dir / "run_log.json").write_text(json.dumps(run_log, indent=2), encoding="utf-8")
    return run_log
