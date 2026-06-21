"""
Behavior tests for spiceguard, run against REAL ngspice output.

These are the honesty harness: they assert the verdict and the specific
codes we expect on known-good and known-bad circuits. If a refactor breaks
a real diagnosis, these fail.

Run: PYTHONPATH=src python3 -m pytest tests/ -q
"""
import subprocess
from pathlib import Path

import pytest

import spiceguard as tg
from spiceguard import formats

NET = Path(__file__).parent / "netlists"

requires_ngspice = pytest.mark.skipif(
    not tg.ngspice.ngspice_available(),
    reason="ngspice not installed",
)


def verdict_for(name):
    r = tg.evaluate(NET / name)
    return r.verdict, {i.code for i in r.issues}


# --- healthy circuits must be left alone (no crying wolf) ---

@requires_ngspice
def test_healthy_rc_is_trustworthy():
    v, codes = verdict_for("n5_healthy_control.cir")
    assert v == "TRUSTWORTHY", (v, codes)
    assert codes == set()


@requires_ngspice
def test_converging_smps_is_trustworthy():
    # N3 converges on ngspice 46 — must NOT be flagged
    v, codes = verdict_for("n3_ideal_switch_smps.cir")
    assert v == "TRUSTWORTHY", (v, codes)


@requires_ngspice
def test_converging_bsource_is_trustworthy():
    v, codes = verdict_for("n4_bsource_singular.cir")
    assert v == "TRUSTWORTHY", (v, codes)


# --- silent failures (exit 0 but wrong) must be caught as SUSPECT ---

@requires_ngspice
def test_missing_ground_is_suspect():
    v, codes = verdict_for("n1_missing_ground.cir")
    assert v == "SUSPECT", (v, codes)
    assert "no_ground" in codes


@requires_ngspice
def test_floating_node_is_suspect():
    v, codes = verdict_for("n2_floating_node.cir")
    assert v == "SUSPECT", (v, codes)
    assert "no_dc_path" in codes
    assert "silent_fallback" in codes  # ngspice returned 0 via fallback


@requires_ngspice
def test_legit_above_rail_is_trustworthy():
    # N8: stacked 5V sources put node 2 at 10V — correct, grounded, converges.
    # The old magnitude-based detector wrongly flagged this; the fix must not.
    v, codes = verdict_for("n8_stacked_sources.cir")
    assert v == "TRUSTWORTHY", (v, codes)
    assert codes == set()


# --- hard failures (exit != 0) must be FAILED with the culprit named ---

@requires_ngspice
def test_source_conflict_is_failed_and_names_sources():
    r = tg.evaluate(NET / "n6_source_conflict.cir")
    assert r.verdict == "FAILED", r.verdict
    codes = {i.code for i in r.issues}
    assert "source_conflict" in codes
    # the diagnosis text must name the actual conflicting refdes
    txt = " ".join(i.message for i in r.issues)
    assert "v1" in txt and "v2" in txt


@requires_ngspice
def test_timestep_collapse_names_instance():
    r = tg.evaluate(NET / "n7_relaxation_osc.cir")
    assert r.verdict == "FAILED", r.verdict
    txt = " ".join(i.message for i in r.issues)
    assert "s1" in txt, txt  # must name the actual switch, not 'sw-instance'


# --- real-world circuits (not designed to trip detectors) ---

@requires_ngspice
def test_realworld_ce_amplifier_trustworthy():
    # coupling/bypass caps present, but nodes are DC-referenced via bias resistors
    v, codes = verdict_for("realworld/ce_amplifier.cir")
    assert v == "TRUSTWORTHY", (v, codes)


@requires_ngspice
def test_realworld_bridge_rectifier_trustworthy():
    # 470uF smoothing cap node must NOT trip no_dc_path (load gives the DC path)
    v, codes = verdict_for("realworld/bridge_rectifier.cir")
    assert v == "TRUSTWORTHY", (v, codes)


@requires_ngspice
def test_realworld_astable_timestep_names_node():
    # found a real false negative: ngspice's 'trouble with node "c2"' form was
    # not parsed. Must now be FAILED and name the actual node c2.
    r = tg.evaluate(NET / "realworld/astable_multivibrator.cir")
    assert r.verdict == "FAILED", r.verdict
    codes = {i.code for i in r.issues}
    assert "timestep_collapse" in codes, codes
    txt = " ".join(i.message for i in r.issues)
    assert "c2" in txt, txt


# --- exit codes for CI use ---

def test_exit_codes():
    assert tg.exit_code("TRUSTWORTHY") == 0
    assert tg.exit_code("FAILED") == 1
    assert tg.exit_code("SUSPECT") == 2


# --- (c) input-format support ---

def test_asc_converts_to_correct_divider_topology():
    netlist, warnings = formats.asc_to_netlist(
        (NET / "realworld/divider.asc").read_text())
    assert warnings == [], warnings
    elems, node_elems, _ = tg.parse_netlist(netlist)
    by = {e.refdes.upper(): set(e.nodes) for e in elems}
    assert {"V1", "R1", "R2"} <= set(by), by
    # exactly the divider topology: V1 & R2 touch ground; V1-R1 and R1-R2 share nets
    assert "0" in by["V1"] and "0" in by["R2"]
    vin = (by["V1"] - {"0"}); mid_r1 = by["R1"] - vin
    assert by["V1"] & by["R1"], "V1 and R1 must share the input net"
    assert by["R1"] & by["R2"], "R1 and R2 must share the mid net"
    assert "0" not in (by["R1"]), "R1 should not touch ground in a divider"


@requires_ngspice
def test_asc_verdict_trustworthy():
    v, codes = verdict_for("realworld/divider.asc")
    assert v == "TRUSTWORTHY", (v, codes)  # INFO 'converted' must not lower it


@requires_ngspice
def test_kicad_netlist_floating_node_caught():
    # KiCad-style /NET names + ground 0; planted floating node must be caught
    r = tg.evaluate(NET / "realworld/kicad_export.cir")
    assert r.verdict == "SUSPECT", r.verdict
    codes = {i.code for i in r.issues}
    assert "no_dc_path" in codes, codes


if __name__ == "__main__":
    # lightweight runner so it works without pytest installed
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"FAIL {fn.__name__}: {e}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)
