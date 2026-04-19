from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from summary_eval_harness.analysis.correction import apply_bh_fdr
from summary_eval_harness.analysis.stats import control_vs_deranged, criterion_control_vs_deranged, label_effects
from summary_eval_harness.types import JoinedRow


def sample_rows() -> list[JoinedRow]:
    return [
        JoinedRow("judge_a", "000", "original", 2, "x.md", "a.md", "alpha", "alpha", 1, 4.0, {"accuracy": 4, "completeness": 4, "clarity": 4, "faithfulness_to_source_prompt": 4, "actionability": 4}),
        JoinedRow("judge_a", "000", "original", 2, "y.md", "b.md", "beta", "beta", 2, 3.0, {"accuracy": 3, "completeness": 3, "clarity": 3, "faithfulness_to_source_prompt": 3, "actionability": 3}),
        JoinedRow("judge_a", "001", "deranged", 0, "x.md", "b.md", "beta", "alpha", 2, 2.0, {"accuracy": 2, "completeness": 2, "clarity": 2, "faithfulness_to_source_prompt": 2, "actionability": 2}),
        JoinedRow("judge_a", "001", "deranged", 0, "y.md", "a.md", "alpha", "beta", 1, 5.0, {"accuracy": 5, "completeness": 5, "clarity": 5, "faithfulness_to_source_prompt": 5, "actionability": 5}),
    ]


class AnalysisStatsTests(unittest.TestCase):
    def test_control_vs_deranged_is_reproducible(self) -> None:
        rows = sample_rows()
        first = control_vs_deranged(rows, 100, 42)
        second = control_vs_deranged(rows, 100, 42)
        self.assertEqual(first, second)

    def test_family_order_does_not_change_results(self) -> None:
        rows = sample_rows()
        first = control_vs_deranged(rows, 100, 42)
        _label = label_effects(rows, 100, 42)
        second = control_vs_deranged(rows, 100, 42)
        self.assertEqual(first, second)
        self.assertTrue(criterion_control_vs_deranged(rows, 100, 42))

    def test_apply_bh_fdr_adds_expected_fields(self) -> None:
        rows = apply_bh_fdr([{"p_value": 0.01}, {"p_value": 0.2}], 0.05)
        self.assertIn("p_value_fdr", rows[0])
        self.assertIn("is_significant_raw", rows[0])
        self.assertIn("is_significant_fdr", rows[0])


if __name__ == "__main__":
    unittest.main()
