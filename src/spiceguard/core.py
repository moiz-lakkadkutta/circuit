"""
Core evaluation orchestration: Result, evaluate, exit_code, report.
"""
from dataclasses import dataclass, field
from pathlib import Path

from spiceguard import formats
from spiceguard.checks import Issue, extract_signals, static_checks, log_checks, silent_checks
from spiceguard.netlist import parse_and_flatten
from spiceguard.ngspice import run_ngspice_text
from spiceguard.sanitize import sanitize_netlist

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


def verdict_from(rc, issues):
    """Compute a verdict string from a simulation return code and issue list.

    FAILED if rc != 0; SUSPECT if any issue.severity in TRUST_BREAKING; else
    TRUSTWORTHY.  This is the single authoritative verdict calculation used by
    evaluate(), kicad.check_kicad_netlist(), and any other site that needs to
    (re-)compute a verdict after augmenting an issue list.
    """
    if rc != 0:
        return "FAILED"
    if any(i.severity in TRUST_BREAKING for i in issues):
        return "SUSPECT"
    return "TRUSTWORTHY"


def evaluate_text(text, ngspice_path=None, no_exec=False, label="<netlist>",
                  cwd=None, extra_issues=None):
    """Evaluate a netlist given as text and return a Result.

    no_exec=True strips .control blocks and .include lines BEFORE parsing and
    simulation (see sanitize.py) — required for untrusted input (MCP, CI on
    PR-submitted netlists). Stripping is recorded as an INFO issue and never
    changes the verdict.
    """
    issues = list(extra_issues) if extra_issues else []
    if no_exec:
        san = sanitize_netlist(text)
        text = san.text
        if san.removed_blocks or san.removed_includes:
            issues.append(Issue(
                "INFO", "no_exec_stripped",
                f"no-exec mode removed {san.removed_blocks} .control block(s) "
                f"and {len(san.removed_includes)} .include line(s) before "
                f"simulation; results may differ from a full run."))

    base_dir = cwd if cwd is not None else Path(".")
    elements, node_elems, parse_issues = parse_and_flatten(text, base_dir)
    rc, log = run_ngspice_text(text, ngspice_path=ngspice_path, cwd=cwd)
    sig = extract_signals(log, rc)

    issues += parse_issues \
        + static_checks(elements, node_elems) \
        + log_checks(sig, node_elems) \
        + silent_checks(sig)

    # de-dup by code, keep most severe ordering
    seen, deduped = set(), []
    for i in sorted(issues, key=lambda x: SEVERITY_ORDER.get(x.severity, 9)):
        if i.code not in seen:
            seen.add(i.code)
            deduped.append(i)

    return Result(label, verdict_from(rc, deduped), rc, deduped, sig, "netlist", text)


def evaluate(path, ngspice_path=None, no_exec=False):
    """Evaluate a netlist (or convertible schematic) file and return a Result."""
    netlist_text, source, conv_warnings = formats.load_as_netlist(path)
    extra = [Issue("WARN", "conversion", w) for w in conv_warnings]
    if source != "netlist":
        extra.append(Issue("INFO", "converted",
            f"Input read as {source}. Verify the generated netlist below against "
            f"LTspice's own 'View > SPICE Netlist' before trusting the result."))
    r = evaluate_text(netlist_text, ngspice_path=ngspice_path, no_exec=no_exec,
                      label=str(path), cwd=Path(path).parent, extra_issues=extra)
    r.source = source
    return r


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
