# -*- coding: utf-8 -*-
"""Make src/ importable for the tests (benchmark_v3, cross_pipeline)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
