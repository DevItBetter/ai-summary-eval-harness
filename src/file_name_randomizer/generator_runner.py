"""Isolated summary generation."""

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
from .generator_schema import parse_generator_stdout, validate_generator_payload
from .types import GeneratorConfig


def load_generators(config_path: Path) -> list[GeneratorConfig]:
    return load_config_entries(config_path, "generator", GeneratorConfig)


def render_prompt(
    template_text: str,
    rubric_text: str,
    generator_name: str,
    source_text_filename: str,
    source_text: str,
) -> str:
    return Template(template_text).substitute(
        rubric_text=rubric_text.strip(),
        generator_name=generator_name,
        source_text_file=source_text_filename,
        source_text=source_text.rstrip(),
    )


def run_one_generator(
    generator: GeneratorConfig,
    input_dir: Path,
    rubric_text: str,
    prompt_template: str,
    outputs_dir: Path,
    work_root: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    txt_files = sorted(input_dir.glob("*.txt"))
    if len(txt_files) != 1:
        raise ValueError(f"Expected exactly one .txt file in {input_dir}, found {len(txt_files)}.")
    txt_file = txt_files[0]
    prefix = txt_file.stem

    output_file = outputs_dir / f"{prefix}_summary__{generator.name}.md"
    workspace_parent = work_root / generator.name
    workspace_parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(dir=workspace_parent, prefix=f"{prefix}_") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        workspace_input = temp_dir / "input"
        workspace_input.mkdir(parents=True, exist_ok=True)
        shutil.copy2(txt_file, workspace_input / txt_file.name)
        before_manifest = hash_directory(workspace_input)

        prompt_text = render_prompt(
            prompt_template,
            rubric_text,
            generator.name,
            txt_file.name,
            txt_file.read_text(encoding="utf-8"),
        )
        prompt_file = temp_dir / "generator_prompt.txt"
        prompt_file.write_text(prompt_text, encoding="utf-8")

        placeholders = {
            "generator_name": generator.name,
            "workspace": str(workspace_input),
            "prompt": prompt_text,
            "prompt_file": str(prompt_file),
            "output_file": str(output_file),
        }
        command = replace_placeholders(generator.command, placeholders)

        env = os.environ.copy()
        env.update(generator.env)
        env.update({"GENERATOR_NAME": generator.name, "GENERATOR_PROMPT_FILE": str(prompt_file)})

        started_at = datetime.now().isoformat(timespec="seconds")
        completed = run_command(command, workspace_input, env, timeout_seconds)
        finished_at = datetime.now().isoformat(timespec="seconds")

        output_written = False
        output_error: str | None = None
        payload: dict[str, Any] | None = None
        if completed.returncode == 0 and generator.capture_mode == "stdout_json":
            try:
                parsed = parse_generator_stdout(completed.stdout)
                validate_generator_payload(parsed, txt_file.name)
                payload = parsed
                output_file.write_text(parsed["summary_markdown"].rstrip() + "\n", encoding="utf-8")
                output_written = True
            except (json.JSONDecodeError, ValueError) as exc:
                output_error = str(exc)

        after_manifest = hash_directory(workspace_input)
        return {
            "generator_name": generator.name,
            "started_at": started_at,
            "finished_at": finished_at,
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "output_file": str(output_file),
            "output_exists": output_file.exists(),
            "output_written": output_written,
            "output_error": output_error,
            "input_untouched": before_manifest == after_manifest,
            "payload": payload,
        }


def run_all_generators(
    input_dir: Path,
    generators: list[JudgeConfig],
    rubric_file: Path,
    prompt_template_path: Path,
    outputs_dir: Path,
    work_root: Path,
    timeout_seconds: int,
    force: bool,
) -> dict[str, Any]:
    if not input_dir.is_dir():
        raise ValueError(f"Input directory does not exist: {input_dir}")
    if not rubric_file.is_file():
        raise ValueError(f"Rubric file does not exist: {rubric_file}")

    prepare_directory(outputs_dir, force)
    prepare_directory(work_root, force)

    rubric_text = rubric_file.read_text(encoding="utf-8")
    prompt_template = load_prompt_template(prompt_template_path)

    run_log: dict[str, Any] = {
        "input_dir": str(input_dir),
        "rubric_file": str(rubric_file),
        "outputs_dir": str(outputs_dir),
        "work_root": str(work_root),
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "runs": [],
    }
    for generator in generators:
        run_log["runs"].append(
            run_one_generator(generator, input_dir, rubric_text, prompt_template, outputs_dir, work_root, timeout_seconds)
        )
    run_log["finished_at"] = datetime.now().isoformat(timespec="seconds")
    (outputs_dir / "run_log.json").write_text(json.dumps(run_log, indent=2), encoding="utf-8")
    return run_log
