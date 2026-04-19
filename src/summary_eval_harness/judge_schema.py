"""Judge output parsing and validation."""

from __future__ import annotations

import json
import re
from typing import Any

from .constants import RUBRIC_KEYS


ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
FENCED_JSON_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


def strip_json_fence(text: str) -> str:
    match = FENCED_JSON_RE.match(text)
    return match.group(1).strip() if match else text


def decode_first_json_value(text: str) -> Any:
    decoder = json.JSONDecoder()
    try:
        return decoder.decode(text)
    except json.JSONDecodeError:
        pass
    # Some model CLIs prepend prose or logs before the final JSON object
    for index, char in enumerate(text):
        if char not in "{[":
            continue
        try:
            value, _end = decoder.raw_decode(text[index:])
            return value
        except json.JSONDecodeError:
            continue
    raise json.JSONDecodeError("no JSON value found in stdout", text, 0)


def parse_judge_stdout(stdout: str) -> Any:
    cleaned = ANSI_ESCAPE_RE.sub("", stdout).strip()
    if not cleaned:
        raise json.JSONDecodeError("empty stdout", stdout, 0)
    top_level = decode_first_json_value(cleaned)
    if isinstance(top_level, dict) and isinstance(top_level.get("result"), str):
        # Claude-style wrappers can place the actual payload in a string field
        result_text = strip_json_fence(top_level["result"].strip())
        if result_text:
            try:
                return json.loads(result_text)
            except json.JSONDecodeError:
                return top_level
    if isinstance(top_level, dict) and isinstance(top_level.get("response"), str):
        # Gemini-style wrappers can place the actual payload in a response field
        response_text = strip_json_fence(top_level["response"].strip())
        if response_text:
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                return top_level
    return top_level


def validate_result_payload(payload: Any, judge_name: str, set_name: str, summary_filenames: list[str]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("Judge output must be a JSON object.")
    required_top_keys = {
        "judge_name",
        "set_name",
        "evaluated_at",
        "source_text_file",
        "rubric_version",
        "results",
        "ranking",
        "overall_notes",
    }
    if set(payload.keys()) != required_top_keys:
        raise ValueError(f"Judge output must contain exactly these top-level keys: {sorted(required_top_keys)}")
    if payload["judge_name"] != judge_name:
        raise ValueError(f"judge_name must be '{judge_name}'.")
    if payload["set_name"] != set_name:
        raise ValueError(f"set_name must be '{set_name}'.")
    if not isinstance(payload["source_text_file"], str) or not payload["source_text_file"].endswith(".txt"):
        raise ValueError("source_text_file must be a .txt filename string.")
    if not isinstance(payload["rubric_version"], str) or not payload["rubric_version"].strip():
        raise ValueError("rubric_version must be a non-empty string.")
    if payload["evaluated_at"] is not None and not isinstance(payload["evaluated_at"], str):
        raise ValueError("evaluated_at must be a string or null.")
    if not isinstance(payload["overall_notes"], str):
        raise ValueError("overall_notes must be a string.")

    expected_files = set(summary_filenames)
    results = payload["results"]
    if not isinstance(results, list) or len(results) != len(summary_filenames):
        raise ValueError("results must be a list with one entry per summary file.")

    seen_result_files: set[str] = set()
    for item in results:
        if not isinstance(item, dict):
            raise ValueError("Each results entry must be an object.")
        required_result_keys = {"filename", "scores", "overall_score", "strengths", "weaknesses", "notes"}
        if set(item.keys()) != required_result_keys:
            raise ValueError(f"Each results entry must contain exactly these keys: {sorted(required_result_keys)}")
        filename = item["filename"]
        if filename not in expected_files:
            raise ValueError(f"Unexpected filename in results: {filename}")
        if filename in seen_result_files:
            raise ValueError(f"Duplicate filename in results: {filename}")
        seen_result_files.add(filename)
        scores = item["scores"]
        if not isinstance(scores, dict) or tuple(scores.keys()) != RUBRIC_KEYS:
            raise ValueError(f"scores must contain exactly these keys in order: {list(RUBRIC_KEYS)}")
        for rubric_key, value in scores.items():
            if not isinstance(value, int) or not (0 <= value <= 5):
                raise ValueError(f"Score '{rubric_key}' must be an integer from 0 to 5.")
        overall_score = item["overall_score"]
        if not isinstance(overall_score, (int, float)) or not (0 <= overall_score <= 5):
            raise ValueError("overall_score must be a number from 0 to 5.")
        if not isinstance(item["strengths"], list) or not all(isinstance(v, str) for v in item["strengths"]):
            raise ValueError("strengths must be a list of strings.")
        if not isinstance(item["weaknesses"], list) or not all(isinstance(v, str) for v in item["weaknesses"]):
            raise ValueError("weaknesses must be a list of strings.")
        if not isinstance(item["notes"], str):
            raise ValueError("notes must be a string.")

    ranking = payload["ranking"]
    if not isinstance(ranking, list) or len(ranking) != len(summary_filenames):
        raise ValueError("ranking must be a list with one entry per summary file.")
    seen_rank_files: set[str] = set()
    seen_ranks: set[int] = set()
    for item in ranking:
        if not isinstance(item, dict):
            raise ValueError("Each ranking entry must be an object.")
        if set(item.keys()) != {"filename", "rank"}:
            raise ValueError("Each ranking entry must contain exactly 'filename' and 'rank'.")
        filename = item["filename"]
        rank = item["rank"]
        if filename not in expected_files:
            raise ValueError(f"Unexpected filename in ranking: {filename}")
        if filename in seen_rank_files:
            raise ValueError(f"Duplicate filename in ranking: {filename}")
        seen_rank_files.add(filename)
        if not isinstance(rank, int):
            raise ValueError("rank must be an integer.")
        if rank in seen_ranks:
            raise ValueError(f"Duplicate rank in ranking: {rank}")
        seen_ranks.add(rank)
    if seen_ranks != set(range(1, len(summary_filenames) + 1)):
        raise ValueError("ranking must use unique ranks starting at 1 with no gaps.")
