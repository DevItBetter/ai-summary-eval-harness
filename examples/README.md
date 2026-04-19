# Example Configs

This directory contains example generator and judge configs for different CLI runners.

The JSON shape is the same for both generators and judges:

- `name`
- `capture_mode`
- `command`

The separation is logical, not structural.

- generator configs are used with `generate_summaries.py`
- judge configs are used with `run_judge_evaluations.py`

If you want the same models to author summaries and later judge them, you can reuse the same harness family in both places.

## Generators

- `generators/generators.opencode.example.json`
- `generators/generators.claude.example.json`
- `generators/generators.codex.example.json`
- `generators/generators.gemini.example.json`
- `generators/generators.copilot.example.json`

## Judges

- `judges/judges.opencode.example.json`
- `judges/judges.claude.example.json`
- `judges/judges.codex.example.json`
- `judges/judges.gemini.example.json`
- `judges/judges.copilot.example.json`
