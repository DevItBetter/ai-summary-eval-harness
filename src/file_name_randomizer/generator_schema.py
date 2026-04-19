"""Generator output parsing and validation."""

from __future__ import annotations

import json
from typing import Any

from .judge_schema import parse_judge_stdout


def parse_generator_stdout(stdout: str) -> Any:
    return parse_judge_stdout(stdout)


def validate_generator_payload(payload: Any, source_text_filename: str) -> None:
    if not isinstance(payload, dict):
        raise ValueError("Generator output must be a JSON object.")

    required_top_keys = {
        "source_text_file",
        "summary_markdown",
        "notes",
    }
    if set(payload.keys()) != required_top_keys:
        raise ValueError(
            f"Generator output must contain exactly these top-level keys: {sorted(required_top_keys)}"
        )

    if payload["source_text_file"] != source_text_filename:
        raise ValueError(f"source_text_file must be '{source_text_filename}'.")
    if not isinstance(payload["summary_markdown"], str) or not payload["summary_markdown"].strip():
        raise ValueError("summary_markdown must be a non-empty string.")
    if not isinstance(payload["notes"], str):
        raise ValueError("notes must be a string.")
