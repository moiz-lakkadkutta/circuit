"""Tests for the benchmark table formatter."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "benchmark"))

from run_benchmark import format_header, format_table  # noqa: E402


def test_table_counts_silent_lies_per_slice_and_overall():
    rows = [
        {"file": "a.cir", "slice": "curated", "ngspice_exit": 0,
         "spiceguard": "TRUSTWORTHY", "silent_lie": False},
        {"file": "b.cir", "slice": "curated", "ngspice_exit": 0,
         "spiceguard": "SUSPECT", "silent_lie": True},
        {"file": "c.cir", "slice": "ai_generated", "ngspice_exit": 1,
         "spiceguard": "FAILED", "silent_lie": False},
    ]
    out = format_table(rows)
    assert "| b.cir | 0 (looks fine) | SUSPECT | YES |" in out
    # Curated slice: a.cir + b.cir both exit-0, only b.cir is a silent lie.
    assert "1 of 2 exit-0 runs (50%) were silently untrustworthy." in out
    # Overall total across both slices (ai_generated's c.cir is exit-1, not
    # counted in the exit-0 denominator) -> same 1 of 2 overall.
    assert "1 of 2 exit-0 runs (50%) were silently untrustworthy across all slices." in out
    assert "Curated corpus" in out
    assert "AI-generated corpus" in out


def test_table_handles_zero_exit_zero_runs():
    rows = [{"file": "c.cir", "slice": "curated", "ngspice_exit": 1,
             "spiceguard": "FAILED", "silent_lie": False}]
    out = format_table(rows)
    assert "0 of 0" in out
    # No AI-generated rows -> no AI-generated section, no zero-division blowup.
    assert "AI-generated corpus" not in out


def test_header_states_mode_and_repro_command():
    header = format_header(version="9.9.9")
    assert "9.9.9" in header
    assert "no_exec=False" in header
    assert "trusted first-party content" in header
    assert "PYTHONPATH=src python3 benchmark/run_benchmark.py" in header
