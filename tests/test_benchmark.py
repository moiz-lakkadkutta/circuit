"""Tests for the benchmark table formatter."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "benchmark"))

from run_benchmark import format_table  # noqa: E402


def test_table_counts_silent_lies():
    rows = [
        {"file": "a.cir", "ngspice_exit": 0, "spiceguard": "TRUSTWORTHY", "silent_lie": False},
        {"file": "b.cir", "ngspice_exit": 0, "spiceguard": "SUSPECT", "silent_lie": True},
        {"file": "c.cir", "ngspice_exit": 1, "spiceguard": "FAILED", "silent_lie": False},
    ]
    out = format_table(rows)
    assert "| b.cir | 0 (looks fine) | SUSPECT | YES |" in out
    assert "1 of 2 exit-0 runs (50%) were silently untrustworthy" in out


def test_table_handles_zero_exit_zero_runs():
    rows = [{"file": "c.cir", "ngspice_exit": 1, "spiceguard": "FAILED", "silent_lie": False}]
    out = format_table(rows)
    assert "0 of 0" in out
