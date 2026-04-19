from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from file_name_randomizer.shuffle import find_source_files, sample_derangements, sanitize_text


class ShuffleTests(unittest.TestCase):
    def test_find_source_files_uses_txt_stem_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "session.txt").write_text("prompt\n", encoding="utf-8")
            (root / "session_summary__alpha.md").write_text("a\n", encoding="utf-8")
            (root / "session_summary__beta.md").write_text("b\n", encoding="utf-8")
            txt_file, prefix, summaries = find_source_files(root)
            self.assertEqual(txt_file.name, "session.txt")
            self.assertEqual(prefix, "session")
            self.assertEqual([summary.model_name for summary in summaries], ["alpha", "beta"])

    def test_sanitize_text_removes_sequential_model_mentions(self) -> None:
        text = "Written by claude sonnett 4 6. Another claude-sonnett-4-6 mention."
        cleaned = sanitize_text(text, "claude-sonnett-4-6")
        self.assertNotIn("claude", cleaned.lower())
        self.assertNotIn("sonnett", cleaned.lower())

    def test_sample_derangements_have_zero_fixed_points(self) -> None:
        items = ["a", "b", "c"]
        derangements = sample_derangements(items, 2, 7)
        self.assertEqual(len(derangements), 2)
        for assignment in derangements:
            self.assertTrue(all(original != shuffled for original, shuffled in zip(items, assignment)))


if __name__ == "__main__":
    unittest.main()
