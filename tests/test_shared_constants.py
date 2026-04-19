from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from file_name_randomizer.constants import RUBRIC_KEYS


class SharedConstantsTests(unittest.TestCase):
    def test_rubric_keys_are_stable(self) -> None:
        self.assertEqual(
            RUBRIC_KEYS,
            (
                "accuracy",
                "completeness",
                "clarity",
                "faithfulness_to_source_prompt",
                "actionability",
            ),
        )


if __name__ == "__main__":
    unittest.main()
