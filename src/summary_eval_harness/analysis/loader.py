"""Load mapping and judge results into normalized rows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..constants import RUBRIC_KEYS
from ..types import JoinedRow


def load_mapping(mapping_file: Path) -> dict[str, Any]:
    payload = json.loads(mapping_file.read_text(encoding="utf-8"))
    review_sets = payload.get("review_sets")
    if not isinstance(review_sets, list) or not review_sets:
        raise ValueError("Mapping file does not contain review_sets.")
    return payload


def index_mapping_sets(mapping_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for review_set in mapping_payload["review_sets"]:
        indexed[review_set["set_name"]] = {
            "condition": review_set["condition"],
            "fixed_points": review_set["fixed_points"],
            "files": {item["output_file"]: item for item in review_set["files"]},
        }
    return indexed


def load_joined_rows(mapping_index: dict[str, dict[str, Any]], results_dir: Path) -> list[JoinedRow]:
    rows: list[JoinedRow] = []
    for judge_dir in sorted(path for path in results_dir.iterdir() if path.is_dir()):
        for result_file in sorted(judge_dir.glob("*.json")):
            payload = json.loads(result_file.read_text(encoding="utf-8"))
            set_name = payload["set_name"]
            if set_name not in mapping_index:
                raise ValueError(f"Result set_name '{set_name}' not found in mapping.")
            set_mapping = mapping_index[set_name]
            ranking = {item["filename"]: item["rank"] for item in payload["ranking"]}
            for result in payload["results"]:
                filename = result["filename"]
                mapped = set_mapping["files"].get(filename)
                if mapped is None:
                    raise ValueError(f"Filename '{filename}' in {result_file} not found in mapping for set '{set_name}'.")
                rows.append(
                    JoinedRow(
                        judge_name=payload["judge_name"],
                        set_name=set_name,
                        condition=set_mapping["condition"],
                        fixed_points=set_mapping["fixed_points"],
                        filename=filename,
                        source_file=mapped["source_file"],
                        true_model=mapped["true_model"],
                        displayed_model=mapped["displayed_model"],
                        rank=ranking[filename],
                        overall_score=float(result["overall_score"]),
                        scores={key: int(result["scores"][key]) for key in RUBRIC_KEYS},
                    )
                )
    if not rows:
        raise ValueError("No judge results found.")
    return rows
