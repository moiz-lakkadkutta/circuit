"""
Tests for trustguard.kicad — KiCad post-simulation hook (Task T5, feature C).

Pure preflight tests require no ngspice.
Integration tests (check_kicad_netlist, CLI end-to-end) are gated by
the same `requires_ngspice` skip marker used across the suite.
"""
import sys
from io import StringIO
from pathlib import Path

import pytest

import trustguard as tg
from trustguard.kicad import kicad_preflight

NET = Path(__file__).parent / "netlists"
RW = NET / "realworld"

requires_ngspice = pytest.mark.skipif(
    not tg.ngspice.ngspice_available(),
    reason="ngspice not installed",
)


# ---------------------------------------------------------------------------
# Pure preflight: ground-not-zero detection
# ---------------------------------------------------------------------------

def test_preflight_gnd_no_zero():
    """GND net with no node 0 → kicad_ground_not_zero WARN."""
    text = (
        ".title GND test\n"
        "V1 VIN GND DC 5\n"
        "R1 VIN OUT 1k\n"
        "R2 OUT GND 1k\n"
        ".op\n"
        ".end\n"
    )
    issues = kicad_preflight(text)
    codes = {i.code for i in issues}
    assert "kicad_ground_not_zero" in codes, f"Issues: {issues}"


def test_preflight_gnda_no_zero():
    """GNDA net with no node 0 → kicad_ground_not_zero WARN."""
    text = (
        ".title GNDA test\n"
        "V1 VIN GNDA DC 5\n"
        "R1 VIN OUT 1k\n"
        "R2 OUT GNDA 1k\n"
        ".op\n"
        ".end\n"
    )
    issues = kicad_preflight(text)
    codes = {i.code for i in issues}
    assert "kicad_ground_not_zero" in codes, f"Issues: {issues}"


def test_preflight_vss_no_zero():
    """VSS net with no node 0 → kicad_ground_not_zero WARN."""
    text = (
        ".title VSS test\n"
        "V1 VIN VSS DC 5\n"
        "R1 VIN OUT 1k\n"
        "R2 OUT VSS 1k\n"
        ".op\n"
        ".end\n"
    )
    issues = kicad_preflight(text)
    codes = {i.code for i in issues}
    assert "kicad_ground_not_zero" in codes, f"Issues: {issues}"


def test_preflight_0v_no_zero():
    """0V net with no node 0 → kicad_ground_not_zero WARN."""
    text = (
        ".title 0V test\n"
        "V1 VIN 0V DC 5\n"
        "R1 VIN OUT 1k\n"
        "R2 OUT 0V 1k\n"
        ".op\n"
        ".end\n"
    )
    issues = kicad_preflight(text)
    codes = {i.code for i in issues}
    assert "kicad_ground_not_zero" in codes, f"Issues: {issues}"


def test_preflight_zero_present_no_finding():
    """Node 0 already present → no kicad_ground_not_zero finding."""
    text = (
        ".title node 0 test\n"
        "V1 VIN 0 DC 5\n"
        "R1 VIN OUT 1k\n"
        "R2 OUT 0 1k\n"
        ".op\n"
        ".end\n"
    )
    issues = kicad_preflight(text)
    codes = {i.code for i in issues}
    assert "kicad_ground_not_zero" not in codes, f"Issues: {issues}"


def test_preflight_both_zero_and_gnd_no_finding():
    """Node 0 AND GND present → no finding (0 satisfies ngspice)."""
    text = (
        ".title mixed test\n"
        "V1 VIN 0 DC 5\n"
        "R1 VIN GND 1k\n"
        "R2 GND 0 1k\n"
        ".op\n"
        ".end\n"
    )
    issues = kicad_preflight(text)
    codes = {i.code for i in issues}
    assert "kicad_ground_not_zero" not in codes, f"Issues: {issues}"


def test_preflight_finding_severity_is_warn():
    """kicad_ground_not_zero must have WARN severity."""
    text = (
        ".title severity test\n"
        "V1 VIN GND DC 5\n"
        "R1 VIN GND 1k\n"
        ".op\n"
        ".end\n"
    )
    issues = kicad_preflight(text)
    for i in issues:
        if i.code == "kicad_ground_not_zero":
            assert i.severity == "WARN", f"Expected WARN, got {i.severity}"
            return
    pytest.fail("kicad_ground_not_zero issue not found")


def test_preflight_finding_message_contains_guidance():
    """kicad_ground_not_zero message must mention node 0 and KiCad remediation."""
    text = (
        ".title message test\n"
        "V1 VIN GND DC 5\n"
        "R1 VIN GND 1k\n"
        ".op\n"
        ".end\n"
    )
    issues = kicad_preflight(text)
    for i in issues:
        if i.code == "kicad_ground_not_zero":
            msg = i.message.lower()
            # Must mention node 0 and some remediation guidance
            assert "0" in msg, f"Message must mention node 0: {i.message}"
            assert any(w in msg for w in ("kicad", "gnd", "map", "spice", "pwr")), (
                f"Message must contain KiCad-specific guidance: {i.message}"
            )
            return
    pytest.fail("kicad_ground_not_zero issue not found")


def test_preflight_empty_netlist_no_crash():
    """Empty or title-only netlist must not raise, must return empty list."""
    assert kicad_preflight("") == []
    assert kicad_preflight(".title nothing\n.end\n") == []


def test_preflight_kicad_gnd_fixture():
    """kicad_gnd.cir fixture must trigger kicad_ground_not_zero."""
    text = (RW / "kicad_gnd.cir").read_text()
    issues = kicad_preflight(text)
    codes = {i.code for i in issues}
    assert "kicad_ground_not_zero" in codes, f"Issues: {issues}"


def test_preflight_kicad_subckt_fixture_no_finding():
    """kicad_subckt.cir has node 0 → no kicad_ground_not_zero."""
    text = (RW / "kicad_subckt.cir").read_text()
    issues = kicad_preflight(text)
    codes = {i.code for i in issues}
    assert "kicad_ground_not_zero" not in codes, f"Issues: {issues}"


# ---------------------------------------------------------------------------
# check_kicad_netlist: integration (skip if ngspice absent)
# ---------------------------------------------------------------------------

@requires_ngspice
def test_check_kicad_netlist_subckt_trustworthy():
    """kicad_subckt.cir via check_kicad_netlist must yield TRUSTWORTHY."""
    from trustguard.kicad import check_kicad_netlist
    result = check_kicad_netlist(str(RW / "kicad_subckt.cir"))
    assert result.verdict == "TRUSTWORTHY", (
        f"Expected TRUSTWORTHY, got {result.verdict}. Issues: {result.issues}"
    )


@requires_ngspice
def test_check_kicad_netlist_gnd_suspect():
    """kicad_gnd.cir via check_kicad_netlist must be SUSPECT (preflight WARN)."""
    from trustguard.kicad import check_kicad_netlist
    result = check_kicad_netlist(str(RW / "kicad_gnd.cir"))
    assert result.verdict in ("SUSPECT", "FAILED"), (
        f"Expected SUSPECT/FAILED, got {result.verdict}"
    )
    codes = {i.code for i in result.issues}
    assert "kicad_ground_not_zero" in codes, f"Issues: {result.issues}"


# ---------------------------------------------------------------------------
# CLI kicad subcommand — stdin ('-') support (monkeypatched)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# NICE-TO-HAVE: exact-token matching — substring ground names must not fire
# ---------------------------------------------------------------------------

def test_preflight_substring_ground_names_no_finding():
    """Net names that merely CONTAIN a ground substring (GNDPLANE, AGND_SENSE)
    must NOT trigger kicad_ground_not_zero — matching is exact token only."""
    text = (
        ".title substring ground names\n"
        "V1 VIN GNDPLANE DC 5\n"
        "R1 VIN AGND_SENSE 1k\n"
        "R2 AGND_SENSE GNDPLANE 1k\n"
        ".op\n"
        ".end\n"
    )
    issues = kicad_preflight(text)
    codes = {i.code for i in issues}
    assert "kicad_ground_not_zero" not in codes, (
        "Substring-only ground names must not fire kicad_ground_not_zero. "
        f"Issues: {issues}"
    )


# ---------------------------------------------------------------------------
# SHOULD-FIX: check_kicad_netlist must preflight the CONVERTED text
# ---------------------------------------------------------------------------

def test_check_kicad_netlist_uses_converted_text(monkeypatch, tmp_path):
    """check_kicad_netlist must run kicad_preflight on the text returned by
    formats.load_as_netlist (the converted/normalised netlist), NOT on the
    raw bytes from p.read_text().

    The test simulates a convertible input by:
    - Writing a raw file with node 0 (no GND issue → preflight silent on raw).
    - Monkey-patching formats.load_as_netlist to return a text that uses GND
      and lacks node 0 (→ preflight should fire on the converted text).
    - Monkey-patching evaluate so no ngspice is needed.

    If the buggy path (p.read_text()) is used, the finding is absent;
    if the fixed path (load_as_netlist) is used, the finding is present.
    """
    from trustguard.core import Result
    from trustguard.kicad import check_kicad_netlist

    # Raw file: uses node 0 — preflight would NOT fire on this text.
    raw_text = (
        ".title raw no gnd issue\n"
        "V1 VIN 0 DC 5\n"
        "R1 VIN 0 1k\n"
        ".op\n"
        ".end\n"
    )
    # Converted text: GND net, no node 0 — preflight SHOULD fire on this.
    converted_text = (
        "* converted by trustguard (mock)\n"
        "V1 VIN GND DC 5\n"
        "R1 VIN GND 1k\n"
        ".op\n"
        ".end\n"
    )

    netlist_file = tmp_path / "test.cir"
    netlist_file.write_text(raw_text)

    # Patch load_as_netlist to return converted_text instead of raw_text.
    monkeypatch.setattr(
        "trustguard.formats.load_as_netlist",
        lambda path: (converted_text, "mock-converted", []),
    )
    # Patch evaluate so no ngspice binary is needed.
    monkeypatch.setattr(
        "trustguard.core.evaluate",
        lambda path, ngspice_path=None: Result(
            path=path, verdict="TRUSTWORTHY", rc=0,
        ),
    )

    result = check_kicad_netlist(str(netlist_file))
    codes = {i.code for i in result.issues}
    assert "kicad_ground_not_zero" in codes, (
        "Expected kicad_ground_not_zero when preflight uses converted text "
        f"(with GND alias, no node 0). Issues: {result.issues}"
    )


# ---------------------------------------------------------------------------
# CLI kicad subcommand — stdin ('-') support (monkeypatched)
# ---------------------------------------------------------------------------

def test_kicad_cli_stdin_gnd_preflight(monkeypatch, capsys):
    """trustguard kicad - reads stdin; GND fixture triggers kicad_ground_not_zero SUSPECT.

    The kicad CLI branch now delegates to kicad.check_kicad_netlist, which
    lazily imports evaluate from trustguard.core.  Patch trustguard.core.evaluate
    (not trustguard.cli.evaluate) to avoid running real ngspice.
    """
    text = (RW / "kicad_gnd.cir").read_text()
    monkeypatch.setattr("sys.stdin", StringIO(text))

    # Mock evaluate via the core module so check_kicad_netlist's lazy import
    # picks it up; return a clean TRUSTWORTHY base so kicad_preflight determines
    # the final verdict.
    from trustguard.core import Result
    monkeypatch.setattr(
        "trustguard.core.evaluate",
        lambda path, ngspice_path=None: Result(path=path, verdict="TRUSTWORTHY", rc=0),
    )

    from trustguard.cli import main
    code = main(["kicad", "-"])
    assert code == 2, f"Expected exit 2 (SUSPECT), got {code}"
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "kicad_ground_not_zero" in combined, (
        f"Expected kicad_ground_not_zero in output: {combined}"
    )
