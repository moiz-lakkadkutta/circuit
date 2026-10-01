"""Tests for the MCP server implementation functions (not the protocol layer)."""
import sys
from pathlib import Path

import pytest

# mcp (mcp.server.fastmcp, pulled in by spiceguard_mcp.server) requires
# Python >=3.10 and is not installed on every CI leg (notably the 3.9 leg,
# which cannot install it at all). Skip this whole module cleanly rather
# than letting the import below raise a collection error that would zero
# out the entire pytest run.
pytest.importorskip("mcp")

sys.path.insert(0, str(Path(__file__).parent.parent / "mcp-server" / "src"))

from spiceguard import core  # noqa: E402
from spiceguard_mcp.server import check_netlist_impl  # noqa: E402


@pytest.fixture
def simulated_run(monkeypatch):
    """Force the simulation branch and capture the text ngspice would receive.

    check_netlist_impl falls back to static-only when no ngspice binary is
    present, so these tests must pin availability rather than inherit it from
    the machine — otherwise they exercise a different code path on a CI runner
    than on a developer box with ngspice installed.
    """
    import spiceguard_mcp.server as srv

    seen = {}

    def fake_run(text, ngspice_path=None, cwd=None):
        seen["text"] = text
        return 0, "ok"

    monkeypatch.setattr(srv, "ngspice_available", lambda: True)
    monkeypatch.setattr(core, "run_ngspice_text", fake_run)
    return seen


def test_returns_structured_dict_with_verdict(simulated_run):
    out = check_netlist_impl("v1 1 0 5\nr1 1 0 1k\n.op\n.end\n")
    assert out["verdict"] in ("TRUSTWORTHY", "SUSPECT", "FAILED")
    assert out["mode"] == "no-exec"
    assert isinstance(out["issues"], list)


def test_hostile_netlist_never_reaches_ngspice_unsanitized(simulated_run):
    check_netlist_impl(".control\nshell echo pwned\n.endc\nv1 1 0 5\n.op\n.end\n")
    assert "shell" not in simulated_run["text"]


def test_falls_back_to_static_when_ngspice_missing(monkeypatch):
    import spiceguard_mcp.server as srv
    monkeypatch.setattr(srv, "ngspice_available", lambda: False)
    out = check_netlist_impl("v1 1 2 5\nr1 1 2 1k\n.op\n.end\n")
    assert out["mode"] == "static-only"
    assert "no_ground" in [i["code"] for i in out["issues"]]
    assert "install ngspice" in out["note"].lower()
