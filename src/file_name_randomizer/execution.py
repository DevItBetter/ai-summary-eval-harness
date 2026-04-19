"""Shared execution helpers for generator and judge workflows."""

from __future__ import annotations

import json
import shutil
import subprocess
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, TypeVar


ConfigT = TypeVar("ConfigT")


def load_config_entries(
    config_path: Path,
    config_label: str,
    factory: Callable[[str, list[str], dict[str, str], str], ConfigT],
) -> list[ConfigT]:
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"{config_label} config must be a non-empty JSON list.")

    entries: list[ConfigT] = []
    for entry in payload:
        if not isinstance(entry, dict):
            raise ValueError(f"Each {config_label} config entry must be an object.")
        name = entry.get("name")
        command = entry.get("command")
        env = entry.get("env", {})
        capture_mode = entry.get("capture_mode", "stdout_json")
        if not isinstance(name, str) or not name:
            raise ValueError(f"Each {config_label} config entry needs a non-empty string 'name'.")
        if not isinstance(command, list) or not all(isinstance(part, str) for part in command):
            raise ValueError(f"{config_label.title()} '{name}' needs 'command' as a list of strings.")
        if not isinstance(env, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in env.items()):
            raise ValueError(f"{config_label.title()} '{name}' has an invalid 'env' map.")
        if capture_mode != "stdout_json":
            raise ValueError(f"{config_label.title()} '{name}' has unsupported capture_mode '{capture_mode}'.")
        entries.append(factory(name, command, env, capture_mode))
    return entries


def prepare_directory(path: Path, force: bool) -> None:
    if path.exists():
        if not force:
            raise ValueError(f"Path already exists: {path}. Re-run with --force to overwrite.")
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def hash_directory(root: Path) -> dict[str, str]:
    manifest: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            manifest[path.relative_to(root).as_posix()] = sha256(path.read_bytes()).hexdigest()
    return manifest


def load_prompt_template(template_path: Path) -> str:
    return template_path.read_text(encoding="utf-8")


def replace_placeholders(parts: list[str], values: dict[str, str]) -> list[str]:
    # Replace only our known tokens so JSON braces in command strings stay intact
    replaced: list[str] = []
    for part in parts:
        updated = part
        for key, value in values.items():
            updated = updated.replace("{" + key + "}", value)
        replaced.append(updated)
    return replaced


def run_command(
    command: list[str],
    cwd: Path,
    env: dict[str, str],
    timeout_seconds: int,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
