# Summary Evaluation Harness

A small Python package for running blinded summary-generation experiments across multiple models.

It supports four stages:

1. Generate summaries from a source `.txt` file with isolated model runs.
2. Remove authorship traces from summary contents and shuffle model labels in filenames.
3. Judge the shuffled summaries with isolated evaluator runs using a shared rubric.
4. Analyze the results with reproducible statistics, agreement metrics, and a Markdown report.

## What It Does

- Runs generators and judges in isolated temporary workspaces.
- Embeds prompt inputs directly into model prompts to reduce tool and permission variance.
- Validates generator and judge outputs against strict JSON contracts.
- Produces blinded review sets with mapping files for later recovery.
- Computes descriptive statistics, permutation-test p-values, bootstrap confidence intervals, FDR-adjusted significance, judge agreement metrics, and a report.
- Keeps the analysis reproducible for a fixed seed.

## Repository Layout

```text
src/summary_eval_harness/
  cli/                  Thin CLI entry points
  templates/            Prompt templates
  analysis/             Loaders, stats, correction, reporting
  shuffle.py            Blinding and filename shuffling
  generator_runner.py   Summary generation runner
  judge_runner.py       Judge execution runner

tests/                  Unit and integration tests
```

Top-level scripts are compatibility wrappers:

- `generate_summaries.py`
- `shuffle_model_names.py`
- `run_judge_evaluations.py`
- `analyze_judge_results.py`

## Requirements

- Python `>= 3.11`
- Model CLIs configured in generator and judge config JSON files

## Core Inputs

- Source directory for generation:
  - exactly one `.txt` file
- Source directory for shuffling:
  - exactly one `.txt` file
  - one or more summary `.md` files named like `<prefix>_summary__<model>.md`
- Generator config JSON
- Judge config JSON
- Generation rubric
- Evaluation rubric

Example configs:

- [judges.example.json](./judges.example.json)
- [examples/](./examples/)

Example rubrics:

- [generation_rubric_template.md](./generation_rubric_template.md)
- [rubric_template.md](./rubric_template.md)

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

You also need access to the model CLI(s) referenced in your generator and judge config files.

## Config Notes

The example generator and judge configs assume an `opencode` executable is available on your `PATH`.
If your local install uses a different path or wrapper, edit the `command` arrays in the JSON files accordingly.
`opencode` is only the example runner used in this repo. The config format is generic, so you can replace those commands with any compatible CLI invocation.

## Typical Workflow

### 1. Generate summaries

```bash
python3 generate_summaries.py /path/to/source_dir \
  --generators-config ./examples/generators.opencode.example.json \
  --rubric-file ./generation_rubric_template.md \
  --outputs-dir /path/to/generated \
  --work-root /path/to/generator_work
```

This writes summary markdown files and a generation run log.

### 2. Create blinded review sets

Copy the original `.txt` file into the generated directory if needed, then:

```bash
python3 shuffle_model_names.py /path/to/generated \
  --count 10 \
  --seed 42
```

This writes:

- `clean/`
- `review_sets/`
- a mapping JSON in the current working directory

### 3. Run judges

```bash
python3 run_judge_evaluations.py /path/to/generated/review_sets \
  --judges-config ./judges.example.json \
  --rubric-file ./rubric_template.md \
  --results-dir /path/to/results \
  --work-root /path/to/judge_work
```

This writes one JSON result per judge per review set plus a run log.

### 4. Analyze results

```bash
python3 analyze_judge_results.py /path/to/mapping.json /path/to/results \
  --output-dir /path/to/analysis \
  --permutations 5000 \
  --seed 42 \
  --alpha 0.05
```

This writes:

- `joined_results.csv`
- `analysis_summary.json`
- `control_vs_deranged.csv`
- `criterion_control_vs_deranged.csv`
- `displayed_model_effects.csv`
- `comparison_table.csv`
- `judge_agreement_pairwise.csv`
- `analysis_report.md`

## Design Notes

- Generation and judging are intentionally separate workflows.
- The runner writes files; models return structured stdout.
- Input files are embedded directly into prompts for more stable cross-model behavior.
- Analysis uses deterministic RNG streams derived from the root seed for reproducibility.
- Multiple-comparison correction uses Benjamini-Hochberg FDR.

## Testing

Run the test suite with:

```bash
python3 -m unittest discover -s tests -v
```

The test suite covers:

- shared constants
- filename parsing and shuffling behavior
- generator and judge stdout parsing/validation
- reproducible statistical behavior
- small integration paths for generation and analysis

## Current Scope

This project is intentionally narrow:

- summary generation
- summary blinding
- rubric-based judging
- statistical analysis

It is meant to be small, reproducible, and easy to adapt for similar evaluation workflows.
