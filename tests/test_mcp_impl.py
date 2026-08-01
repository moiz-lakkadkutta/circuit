"""Tests for the MCP server implementation functions (not the protocol layer)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "mcp-server" / "src"))

from spiceguard import core  # noqa: E402
from spiceguard_mcp.server import check_netlist_impl  # noqa: E402


def test_returns_structured_dict_with_verdict(monkeypatch):
    monkeypatch.setattr(core, "run_ngspice_text",
                        lambda text, ngspice_path=None, cwd=None: (0, "ok"))
    out = check_netlist_impl("v1 1 0 5\nr1 1 0 1k\n.op\n.end\n")
    assert out["verdict"] in ("TRUSTWORTHY", "SUSPECT", "FAILED")
    assert out["mode"] == "no-exec"
    assert isinstance(out["issues"], list)


def test_hostile_netlist_never_reaches_ngspice_unsanitized(monkeypatch):
    seen = {}

    def fake_run(text, ngspice_path=None, cwd=None):
        seen["text"] = text
        return 0, "ok"

    monkeypatch.setattr(core, "run_ngspice_text", fake_run)
    check_netlist_impl(".control\nshell echo pwned\n.endc\nv1 1 0 5\n.op\n.end\n")
    assert "shell" not in seen["text"]


def test_falls_back_to_static_when_ngspice_missing(monkeypatch):
    import spiceguard_mcp.server as srv
    monkeypatch.setattr(srv, "ngspice_available", lambda: False)
    out = check_netlist_impl("v1 1 2 5\nr1 1 2 1k\n.op\n.end\n")
    assert out["mode"] == "static-only"
    assert "no_ground" in [i["code"] for i in out["issues"]]
    assert "install ngspice" in out["note"].lower()
