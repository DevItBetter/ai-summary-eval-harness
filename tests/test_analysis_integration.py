from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from file_name_randomizer.analysis.correction import apply_bh_fdr
from file_name_randomizer.analysis.loader import index_mapping_sets, load_joined_rows, load_mapping
from file_name_randomizer.analysis.reporting import build_markdown_report, prepare_output_dir, write_flat_csv
from file_name_randomizer.analysis.stats import comparison_table, control_vs_deranged, criterion_control_vs_deranged, descriptive_summary, judge_agreement, label_effects


class AnalysisIntegrationTests(unittest.TestCase):
    def test_loader_to_report_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results = root / "results" / "judge_a"
            results.mkdir(parents=True)
            mapping = {
                "review_sets": [
                    {
                        "set_name": "000",
                        "condition": "original",
                        "fixed_points": 2,
                        "files": [
                            {"source_file": "a.md", "true_model": "alpha", "displayed_model": "alpha", "output_file": "x.md"},
                            {"source_file": "b.md", "true_model": "beta", "displayed_model": "beta", "output_file": "y.md"},
                        ],
                    },
                    {
                        "set_name": "001",
                        "condition": "deranged",
                        "fixed_points": 0,
                        "files": [
                            {"source_file": "a.md", "true_model": "alpha", "displayed_model": "beta", "output_file": "y.md"},
                            {"source_file": "b.md", "true_model": "beta", "displayed_model": "alpha", "output_file": "x.md"},
                        ],
                    },
                ]
            }
            (root / "mapping.json").write_text(json.dumps(mapping), encoding="utf-8")
            payloads = {
                "000.json": {
                    "judge_name": "judge_a",
                    "set_name": "000",
                    "evaluated_at": None,
                    "source_text_file": "prompt.txt",
                    "rubric_version": "v1",
                    "results": [
                        {"filename": "x.md", "scores": {"accuracy": 4, "completeness": 4, "clarity": 4, "faithfulness_to_source_prompt": 4, "actionability": 4}, "overall_score": 4, "strengths": [], "weaknesses": [], "notes": ""},
                        {"filename": "y.md", "scores": {"accuracy": 3, "completeness": 3, "clarity": 3, "faithfulness_to_source_prompt": 3, "actionability": 3}, "overall_score": 3, "strengths": [], "weaknesses": [], "notes": ""},
                    ],
                    "ranking": [{"filename": "x.md", "rank": 1}, {"filename": "y.md", "rank": 2}],
                    "overall_notes": "",
                },
                "001.json": {
                    "judge_name": "judge_a",
                    "set_name": "001",
                    "evaluated_at": None,
                    "source_text_file": "prompt.txt",
                    "rubric_version": "v1",
                    "results": [
                        {"filename": "x.md", "scores": {"accuracy": 2, "completeness": 2, "clarity": 2, "faithfulness_to_source_prompt": 2, "actionability": 2}, "overall_score": 2, "strengths": [], "weaknesses": [], "notes": ""},
                        {"filename": "y.md", "scores": {"accuracy": 5, "completeness": 5, "clarity": 5, "faithfulness_to_source_prompt": 5, "actionability": 5}, "overall_score": 5, "strengths": [], "weaknesses": [], "notes": ""},
                    ],
                    "ranking": [{"filename": "y.md", "rank": 1}, {"filename": "x.md", "rank": 2}],
                    "overall_notes": "",
                },
            }
            for name, payload in payloads.items():
                (results / name).write_text(json.dumps(payload), encoding="utf-8")

            rows = load_joined_rows(index_mapping_sets(load_mapping(root / "mapping.json")), root / "results")
            out = root / "out"
            prepare_output_dir(out, True)
            write_flat_csv(rows, out / "joined.csv")
            control = apply_bh_fdr(control_vs_deranged(rows, 100, 42), 0.05)
            criteria = apply_bh_fdr(criterion_control_vs_deranged(rows, 100, 42), 0.05)
            labels = apply_bh_fdr(label_effects(rows, 100, 42), 0.05)
            summary = {
                "permutations": 100,
                "seed": 42,
                "alpha": 0.05,
                "descriptive_summary": descriptive_summary(rows),
                "control_vs_deranged": control,
                "criterion_control_vs_deranged": criteria,
                "displayed_model_effects": labels,
                "comparison_table": apply_bh_fdr(comparison_table(control, labels, criteria), 0.05),
                "judge_agreement": judge_agreement(rows),
            }
            report = build_markdown_report(summary)
            self.assertIn("# Judge Analysis Report", report)
            self.assertIn("## Judge Agreement", report)
            self.assertTrue((out / "joined.csv").exists())


if __name__ == "__main__":
    unittest.main()
