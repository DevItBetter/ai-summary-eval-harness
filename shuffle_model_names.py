#!/usr/bin/env python3
"""Compatibility wrapper for the packaged shuffle CLI."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from file_name_randomizer.cli.shuffle_model_names import main


if __name__ == "__main__":
    raise SystemExit(main())
