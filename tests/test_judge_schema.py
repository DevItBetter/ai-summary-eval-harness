from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from summary_eval_harness.judge_schema import parse_judge_stdout, validate_result_payload


def valid_payload() -> dict:
    return {
        "judge_name": "judge",
        "set_name": "000",
        "evaluated_at": None,
        "source_text_file": "prompt.txt",
        "rubric_version": "v1",
        "results": [
            {
                "filename": "a.md",
                "scores": {
                    "accuracy": 1,
                    "completeness": 1,
                    "clarity": 1,
                    "faithfulness_to_source_prompt": 1,
                    "actionability": 1,
                },
                "overall_score": 1,
                "strengths": [],
                "weaknesses": [],
                "notes": "",
            }
        ],
        "ranking": [{"filename": "a.md", "rank": 1}],
        "overall_notes": "",
    }


class JudgeSchemaTests(unittest.TestCase):
    def test_parse_judge_stdout_unwraps_claude_result(self) -> None:
        payload = json.dumps(valid_payload(), indent=2)
        wrapped = json.dumps({"result": f"```json\n{payload}\n```"})
        parsed = parse_judge_stdout(wrapped)
        self.assertEqual(parsed["judge_name"], "judge")

    def test_parse_judge_stdout_extracts_json_after_prefix(self) -> None:
        payload = json.dumps(valid_payload())
        parsed = parse_judge_stdout(f"preface line\n{payload}")
        self.assertEqual(parsed["set_name"], "000")

    def test_validate_result_payload_rejects_extra_keys(self) -> None:
        payload = valid_payload()
        payload["extra"] = True
        with self.assertRaises(ValueError):
            validate_result_payload(payload, "judge", "000", ["a.md"])


if __name__ == "__main__":
    unittest.main()
