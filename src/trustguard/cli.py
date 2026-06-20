"""
Command-line interface for trustguard.
"""
import argparse
import sys
import tempfile
from pathlib import Path

import trustguard
from trustguard.core import evaluate, exit_code, report, TRUST_BREAKING
from trustguard.ngspice import NgspiceNotFound

# Known subcommands — detected manually before argparse so that positional
# FILE arguments are never mistaken for subcommand choices.  On Python 3.9+,
# argparse's _SubParsersAction raises an error even for optional subparsers
# when it encounters an unrecognised first positional token.  T5 adds its
# kicad branch by checking `command == "kicad"` in main().
_SUBCOMMANDS = frozenset({"kicad"})

# EDGE CASE NOTE: a file literally named "kicad" passed as the first positional
# argument is treated as the subcommand, not as a FILE path.  This is
# intentional and acceptable — the manual subcommand peeling happens before
# argparse so Python 3.9+ _SubParsersAction confusion is avoided.  Users with
# a file named "kicad" can work around it with "./kicad" or an absolute path.


class _ArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that exits with code 64 (usage error) instead of 2.

    Exit code 2 collides with SUSPECT, so all parse errors must use 64.
    """

    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(64, f"{self.prog}: error: {message}\n")


def _build_parser():
    """Build the main argument parser.

    Subcommand dispatch (dest='command') is handled manually in main() via
    _SUBCOMMANDS so that positional paths are never confused with subcommand
    names on Python 3.9+.  The parser itself handles options and FILE paths.
    """
    parser = _ArgumentParser(
        prog="trustguard",
        description="Evaluate SPICE netlists for simulation trustworthiness.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"trustguard {trustguard.__version__}",
    )
    parser.add_argument(
        "--ngspice",
        metavar="PATH",
        default=None,
        help="Path to the ngspice binary (overrides auto-discovery).",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        metavar="FILE",
        help="Netlist or schematic files to check.",
    )
    return parser


def _worst_exit_code(codes):
    """Return the worst exit code across a list of per-file verdict codes.

    FAILED (1) outranks SUSPECT (2) outranks TRUSTWORTHY (0).
    We cannot use max() because 2 > 1 numerically but FAILED outranks SUSPECT.
    """
    if 1 in codes:
        return 1
    if 2 in codes:
        return 2
    return 0


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    # ------------------------------------------------------------------ #
    # Step 1 — optional subcommand detection                               #
    # Peel off a leading subcommand token before argparse sees the argv.   #
    # This prevents argparse from confusing FILE paths with subcommand     #
    # names (Python 3.9+ _SubParsersAction behaviour).                    #
    # dest='command' is set on args manually to preserve the contract.    #
    # ------------------------------------------------------------------ #
    remaining = list(argv)
    command = None
    if remaining and remaining[0] in _SUBCOMMANDS:
        command = remaining.pop(0)

    # ------------------------------------------------------------------ #
    # Step 2 — parse options + paths                                       #
    # ------------------------------------------------------------------ #
    parser = _build_parser()
    args = parser.parse_args(remaining)

    # Expose subcommand on the namespace (matches dest='command' contract).
    args.command = command

    paths = args.paths
    ngspice_path = args.ngspice

    # No paths given → usage error (exit 64).
    if not paths:
        parser.print_usage(sys.stderr)
        sys.exit(64)

    # ------------------------------------------------------------------ #
    # Step 3 — dispatch                                                    #
    # ------------------------------------------------------------------ #

    if command == "kicad":
        # KiCad post-simulation hook: run kicad_preflight (ngspice-free
        # gotcha detection) on top of the standard evaluate() pass.
        # FILE '-' reads the netlist from STDIN, enabling the pipe workflow:
        #   kicad-cli sch export netlist --format spice ... | trustguard kicad -
        from trustguard import kicad as _kicad_mod
        codes = []
        try:
            for p in paths:
                if p == "-":
                    text = sys.stdin.read()
                    # Write stdin text to a temp file so evaluate() can use it.
                    with tempfile.NamedTemporaryFile(
                        "w", suffix=".cir", delete=False
                    ) as f:
                        f.write(text)
                        tmp = f.name
                    try:
                        r = evaluate(tmp, ngspice_path=ngspice_path)
                    finally:
                        Path(tmp).unlink(missing_ok=True)
                else:
                    # Call evaluate first (supports monkeypatching in tests);
                    # text is retrieved from r.netlist_text to avoid a second
                    # file read and to work correctly with format-converted inputs.
                    r = evaluate(p, ngspice_path=ngspice_path)
                    text = r.netlist_text

                # Run KiCad-specific preflight and merge any new findings.
                preflight = _kicad_mod.kicad_preflight(text)
                if preflight:
                    existing = {i.code for i in r.issues}
                    for pi in reversed(preflight):
                        if pi.code not in existing:
                            r.issues.insert(0, pi)
                            existing.add(pi.code)
                    # Recalculate verdict with augmented issues.
                    trust_breaking = any(
                        i.severity in TRUST_BREAKING for i in r.issues
                    )
                    if r.rc != 0:
                        r.verdict = "FAILED"
                    elif trust_breaking:
                        r.verdict = "SUSPECT"
                    else:
                        r.verdict = "TRUSTWORTHY"

                report(r)
                codes.append(exit_code(r.verdict))
        except NgspiceNotFound as exc:
            print(str(exc), file=sys.stderr)
            sys.exit(3)
        return _worst_exit_code(codes)

    # Default review mode.
    codes = []
    try:
        for p in paths:
            r = evaluate(p, ngspice_path=ngspice_path)
            report(r)
            codes.append(exit_code(r.verdict))
    except NgspiceNotFound as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(3)

    return _worst_exit_code(codes)


if __name__ == "__main__":
    raise SystemExit(main())
