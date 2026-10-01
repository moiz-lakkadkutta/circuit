"""Tests for no-exec mode wiring through core and CLI."""
import pytest

from spiceguard import core
from spiceguard.checks import Issue


@pytest.fixture
def fake_ngspice(monkeypatch):
    """Capture the text handed to ngspice; pretend the sim succeeded."""
    captured = {}

    def fake_run(text, ngspice_path=None, cwd=None):
        captured["text"] = text
        return 0, "No. of Data Rows : 1\n"

    monkeypatch.setattr(core, "run_ngspice_text", fake_run)
    return captured


HOSTILE = (
    "v1 1 0 5\n"
    "r1 1 0 1k\n"
    ".control\n"
    "shell echo pwned\n"
    ".endc\n"
    ".include /etc/passwd\n"
    ".op\n"
    ".end\n"
)


def test_evaluate_text_no_exec_strips_before_ngspice(fake_ngspice):
    r = core.evaluate_text(HOSTILE, no_exec=True)
    assert "shell" not in fake_ngspice["text"]
    assert ".include" not in fake_ngspice["text"]
    codes = [i.code for i in r.issues]
    assert "no_exec_stripped" in codes
    stripped = next(i for i in r.issues if i.code == "no_exec_stripped")
    assert stripped.severity == "INFO"


def test_evaluate_text_no_exec_info_does_not_lower_verdict(fake_ngspice):
    clean_plus_control = "v1 1 0 5\nr1 1 0 1k\n.control\nrun\n.endc\n.op\n.end\n"
    r = core.evaluate_text(clean_plus_control, no_exec=True)
    assert r.verdict == "TRUSTWORTHY"


def test_evaluate_text_default_mode_leaves_text_alone(fake_ngspice):
    core.evaluate_text(HOSTILE, no_exec=False)
    assert ".control" in fake_ngspice["text"]


def test_evaluate_text_label_becomes_result_path(fake_ngspice):
    r = core.evaluate_text("v1 1 0 5\n.op\n.end\n", label="from-mcp")
    assert r.path == "from-mcp"


def test_evaluate_file_passes_no_exec_through(fake_ngspice, tmp_path):
    p = tmp_path / "hostile.cir"
    p.write_text(HOSTILE)
    r = core.evaluate(str(p), no_exec=True)
    assert "shell" not in fake_ngspice["text"]
    assert "no_exec_stripped" in [i.code for i in r.issues]


def test_cli_accepts_no_exec_flag(monkeypatch, tmp_path, capsys):
    from spiceguard import cli

    p = tmp_path / "ok.cir"
    p.write_text("v1 1 0 5\nr1 1 0 1k\n.control\nrun\n.endc\n.op\n.end\n")

    def fake_run(text, ngspice_path=None, cwd=None):
        assert ".control" not in text
        return 0, "No. of Data Rows : 1\n"

    monkeypatch.setattr(core, "run_ngspice_text", fake_run)
    rc = cli.main(["--no-exec", str(p)])
    assert rc == 0
