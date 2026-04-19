from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from summary_eval_harness.generator_schema import parse_generator_stdout, validate_generator_payload


class GeneratorSchemaTests(unittest.TestCase):
    def test_parse_generator_stdout_handles_prefixed_json(self) -> None:
        payload = {
            "source_text_file": "session.txt",
            "summary_markdown": "# Summary\nHello\n",
            "notes": "",
        }
        parsed = parse_generator_stdout("status line\n" + json.dumps(payload))
        self.assertEqual(parsed["source_text_file"], "session.txt")

    def test_validate_generator_payload_rejects_wrong_filename(self) -> None:
        payload = {
            "source_text_file": "other.txt",
            "summary_markdown": "# Summary\nHello\n",
            "notes": "",
        }
        with self.assertRaises(ValueError):
            validate_generator_payload(payload, "session.txt")


if __name__ == "__main__":
    unittest.main()
