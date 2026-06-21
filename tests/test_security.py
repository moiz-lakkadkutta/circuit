"""Security-hardening regression tests (Phase: pre-publish audit)."""
import subprocess
from pathlib import Path

import pytest

from spiceguard import ngspice as ng
from spiceguard.netlist import parse_and_flatten, MAX_SUBCKT_DEPTH


# --- ngspice invocation hardening -------------------------------------------

def test_ngspice_invoked_with_no_spiceinit(monkeypatch):
    """`-n/--no-spiceinit` must be passed so a planted .spiceinit can't auto-run."""
    captured = {}

    def fake_run(argv, **kwargs):
        captured["argv"] = argv
        class P:  # noqa: D401
            returncode = 0
            stdout = ""
            stderr = ""
        return P()

    monkeypatch.setattr(ng, "resolve_ngspice_path", lambda explicit=None: "/usr/bin/ngspice")
    monkeypatch.setattr(ng.subprocess, "run", fake_run)
    ng.run_ngspice_text("v1 1 0 5\n.op\n.end\n")
    assert "-n" in captured["argv"], captured["argv"]
    assert captured["argv"][0] == "/usr/bin/ngspice"


def test_ngspice_timeout_returns_clean_not_raises(monkeypatch):
    """A hanging ngspice must surface as a non-zero rc + message, never a traceback."""
    def fake_run(argv, **kwargs):
        raise subprocess.TimeoutExpired(cmd=argv, timeout=ng.NGSPICE_TIMEOUT)

    monkeypatch.setattr(ng, "resolve_ngspice_path", lambda explicit=None: "/usr/bin/ngspice")
    monkeypatch.setattr(ng.subprocess, "run", fake_run)
    rc, log = ng.run_ngspice_text("v1 1 0 5\n.op\n.end\n")
    assert rc != 0
    assert "timed out" in log.lower()


def test_ngspice_tempfile_cleaned_up_on_timeout(monkeypatch, tmp_path):
    """The temp netlist file must not leak when the run times out."""
    monkeypatch.setattr(ng.tempfile, "tempdir", str(tmp_path))
    before = set(tmp_path.iterdir())

    def fake_run(argv, **kwargs):
        raise subprocess.TimeoutExpired(cmd=argv, timeout=1)

    monkeypatch.setattr(ng, "resolve_ngspice_path", lambda explicit=None: "/usr/bin/ngspice")
    monkeypatch.setattr(ng.subprocess, "run", fake_run)
    ng.run_ngspice_text("x")
    after = set(tmp_path.iterdir())
    assert before == after, f"temp file leaked: {after - before}"


# --- parser hardening --------------------------------------------------------

def test_binary_include_does_not_crash(tmp_path):
    """A .include pointing at a binary file → warning, not UnicodeDecodeError."""
    (tmp_path / "blob.inc").write_bytes(b"\x00\x01\x02\xff\xfe garbage")
    text = 'v1 1 0 5\n.include "blob.inc"\nr1 1 0 1k\n.op\n.end\n'
    elems, node_elems, issues = parse_and_flatten(text, tmp_path)
    codes = {i.code for i in issues}
    assert "missing_include" in codes, codes  # reported cleanly, no exception


def test_deep_subckt_nesting_bounded(tmp_path):
    """Pathologically deep acyclic nesting → bounded (no RecursionError)."""
    depth = MAX_SUBCKT_DEPTH + 10
    lines = [".subckt L0 a b", "r1 a b 1k", ".ends"]
    for i in range(1, depth):
        lines += [f".subckt L{i} a b", f"x1 a b L{i-1}", ".ends"]
    lines += ["v1 1 0 5", f"x1 1 0 L{depth-1}", ".op", ".end"]
    text = "\n".join(lines) + "\n"
    elems, node_elems, issues = parse_and_flatten(text, tmp_path)  # must not raise
    assert any(i.code == "subckt_too_deep" for i in issues)


def test_include_path_is_relative_to_netlist_dir(tmp_path):
    """Sanity: includes resolve relative to the netlist's directory."""
    (tmp_path / "models.inc").write_text(".subckt RBLK a b\nr1 a b 1k\n.ends\n")
    text = 'v1 in 0 5\n.include "models.inc"\nx1 in 0 RBLK\n.op\n.end\n'
    elems, node_elems, issues = parse_and_flatten(text, tmp_path)
    assert not any(i.code == "missing_include" for i in issues)
    assert any(e.refdes.endswith("r1") for e in elems)
