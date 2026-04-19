"""Shared dataclasses."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SummaryFile:
    path: Path
    filename: str
    model_name: str


@dataclass(frozen=True)
class JudgeConfig:
    name: str
    command: list[str]
    env: dict[str, str]
    capture_mode: str


@dataclass(frozen=True)
class GeneratorConfig:
    name: str
    command: list[str]
    env: dict[str, str]
    capture_mode: str


@dataclass(frozen=True)
class JoinedRow:
    judge_name: str
    set_name: str
    condition: str
    fixed_points: int
    filename: str
    source_file: str
    true_model: str
    displayed_model: str
    rank: int
    overall_score: float
    scores: dict[str, int]
