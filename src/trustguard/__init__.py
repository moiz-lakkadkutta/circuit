"""
trustguard — answer one question about a SPICE run: can I trust this result?
"""
__version__ = "0.1.0"

from trustguard import formats, ngspice
from trustguard.checks import Issue
from trustguard.core import Result, evaluate, exit_code, report
from trustguard.netlist import parse_and_flatten, parse_netlist

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
