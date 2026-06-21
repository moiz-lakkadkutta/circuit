"""
TDD tests for subcircuit-aware parse_and_flatten (Task T4, feature B).

These tests are PURE — no ngspice required.
Run: PYTHONPATH=src python3 -m pytest tests/test_subcircuits.py -q
"""
from pathlib import Path
from collections import defaultdict

import pytest

from spiceguard.netlist import parse_and_flatten
from spiceguard import checks

NET = Path(__file__).parent / "netlists"
RW = NET / "realworld"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def issue_codes(issues):
    return {i.code for i in issues}


def static_issue_codes(elements, node_elems):
    return issue_codes(checks.static_checks(elements, node_elems))


# ---------------------------------------------------------------------------
# AC-B1: continuation lines ('+' prefix)
# ---------------------------------------------------------------------------

def test_continuation_lines_joined():
    """A line split with '+' must parse as one element."""
    text = """\
* continuation test
R1 A
+ B 1k
V1 A 0 5
"""
    elements, node_elems, parse_issues = parse_and_flatten(text, Path("."))
    assert parse_issues == []
    refdes_list = [e.refdes for e in elements]
    assert "R1" in refdes_list, f"R1 not parsed, got: {refdes_list}"
    r1 = next(e for e in elements if e.refdes == "R1")
    assert r1.nodes == ["A", "B"], f"Expected ['A','B'], got {r1.nodes}"


# ---------------------------------------------------------------------------
# AC-B2 / AC-B5: DC path soundness — subckt resistor prevents false no_dc_path
# ---------------------------------------------------------------------------

def test_subckt_dcpath_no_false_positive():
    """X-instance whose subckt connects port to ground via R must NOT trigger no_dc_path."""
    text = (RW / "sub_dcpath.cir").read_text()
    elements, node_elems, parse_issues = parse_and_flatten(text, RW)
    assert parse_issues == [], f"Unexpected parse issues: {parse_issues}"
    codes = static_issue_codes(elements, node_elems)
    assert "no_dc_path" not in codes, (
        f"False no_dc_path fired. Node set: {set(node_elems)}. Codes: {codes}"
    )


# ---------------------------------------------------------------------------
# AC-B5: floating internal node must still be caught (on namespaced name)
# ---------------------------------------------------------------------------

def test_subckt_floating_internal_caught():
    """Internal node reachable only via caps must still get no_dc_path."""
    text = (RW / "sub_floating.cir").read_text()
    elements, node_elems, parse_issues = parse_and_flatten(text, RW)
    assert parse_issues == [], f"Unexpected parse issues: {parse_issues}"
    codes = static_issue_codes(elements, node_elems)
    assert "no_dc_path" in codes, (
        f"Expected no_dc_path for floating internal node. "
        f"Node set: {set(node_elems)}. Codes: {codes}"
    )
    # The offending node should be namespaced (contain ':')
    static_issues = checks.static_checks(elements, node_elems)
    flagged_nodes = [
        i.message for i in static_issues if i.code == "no_dc_path"
    ]
    assert any(":" in msg for msg in flagged_nodes), (
        f"Floating node name should be namespaced (contain ':'). Got: {flagged_nodes}"
    )


# ---------------------------------------------------------------------------
# AC-B2: nested subckts flatten correctly
# ---------------------------------------------------------------------------

def test_nested_subckts_flatten():
    """A subckt containing an X-instance of another subckt must flatten without error."""
    text = (RW / "sub_nested.cir").read_text()
    elements, node_elems, parse_issues = parse_and_flatten(text, RW)
    assert parse_issues == [], f"Unexpected parse issues: {parse_issues}"
    # After flattening, net1 is connected (via nested R) to 0
    codes = static_issue_codes(elements, node_elems)
    assert "no_dc_path" not in codes, (
        f"no_dc_path should not fire after nested flatten. Codes: {codes}"
    )
    # Must have at least one element (the inner R)
    assert len(elements) >= 2, f"Expected >=2 elements after flattening, got {elements}"


# ---------------------------------------------------------------------------
# AC-B6: undefined subckt produces parse_issue
# ---------------------------------------------------------------------------

def test_undefined_subckt_parse_issue():
    """X referencing missing subckt must emit undefined_subckt in parse_issues."""
    text = (RW / "sub_undefined.cir").read_text()
    elements, node_elems, parse_issues = parse_and_flatten(text, RW)
    codes = issue_codes(parse_issues)
    assert "undefined_subckt" in codes, (
        f"Expected undefined_subckt issue, got: {parse_issues}"
    )


# ---------------------------------------------------------------------------
# AC-B4: .include resolves sub_models.inc and flattening works
# ---------------------------------------------------------------------------

def test_include_resolves_subckt():
    """.include file providing subckt must be loaded and X-instance flattened."""
    text = (RW / "sub_include.cir").read_text()
    elements, node_elems, parse_issues = parse_and_flatten(text, RW)
    assert parse_issues == [], f"Unexpected parse issues: {parse_issues}"
    # MID node exists and has DC path (R1, R2 inside DIVIDER)
    assert "MID" in node_elems or "mid" in node_elems or any(
        "MID" in k.upper() for k in node_elems
    ), f"MID node not found. node_elems keys: {set(node_elems)}"
    codes = static_issue_codes(elements, node_elems)
    assert "no_dc_path" not in codes, (
        f"no_dc_path should not fire. Codes: {codes}"
    )


# ---------------------------------------------------------------------------
# AC-B3: port count mismatch emits a parse_issue
# ---------------------------------------------------------------------------

def test_port_count_mismatch():
    """X-instance with wrong number of ports must emit a parse_issue."""
    text = """\
* port mismatch test
.subckt TWOPORTR p1 p2
R1 p1 p2 1k
.ends TWOPORTR
V1 A 0 5
* TWOPORTR needs 2 ports but we give 3
XBAD A B C TWOPORTR
.op
.end
"""
    elements, node_elems, parse_issues = parse_and_flatten(text, Path("."))
    codes = issue_codes(parse_issues)
    assert len(parse_issues) > 0, "Expected at least one parse_issue for port mismatch"
    # Should have some issue relating to port mismatch (undefined_subckt or port_mismatch)
    assert codes & {"port_mismatch", "undefined_subckt"} or any(
        "port" in str(i.message).lower() or "mismatch" in str(i.message).lower()
        or "XBAD" in str(i.message)
        for i in parse_issues
    ), f"Expected port mismatch issue, got: {parse_issues}"


# ---------------------------------------------------------------------------
# Recursion / cycle guard
# ---------------------------------------------------------------------------

def test_subckt_recursion_guard():
    """A self-referencing subckt must emit subckt_recursion, not infinite loop."""
    text = """\
* recursion test
.subckt RECURSIVE p1 p2
R1 p1 p2 1k
XREC p1 p2 RECURSIVE
.ends RECURSIVE
V1 A 0 5
XTOP A 0 RECURSIVE
.op
.end
"""
    # Must return without hanging
    elements, node_elems, parse_issues = parse_and_flatten(text, Path("."))
    codes = issue_codes(parse_issues)
    assert "subckt_recursion" in codes, (
        f"Expected subckt_recursion issue, got: {parse_issues}"
    )


# ---------------------------------------------------------------------------
# AC-B1 + no-op: existing plain netlists unchanged
# ---------------------------------------------------------------------------

def test_plain_netlist_unchanged():
    """A netlist with no .subckt/X/.include/'+' must parse identically to today."""
    path = NET / "n5_healthy_control.cir"
    text = path.read_text()

    from spiceguard.netlist import parse_netlist
    elements_old, node_elems_old, _ = parse_netlist(text)
    elements_new, node_elems_new, parse_issues = parse_and_flatten(text, path.parent)

    assert parse_issues == [], f"No parse issues expected for plain netlist: {parse_issues}"
    assert [e.refdes for e in elements_new] == [e.refdes for e in elements_old]
    assert set(node_elems_new.keys()) == set(node_elems_old.keys())


# ---------------------------------------------------------------------------
# AC-B4: missing include file emits parse_issue, does not crash
# ---------------------------------------------------------------------------

def test_missing_include_parse_issue():
    """A .include pointing to a nonexistent file must emit a parse_issue."""
    text = """\
* missing include
.include "does_not_exist.inc"
V1 A 0 5
R1 A 0 1k
.op
.end
"""
    elements, node_elems, parse_issues = parse_and_flatten(text, Path("/tmp"))
    codes = issue_codes(parse_issues)
    assert len(parse_issues) > 0, "Expected a parse_issue for missing include"
    assert any("include" in str(i.message).lower() or "does_not_exist" in str(i.message)
               for i in parse_issues), f"Expected include-related issue, got: {parse_issues}"


# ---------------------------------------------------------------------------
# Internal node names must not collide with top-level nets
# ---------------------------------------------------------------------------

def test_internal_nodes_namespaced():
    """Internal nodes of a subckt must be namespaced so they don't collide."""
    text = """\
* namespace collision test
.subckt BLOCK p1 p2
R1 p1 internal 500
R2 internal p2 500
.ends BLOCK
* top-level node also called 'internal'
R_top internal 0 1k
V1 A 0 5
XBLK A internal BLOCK
.op
.end
"""
    elements, node_elems, parse_issues = parse_and_flatten(text, Path("."))
    assert parse_issues == [], f"Unexpected parse issues: {parse_issues}"
    # The top-level 'internal' node and the subckt internal 'internal' node
    # must be distinct keys in node_elems
    keys = set(node_elems.keys())
    # There should be a namespaced version like 'XBLK:internal'
    namespaced = {k for k in keys if ":" in k}
    assert len(namespaced) >= 1, (
        f"Expected at least one namespaced internal node, got keys: {keys}"
    )


# ---------------------------------------------------------------------------
# BLOCKER fix: two instances of same subckt must not collide on refdes
# ---------------------------------------------------------------------------

def test_two_instances_same_subckt_no_refdes_collision():
    """Two X-instances of the same subckt sharing a node must each emit a
    distinct namespaced refdes, so node_elems for the shared node has TWO
    entries, no spurious dangling_node, and the circuit is not mis-flagged."""
    text = (RW / "sub_twoinst.cir").read_text()
    elements, node_elems, parse_issues = parse_and_flatten(text, RW)

    assert parse_issues == [], f"Unexpected parse issues: {parse_issues}"

    # node_elems["MID"] must contain refdes from BOTH instances
    mid_refs = node_elems.get("MID", set())
    assert len(mid_refs) == 2, (
        f"Expected 2 refdes touching MID (one per instance), got {mid_refs}"
    )
    # Both refdes must be namespaced (contain ':')
    assert all(":" in r for r in mid_refs), (
        f"All refdes touching MID should be namespaced, got {mid_refs}"
    )
    # They must be distinct (one from X1, one from X2)
    prefixes = {r.split(":")[0] for r in mid_refs}
    assert prefixes == {"X1", "X2"}, (
        f"Expected one refdes from X1 and one from X2, got prefixes {prefixes}"
    )

    # No spurious dangling_node or no_dc_path on MID
    all_issues = checks.static_checks(elements, node_elems)
    mid_issues = [i for i in all_issues
                  if "MID" in i.message or "mid" in i.message.lower()]
    assert mid_issues == [], (
        f"No issues expected for MID, got: {mid_issues}"
    )

    # Overall verdict must NOT be SUSPECT due to this collision
    trust_breaking_codes = {i.code for i in all_issues
                            if i.severity in {"FATAL", "SILENT", "WARN"}}
    assert "dangling_node" not in trust_breaking_codes, (
        f"dangling_node should not fire: {trust_breaking_codes}"
    )
    assert "no_dc_path" not in trust_breaking_codes, (
        f"no_dc_path should not fire: {trust_breaking_codes}"
    )


# ---------------------------------------------------------------------------
# SF-3 (FIX 1): X-instance with trailing param=val tokens must not be misparsed
# ---------------------------------------------------------------------------

def test_trailing_params_no_undefined_subckt():
    """X-instance with trailing key=val params must match its subckt, not falsely emit
    undefined_subckt or port_mismatch."""
    text = """\
* trailing params test
.subckt DIV in out
R1 in out 1k
.ends DIV
V1 in 0 5
X1 in out DIV foo=1 bar=2
.op
.end
"""
    elements, node_elems, parse_issues = parse_and_flatten(text, Path("."))
    codes = issue_codes(parse_issues)
    assert "undefined_subckt" not in codes, (
        f"Trailing params caused spurious undefined_subckt: {parse_issues}"
    )
    assert "port_mismatch" not in codes, (
        f"Trailing params caused spurious port_mismatch: {parse_issues}"
    )
    # The flattened resistor from DIV must be present and connect the right nodes
    assert len(elements) >= 1, "Expected flattened elements from DIV subckt"
    refdes_list = [e.refdes for e in elements]
    assert any("R1" in r for r in refdes_list), (
        f"Expected flattened R1 from DIV, got: {refdes_list}"
    )


def test_trailing_params_keyword_tolerated():
    """X-instance with PARAMS: keyword before key=val tokens must parse correctly."""
    text = """\
* params keyword test
.subckt DIV2 in out
R1 in out 2k
.ends DIV2
V1 in 0 5
X1 in out DIV2 PARAMS: foo=1 bar=2
.op
.end
"""
    elements, node_elems, parse_issues = parse_and_flatten(text, Path("."))
    codes = issue_codes(parse_issues)
    assert "undefined_subckt" not in codes, (
        f"PARAMS: keyword caused spurious undefined_subckt: {parse_issues}"
    )
    assert "port_mismatch" not in codes, (
        f"PARAMS: keyword caused spurious port_mismatch: {parse_issues}"
    )
    assert len(elements) >= 1, "Expected flattened elements from DIV2 subckt"


# ---------------------------------------------------------------------------
# AC-B3 (FIX 2): Asymmetric subckt — port mapping must preserve positional order
# ---------------------------------------------------------------------------

def test_asymmetric_port_mapping():
    """Asymmetric subckt must bind ports in correct positional order.

    ASYM has ports (a, b): R1 connects a to 0, C1 connects b to a.
    X1 N1 N2 ASYM => a=N1, b=N2.
    After flatten: R1 nodes must be [N1, 0]; C1 nodes must be [N2, N1].
    A port-swap bug would give R1=[N2,0] and C1=[N1,N2], which is different.
    """
    text = """\
* asymmetric port mapping test
.subckt ASYM a b
R1 a 0 1k
C1 b a 1n
.ends ASYM
X1 N1 N2 ASYM
.op
.end
"""
    elements, node_elems, parse_issues = parse_and_flatten(text, Path("."))
    assert parse_issues == [], f"Unexpected parse issues: {parse_issues}"

    r1 = next((e for e in elements if e.refdes.endswith(":R1")), None)
    c1 = next((e for e in elements if e.refdes.endswith(":C1")), None)
    assert r1 is not None, f"Flattened R1 not found in: {[e.refdes for e in elements]}"
    assert c1 is not None, f"Flattened C1 not found in: {[e.refdes for e in elements]}"

    # a -> N1, 0 stays 0 => R1 nodes = [N1, 0]
    assert r1.nodes == ["N1", "0"], (
        f"R1 should connect [N1, 0] (a=N1), got {r1.nodes}. "
        "If [N2, 0] appears, ports were swapped."
    )
    # b -> N2, a -> N1 => C1 nodes = [N2, N1]
    assert c1.nodes == ["N2", "N1"], (
        f"C1 should connect [N2, N1] (b=N2, a=N1), got {c1.nodes}. "
        "If [N1, N2] appears, ports were swapped."
    )
