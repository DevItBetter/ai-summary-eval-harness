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

from file_name_randomizer.generator_runner import load_generators, run_all_generators


class GeneratorIntegrationTests(unittest.TestCase):
    def test_run_all_generators_with_stdout_json_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "input"
            input_dir.mkdir()
            (input_dir / "session.txt").write_text("hello world\n", encoding="utf-8")
            config = root / "generators.json"
            config.write_text(
                json.dumps(
                    [
                        {
                            "name": "fake",
                            "capture_mode": "stdout_json",
                            "command": [
                                "python3",
                                "-c",
                                "import json; print(json.dumps({'source_text_file':'session.txt','summary_markdown':'# Summary\\nhello\\n','notes':''}))",
                            ],
                        }
                    ]
                ),
                encoding="utf-8",
            )
            rubric = root / "rubric.md"
            rubric.write_text("rubric\n", encoding="utf-8")
            run_log = run_all_generators(
                input_dir=input_dir,
                generators=load_generators(config),
                rubric_file=rubric,
                prompt_template_path=ROOT / "src" / "file_name_randomizer" / "templates" / "generator_prompt.txt",
                outputs_dir=root / "outputs",
                work_root=root / "work",
                timeout_seconds=30,
                force=True,
            )
            self.assertEqual(len(run_log["runs"]), 1)
            self.assertTrue(run_log["runs"][0]["output_written"])
            self.assertTrue((root / "outputs" / "session_summary__fake.md").exists())


if __name__ == "__main__":
    unittest.main()
