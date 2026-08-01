"""
Static-only evaluation: parser + static checks, NO ngspice, NO external processes,
NO filesystem. Safe to run in the browser (Pyodide) on untrusted input.

Deliberately does NOT return "TRUSTWORTHY": without running the simulator we
cannot check log/silent failures, so the best possible verdict here is
PASSED_STATIC.
"""
from pathlib import Path

from spiceguard.checks import static_checks
from spiceguard.core import SEVERITY_ORDER
from spiceguard.netlist import parse_and_flatten
from spiceguard.sanitize import sanitize_netlist


def evaluate_static(text):
    """Run sanitization + static checks on netlist text; return a plain dict."""
    san = sanitize_netlist(text)
    elements, node_elems, parse_issues = parse_and_flatten(san.text, Path("."))
    issues = parse_issues + static_checks(elements, node_elems)

    seen, deduped = set(), []
    for i in sorted(issues, key=lambda x: SEVERITY_ORDER.get(x.severity, 9)):
        if i.code not in seen:
            seen.add(i.code)
            deduped.append(i)

    trust_breaking = any(i.severity in ("FATAL", "SILENT", "WARN") for i in deduped)
    return {
        "mode": "static-only",
        "verdict": "SUSPECT" if trust_breaking else "PASSED_STATIC",
        "issues": [
            {"severity": i.severity, "code": i.code, "message": i.message}
            for i in deduped
        ],
    }
