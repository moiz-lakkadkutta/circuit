#!/usr/bin/env python3
"""
trustguard — answer one question about a SPICE run: can I trust this result?

It wraps ngspice, then combines:
  1. static netlist analysis (missing ground, source conflicts, floating nodes),
  2. failure-log parsing (singular nodes, timestep collapse — decoded to real
     component names), and
  3. SILENT-failure detection: cases where ngspice returns exit code 0 but the
     answer is untrustworthy (op-point obtained via a fallback after stepping
     failed; node voltages far outside the supply rails).

Verdict: TRUSTWORTHY (0) | SUSPECT (2) | FAILED (1).  Exit codes suit CI/scripts.
No third-party deps.
"""
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import formats

NGSPICE = "/opt/homebrew/bin/ngspice"

NODE_COUNT = {
    "R": 2, "C": 2, "L": 2, "V": 2, "I": 2, "D": 2,
    "B": 2, "Q": 3, "J": 3, "M": 4, "E": 4, "G": 4,
    "S": 4, "W": 4, "T": 4,
}
SEVERITY_ORDER = {"FATAL": 0, "SILENT": 1, "WARN": 2, "INFO": 3}
TRUST_BREAKING = {"FATAL", "SILENT", "WARN"}  # INFO never lowers the verdict


@dataclass
class Issue:
    severity: str   # FATAL | SILENT | WARN
    code: str
    message: str


@dataclass
class Element:
    refdes: str
    nodes: list
    raw: str
    @property
    def kind(self):
        return self.refdes[0].upper()


@dataclass
class Result:
    path: str
    verdict: str
    rc: int
    issues: list = field(default_factory=list)
    signals: dict = field(default_factory=dict)
    source: str = "netlist"
    netlist_text: str = ""


# ---- parsing -------------------------------------------------------------

def parse_netlist(text):
    elements, node_elems, title = [], defaultdict(set), ""
    for i, line in enumerate(text.splitlines()):
        s = line.strip()
        if i == 0:
            title = s.lstrip("* ").strip()
        if not s or s[0] in "*.+":
            continue
        toks = s.split()
        n = NODE_COUNT.get(toks[0][0].upper())
        if n is None or len(toks) < 1 + n:
            continue
        el = Element(toks[0], toks[1:1 + n], s)
        elements.append(el)
        for nd in el.nodes:
            node_elems[nd].add(el.refdes)
    return elements, node_elems, title


# Element kinds that pass DC current (provide a galvanic reference path).
# Capacitors are open at DC; current sources and VCCS (G) present infinite
# impedance, so they do NOT establish a node's DC voltage.
NON_DC_KINDS = {"C", "I", "G"}


def dc_edges(el):
    """Node pairs this element galvanically connects at DC (for reference reachability)."""
    if el.kind in NON_DC_KINDS:
        return []
    nd = el.nodes
    if el.kind in ("Q", "J") and len(nd) >= 3:          # BJT/JFET: all terminals
        return [(nd[0], nd[1]), (nd[1], nd[2]), (nd[0], nd[2])]
    if el.kind == "M" and len(nd) >= 4:                 # MOSFET d g s b: skip gate
        return [(nd[0], nd[1]), (nd[0], nd[3]), (nd[1], nd[3])]
    # R,L,V,D,B (2 terminals) and E,S,W (output/switched path = first two nodes)
    return [(nd[0], nd[1])]


def nodes_with_dc_path_to_ground(elements):
    """BFS from node '0' over DC-conducting elements; returns the reachable set."""
    adj = defaultdict(set)
    for el in elements:
        for a, b in dc_edges(el):
            adj[a].add(b)
            adj[b].add(a)
    reachable, frontier = {"0"}, ["0"]
    while frontier:
        n = frontier.pop()
        for m in adj[n]:
            if m not in reachable:
                reachable.add(m)
                frontier.append(m)
    return reachable


# ---- log signal extraction ----------------------------------------------

RE_SINGULAR = re.compile(r"singular matrix:\s*check node\s+(\S+)", re.I)
# ngspice reports the timestep-collapse culprit in more than one format, e.g.
#   "... trouble with sw-instance s1"     (a device instance)
#   "... trouble with node \"c2\""         (a node, quoted)
# Capture the trailing culprit phrase and classify it afterwards.
RE_TS = re.compile(
    r"Timestep too small;\s*time\s*=\s*(\S+),\s*timestep\s*=\s*(\S+):\s*"
    r"trouble with\s+(.+?)\s*$", re.I | re.M)


def classify_ts_culprit(raw):
    """Return (label, name) from a 'trouble with ...' phrase, both formats."""
    m = re.match(r"(\S+?)-instance\s+(\S+)", raw)
    if m:
        return f"{m.group(1)} instance", m.group(2)
    m = re.match(r'node\s+"?([^"]+)"?', raw, re.I)
    if m:
        return "node", m.group(1)
    return "element", raw.strip().strip('"')


def extract_signals(log, rc):
    return {
        "rc": rc,
        "singular_nodes": sorted(set(RE_SINGULAR.findall(log))),
        "timestep": [(t, ts, *classify_ts_culprit(raw))
                     for t, ts, raw in RE_TS.findall(log)],
        "gmin_failed": "gmin stepping failed" in log.lower(),
        "source_failed": "source stepping failed" in log.lower(),
        "dc_failed": ("dc solution failed" in log.lower()
                      or "operating point could not" in log.lower()),
        "fallback_op": ("transient op finished successfully" in log.lower()),
        "aborted": "simulation(s) aborted" in log.lower(),
    }


# ---- rules ---------------------------------------------------------------

def static_checks(elements, node_elems):
    out = []
    if "0" not in node_elems:
        out.append(Issue("FATAL", "no_ground",
            "No node '0' (ground). SPICE has no voltage reference, so it may "
            "float the circuit and return arbitrary WRONG voltages with no error. "
            "Fix: tie a reference node to '0'."))
    vpairs = defaultdict(list)
    for el in elements:
        if el.kind == "V":
            vpairs[frozenset(el.nodes)].append(el.refdes)
    for pair, refs in vpairs.items():
        if len(refs) > 1:
            out.append(Issue("FATAL", "source_conflict",
                f"Voltage sources {', '.join(refs)} are all forced across nodes "
                f"{sorted(pair)} — a zero-impedance conflict (singular). Fix: keep "
                f"one, or add series resistance to each."))
    # Topological DC-path-to-ground check. A node reachable from ground only
    # through capacitors / current sources has its DC voltage set by gmin
    # leakage, not the circuit — untrustworthy REGARDLESS of magnitude (so this
    # does NOT false-positive on legitimately above-rail nodes, e.g. boosts).
    if "0" in node_elems:
        reachable = nodes_with_dc_path_to_ground(elements)
        for nd, refs in node_elems.items():
            if nd != "0" and nd not in reachable:
                out.append(Issue("FATAL", "no_dc_path",
                    f"Node '{nd}' (touches {sorted(refs)}) has no DC path to ground — "
                    f"reachable only through capacitors/current sources. ngspice can't "
                    f"fix its DC voltage, so the operating point comes from tiny gmin "
                    f"leakage, not your circuit. Fix: add a DC path (e.g. 1Meg resistor "
                    f"to ground) or seed it with .ic/.nodeset."))
    for nd, refs in node_elems.items():
        if nd != "0" and len(refs) == 1:
            out.append(Issue("WARN", "dangling_node",
                f"Node '{nd}' connects to only one pin ({next(iter(refs))}). Likely a "
                f"wiring mistake; can cause convergence trouble."))
    return out


def log_checks(sig, node_elems):
    out = []
    # ngspice is case-insensitive and lowercases node names in its messages, so
    # match its names back to our (original-case) netlist nodes case-insensitively.
    ci = {k.lower(): v for k, v in node_elems.items()}
    def touches(name):
        return sorted(node_elems.get(name) or ci.get(name.lower(), []))

    for _t, ts, label, name in sig["timestep"]:
        where = f"{label} '{name}'"
        if label == "node":
            touching = touches(name)
            if touching:
                where += f" (driven by {touching})"
        out.append(Issue("FATAL", "timestep_collapse",
            f"Transient collapsed (timestep → {ts}s); ngspice blames {where}. Something "
            f"there is changing faster than the solver can follow — a discontinuity, "
            f"chatter, or a fast switching edge. Fix: add hysteresis (Vh) for a switch, "
            f"an RC snubber, finite source rise/fall times, or a small parallel "
            f"capacitor to soften the edge at that point."))
    for nd in sig["singular_nodes"]:
        if nd.endswith("#branch"):
            dev = nd.split("#")[0]
            out.append(Issue("FATAL", "singular_branch",
                f"Singular at '{nd}': current through '{dev}' is unconstrained — two "
                f"ideal sources fighting, or a source/inductor loop with no resistance. "
                f"Fix: add series resistance or drop the redundant source '{dev}'."))
        else:
            touching = touches(nd) or ["(unknown)"]
            out.append(Issue("FATAL", "singular_node",
                f"Singular at node '{nd}' (touches {touching}); no defined DC solution. "
                f"Fix: give it a DC path to ground or a .nodeset."))
    return out


def silent_checks(sig):
    """The crown jewel: ngspice said exit 0 but the result is not trustworthy."""
    out = []
    if sig["rc"] == 0 and (sig["gmin_failed"] or sig["source_failed"]) \
            and sig["fallback_op"]:
        out.append(Issue("SILENT", "silent_fallback",
            "ngspice returned SUCCESS (exit 0) but only after gmin/source stepping "
            "FAILED and it fell back to a transient-op guess. The operating point is a "
            "relaxed estimate, not a true solution — treat these numbers as unreliable."))
    return out


# ---- orchestration -------------------------------------------------------

def run_ngspice_text(netlist_text):
    """Run a netlist string through ngspice batch mode via a temp file."""
    with tempfile.NamedTemporaryFile("w", suffix=".cir", delete=False) as f:
        f.write(netlist_text)
        tmp = f.name
    try:
        p = subprocess.run([NGSPICE, "-b", tmp],
                           capture_output=True, text=True, timeout=120)
        return p.returncode, p.stdout + p.stderr
    finally:
        Path(tmp).unlink(missing_ok=True)


def evaluate(path):
    netlist_text, source, conv_warnings = formats.load_as_netlist(path)
    elements, node_elems, _title = parse_netlist(netlist_text)
    rc, log = run_ngspice_text(netlist_text)
    sig = extract_signals(log, rc)

    issues = static_checks(elements, node_elems) \
        + log_checks(sig, node_elems) \
        + silent_checks(sig)
    for w in conv_warnings:
        issues.append(Issue("WARN", "conversion", w))
    if source != "netlist":
        issues.append(Issue("INFO", "converted",
            f"Input read as {source}. Verify the generated netlist below against "
            f"LTspice's own 'View > SPICE Netlist' before trusting the result."))
    # de-dup by code, keep most severe ordering
    seen, deduped = set(), []
    for i in sorted(issues, key=lambda x: SEVERITY_ORDER.get(x.severity, 9)):
        if i.code not in seen:
            seen.add(i.code)
            deduped.append(i)

    trust_breaking = any(i.severity in TRUST_BREAKING for i in deduped)
    verdict = ("FAILED" if rc != 0
               else "SUSPECT" if trust_breaking
               else "TRUSTWORTHY")
    return Result(str(path), verdict, rc, deduped, sig, source, netlist_text)


def exit_code(verdict):
    return {"TRUSTWORTHY": 0, "FAILED": 1, "SUSPECT": 2}[verdict]


BADGE = {"TRUSTWORTHY": "✓", "SUSPECT": "⚠", "FAILED": "✗"}


def report(r):
    print(f"\n{'='*70}\n{Path(r.path).name}\n{'='*70}")
    print(f"{BADGE[r.verdict]}  {r.verdict}   (ngspice exit {r.rc})")
    for i in r.issues:
        print(f"\n  [{i.severity}] {i.code}\n  → {i.message}")
    if not any(i.severity in TRUST_BREAKING for i in r.issues):
        print("\n  No trust issues detected.")
    if r.source != "netlist":
        print("\n  --- generated netlist ---")
        for line in r.netlist_text.strip().splitlines():
            print(f"  | {line}")


def main(argv):
    paths = argv or sorted((Path(__file__).parent / "netlists").glob("*.cir"))
    worst = 0
    for p in paths:
        r = evaluate(p)
        report(r)
        worst = max(worst, exit_code(r.verdict))
    return worst


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
