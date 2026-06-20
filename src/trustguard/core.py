"""
Core evaluation orchestration: Result, evaluate, exit_code, report.
"""
from dataclasses import dataclass, field
from pathlib import Path

from trustguard import formats
from trustguard.checks import Issue, extract_signals, static_checks, log_checks, silent_checks
from trustguard.netlist import parse_and_flatten
from trustguard.ngspice import run_ngspice_text

SEVERITY_ORDER = {"FATAL": 0, "SILENT": 1, "WARN": 2, "INFO": 3}
TRUST_BREAKING = {"FATAL", "SILENT", "WARN"}  # INFO never lowers the verdict
BADGE = {"TRUSTWORTHY": "✓", "SUSPECT": "⚠", "FAILED": "✗"}


@dataclass
class Result:
    path: str
    verdict: str
    rc: int
    issues: list = field(default_factory=list)
    signals: dict = field(default_factory=dict)
    source: str = "netlist"
    netlist_text: str = ""


def evaluate(path, ngspice_path=None):
    """Evaluate a netlist (or convertible schematic) and return a Result."""
    netlist_text, source, conv_warnings = formats.load_as_netlist(path)
    elements, node_elems, parse_issues = parse_and_flatten(netlist_text, Path(path).parent)
    rc, log = run_ngspice_text(netlist_text, ngspice_path=ngspice_path, cwd=Path(path).parent)
    sig = extract_signals(log, rc)

    issues = parse_issues \
        + static_checks(elements, node_elems) \
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
