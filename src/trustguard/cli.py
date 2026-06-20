"""
Command-line interface for trustguard.
"""
import sys
from pathlib import Path

from trustguard.core import evaluate, exit_code, report


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    paths = argv or sorted((Path(__file__).parent.parent.parent / "tests" / "netlists").glob("*.cir"))
    worst = 0
    for p in paths:
        r = evaluate(p)
        report(r)
        worst = max(worst, exit_code(r.verdict))
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
