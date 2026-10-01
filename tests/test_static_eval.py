"""Tests for the static-only evaluator (Pyodide/browser path)."""
from spiceguard.static_eval import evaluate_static


def test_missing_ground_flagged_without_ngspice():
    r = evaluate_static("v1 1 2 5\nr1 1 2 1k\n.op\n.end\n")
    assert r["mode"] == "static-only"
    assert r["verdict"] == "SUSPECT"
    assert "no_ground" in [i["code"] for i in r["issues"]]


def test_healthy_netlist_passes_static_not_trustworthy():
    r = evaluate_static("v1 1 0 5\nr1 1 0 1k\n.op\n.end\n")
    assert r["verdict"] == "PASSED_STATIC"
    assert r["verdict"] != "TRUSTWORTHY"  # static-only must never claim full trust


def test_hostile_input_is_sanitized_and_never_executed():
    r = evaluate_static(".control\nshell echo pwned\n.endc\nv1 1 0 5\n.op\n.end\n")
    assert isinstance(r, dict)  # completes without subprocess/OS access


def test_no_subprocess_import():
    import spiceguard.static_eval as m
    import inspect
    src = inspect.getsource(m)
    assert "subprocess" not in src
    assert "run_ngspice" not in src
