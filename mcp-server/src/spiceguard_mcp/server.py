"""
spiceguard MCP server: lets AI agents verify SPICE netlists they generate.

Security: every netlist is treated as UNTRUSTED. Simulation always runs in
no-exec mode (.control blocks and .include lines stripped before ngspice sees
the text). There is deliberately no flag to disable this.
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
    SPICE netlist. verdict=TRUSTWORTHY means simulated clean; SUSPECT means
    exit 0 but trust issues were found (read the issues and fix them);
    FAILED means the simulation errored.
    """
    return check_netlist_impl(netlist)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
