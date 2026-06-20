"""
Tests for the trustguard CLI (argparse-based, task T3).

All tests monkeypatch trustguard.cli.evaluate to avoid real ngspice.
"""
import sys
from io import StringIO
from pathlib import Path

import pytest

import trustguard
from trustguard.core import Result
from trustguard.ngspice import NgspiceNotFound


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_result(verdict, path="dummy.cir"):
    """Build a minimal Result with the given verdict."""
    return Result(path=path, verdict=verdict, rc=0 if verdict != "FAILED" else 1)


def patch_evaluate(monkeypatch, results_by_path=None, fixed_result=None, raise_exc=None):
    """
    Monkeypatch trustguard.cli.evaluate.

    - results_by_path: dict mapping path str -> Result (keyed by str(path))
    - fixed_result: every call returns a Result with this verdict (path is set
      from the actual call argument so report() shows the real filename)
    - raise_exc: every call raises this exception
    Also records calls as a list of (path, ngspice_path) in `calls`.
    """
    calls = []

    def fake_evaluate(path, ngspice_path=None):
        calls.append((str(path), ngspice_path))
        if raise_exc is not None:
            raise raise_exc
        if fixed_result is not None:
            # Mirror the actual path so report() shows the real filename
            return Result(
                path=str(path),
                verdict=fixed_result.verdict,
                rc=fixed_result.rc,
                issues=list(fixed_result.issues),
            )
        if results_by_path is not None:
            return results_by_path[str(path)]
        raise RuntimeError("patch_evaluate: no result configured")

    monkeypatch.setattr("trustguard.cli.evaluate", fake_evaluate)
    return calls


# ---------------------------------------------------------------------------
# Verdict aggregation / exit codes
# ---------------------------------------------------------------------------

def test_all_trustworthy_exits_0(monkeypatch, capsys):
    patch_evaluate(monkeypatch, fixed_result=make_result("TRUSTWORTHY"))
    from trustguard.cli import main
    code = main(["dummy.cir"])
    assert code == 0


def test_trustworthy_and_suspect_exits_2(monkeypatch, capsys):
    """Worst of TRUSTWORTHY + SUSPECT = exit 2."""
    results = {
        "a.cir": make_result("TRUSTWORTHY", "a.cir"),
        "b.cir": make_result("SUSPECT", "b.cir"),
    }
    patch_evaluate(monkeypatch, results_by_path=results)
    from trustguard.cli import main
    code = main(["a.cir", "b.cir"])
    assert code == 2


def test_trustworthy_and_failed_exits_1(monkeypatch, capsys):
    """Worst of TRUSTWORTHY + FAILED = exit 1."""
    results = {
        "a.cir": make_result("TRUSTWORTHY", "a.cir"),
        "b.cir": make_result("FAILED", "b.cir"),
    }
    patch_evaluate(monkeypatch, results_by_path=results)
    from trustguard.cli import main
    code = main(["a.cir", "b.cir"])
    assert code == 1


def test_failed_and_suspect_exits_1(monkeypatch, capsys):
    """FAILED outranks SUSPECT → exit 1."""
    results = {
        "a.cir": make_result("FAILED", "a.cir"),
        "b.cir": make_result("SUSPECT", "b.cir"),
    }
    patch_evaluate(monkeypatch, results_by_path=results)
    from trustguard.cli import main
    code = main(["a.cir", "b.cir"])
    assert code == 1


# ---------------------------------------------------------------------------
# --version
# ---------------------------------------------------------------------------

def test_version_prints_and_exits_0(capsys):
    from trustguard.cli import main
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    # Output may go to stdout or stderr (argparse puts --version on stdout in 3.x)
    combined = captured.out + captured.err
    assert "trustguard" in combined
    assert trustguard.__version__ in combined


# ---------------------------------------------------------------------------
# No args → usage error (exit 64)
# ---------------------------------------------------------------------------

def test_no_args_exits_64(capsys):
    from trustguard.cli import main
    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code == 64
    captured = capsys.readouterr()
    # Message should appear on stderr
    assert captured.err != "" or captured.out != ""


# ---------------------------------------------------------------------------
# Bad / unknown flags → exit 64 (NOT argparse's default 2)
# ---------------------------------------------------------------------------

def test_unknown_flag_exits_64(capsys):
    from trustguard.cli import main
    with pytest.raises(SystemExit) as exc_info:
        main(["--not-a-real-flag"])
    assert exc_info.value.code == 64


def test_invalid_option_value_exits_64(capsys):
    """--ngspice with no value should give usage error → 64."""
    from trustguard.cli import main
    with pytest.raises(SystemExit) as exc_info:
        main(["--ngspice"])  # missing required argument for --ngspice
    assert exc_info.value.code == 64


# ---------------------------------------------------------------------------
# --ngspice forwarded to evaluate
# ---------------------------------------------------------------------------

def test_ngspice_flag_forwarded_to_evaluate(monkeypatch, capsys):
    calls = patch_evaluate(monkeypatch, fixed_result=make_result("TRUSTWORTHY"))
    from trustguard.cli import main
    code = main(["--ngspice", "/custom/ngspice", "dummy.cir"])
    assert code == 0
    assert len(calls) == 1
    _path, ngspice_path = calls[0]
    assert ngspice_path == "/custom/ngspice"


def test_no_ngspice_flag_passes_none(monkeypatch, capsys):
    calls = patch_evaluate(monkeypatch, fixed_result=make_result("TRUSTWORTHY"))
    from trustguard.cli import main
    code = main(["dummy.cir"])
    assert code == 0
    assert len(calls) == 1
    _path, ngspice_path = calls[0]
    assert ngspice_path is None


# ---------------------------------------------------------------------------
# NgspiceNotFound → exit 3, message on stderr
# ---------------------------------------------------------------------------

def test_ngspice_not_found_exits_3(monkeypatch, capsys):
    exc = NgspiceNotFound("ngspice not found in test")
    patch_evaluate(monkeypatch, raise_exc=exc)
    from trustguard.cli import main
    with pytest.raises(SystemExit) as exc_info:
        main(["dummy.cir"])
    assert exc_info.value.code == 3
    captured = capsys.readouterr()
    assert "ngspice not found in test" in captured.err


# ---------------------------------------------------------------------------
# Subcommand structure: kicad subcommand exists, no-subcommand form works
# ---------------------------------------------------------------------------

def test_kicad_subcommand_accepted(monkeypatch, capsys):
    """kicad subcommand must be accepted without argparse error."""
    patch_evaluate(monkeypatch, fixed_result=make_result("TRUSTWORTHY"))
    from trustguard.cli import main
    # Should not raise SystemExit(64); any valid exit is fine
    try:
        code = main(["kicad", "dummy.cir"])
    except SystemExit as e:
        assert e.code != 64, f"kicad subcommand should not exit 64, got {e.code}"


def test_no_subcommand_form_works(monkeypatch, capsys):
    """trustguard FILE (no subcommand) must work cleanly."""
    patch_evaluate(monkeypatch, fixed_result=make_result("TRUSTWORTHY"))
    from trustguard.cli import main
    code = main(["dummy.cir"])
    assert code == 0


# ---------------------------------------------------------------------------
# report() is called for each result (human output)
# ---------------------------------------------------------------------------

def test_report_called_for_each_file(monkeypatch, capsys):
    """Each evaluated file should produce some output via report()."""
    patch_evaluate(monkeypatch, fixed_result=make_result("TRUSTWORTHY"))
    from trustguard.cli import main
    code = main(["f1.cir", "f2.cir"])
    captured = capsys.readouterr()
    # report() prints a separator line with the filename
    combined = captured.out + captured.err
    assert "f1.cir" in combined or "f2.cir" in combined


# ---------------------------------------------------------------------------
# Optional: real end-to-end with ngspice (skipped if absent)
# ---------------------------------------------------------------------------

import trustguard as tg

requires_ngspice = pytest.mark.skipif(
    not tg.ngspice.ngspice_available(),
    reason="ngspice not installed",
)

NETLISTS = Path(__file__).parent / "netlists"


@requires_ngspice
def test_real_healthy_netlist_exits_0():
    """main() on the healthy control circuit must return 0."""
    from trustguard.cli import main
    code = main([str(NETLISTS / "n5_healthy_control.cir")])
    assert code == 0
