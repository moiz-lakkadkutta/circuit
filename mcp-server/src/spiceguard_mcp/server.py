"""
spiceguard MCP server: lets AI agents verify SPICE netlists they generate.

Security: every netlist is treated as UNTRUSTED. Simulation always runs in
no-exec mode — `.control` blocks and file-splicing directives (`.include`,
its `.inc`/`.incl`/`.inclu`/`.includ` prefix forms, and `.lib`/`.endl`) are
stripped before ngspice sees the text. There is deliberately no flag to
disable this. This is defense-in-depth, not a sandbox guarantee.
"""
from mcp.server.fastmcp import FastMCP

from spiceguard.core import evaluate_text
from spiceguard.ngspice import ngspice_available
from spiceguard.static_eval import evaluate_static

mcp = FastMCP("spiceguard")


def check_netlist_impl(netlist):
    """Core logic behind the check_netlist tool (plain function for tests)."""
    if not ngspice_available():
        out = evaluate_static(netlist)
        out["note"] = (
            "ngspice is not installed, so only static checks ran. "
            "Install ngspice for full verification (silent-failure detection "
            "needs a real simulation run)."
        )
        return out
    r = evaluate_text(netlist, no_exec=True, label="agent-netlist")
    return {
        "mode": "no-exec",
        "verdict": r.verdict,
        "ngspice_exit": r.rc,
        "issues": [
            {"severity": i.severity, "code": i.code, "message": i.message}
            for i in r.issues
        ],
    }


@mcp.tool()
def check_netlist(netlist: str) -> dict:
    """Check whether a SPICE simulation of this netlist can be trusted.

    ngspice often exits 0 with a plausible but WRONG answer (ungrounded
    circuits, relaxed fallback estimates). Call this after generating any
    SPICE netlist.

    Returns a dict with a "mode" key that determines which verdict
    vocabulary "verdict" uses:

    - mode="no-exec" (ngspice is installed; the normal case): a real
      simulation ran, sandboxed by stripping .control blocks and
      file-splicing directives first. verdict is one of:
      TRUSTWORTHY (simulated clean), SUSPECT (exit 0 but trust issues were
      found — read "issues" and fix them), or FAILED (the simulation
      errored).
    - mode="static-only" (ngspice is NOT installed on this machine): no
      simulation ran at all — only parser/static checks. verdict is one of:
      PASSED_STATIC (static checks found nothing; this is NOT the same
      guarantee as TRUSTWORTHY, since silent/log-based failures can only be
      caught by an actual simulation run) or SUSPECT (a static check fired).
      "note" explains that installing ngspice enables full verification.
    """
    return check_netlist_impl(netlist)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
