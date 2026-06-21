"""
spiceguard — answer one question about a SPICE run: can I trust this result?
"""
__version__ = "0.2.0"

from spiceguard import formats, ngspice
from spiceguard.checks import Issue
from spiceguard.core import Result, evaluate, exit_code, report
from spiceguard.netlist import parse_and_flatten, parse_netlist

__all__ = [
    "__version__",
    "evaluate",
    "parse_netlist",
    "parse_and_flatten",
    "exit_code",
    "Result",
    "report",
    "Issue",
    "formats",
    "ngspice",
]
