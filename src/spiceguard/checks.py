"""
Static and log-based issue checks for SPICE netlists.
"""
import re
from collections import defaultdict
from dataclasses import dataclass

from spiceguard.netlist import nodes_with_dc_path_to_ground


@dataclass
class Issue:
    severity: str   # FATAL | SILENT | WARN | INFO
    code: str
    message: str


# ---- log signal extraction --------------------------------------------------

RE_SINGULAR = re.compile(r"singular matrix:\s*check node\s+(\S+)", re.I)
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


# ---- rules ------------------------------------------------------------------

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
    # Topological DC-path-to-ground check.
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
