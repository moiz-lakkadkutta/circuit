#!/usr/bin/env python3
"""
spiceguard ⨯ KiCad — run a trust check on a KiCad schematic or exported netlist.

KiCad has no native "post-simulation" plugin hook, and its schematic-side Python
API is limited, so the reliable integration is via the command line:

    kicad-cli sch export netlist --format spice board.kicad_sch -o board.cir
    spiceguard kicad board.cir

This script wraps that flow into one step and is usable from a terminal, a CI
job, or KiCad's built-in Python console (Tools → Scripting Console):

    python spiceguard_kicad.py board.kicad_sch     # export via kicad-cli, then check
    python spiceguard_kicad.py exported.cir        # check an already-exported netlist
    python spiceguard_kicad.py board.kicad_sch --json

Exit code is spiceguard's own: 0 TRUSTWORTHY, 1 FAILED, 2 SUSPECT,
3 ngspice-not-found, 64 usage error (and 65 here if kicad-cli is missing/fails).
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

SCH_EXTS = (".kicad_sch",)


def _which_or(path, name):
    if path:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
        sys.stderr.write(f"error: '{path}' is not an executable {name}.\n")
        sys.exit(65)
    found = shutil.which(name)
    if not found:
        sys.stderr.write(
            f"error: '{name}' not found on PATH. Install it or pass an explicit path.\n"
        )
        sys.exit(65)
    return found


def export_netlist(sch_path, kicad_cli, out_path):
    """Export a SPICE netlist from a .kicad_sch via kicad-cli."""
    cmd = [kicad_cli, "sch", "export", "netlist",
           "--format", "spice", sch_path, "-o", out_path]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.stderr.write(
            "error: kicad-cli netlist export failed:\n"
            + (proc.stderr or proc.stdout or "")
        )
        sys.exit(65)


def run_spiceguard(netlist_path, spiceguard, as_json):
    cmd = [spiceguard, "kicad"]
    if as_json:
        cmd.append("--json")
    cmd.append(netlist_path)
    # Inherit stdio so the verdict/diagnostics print straight through.
    return subprocess.run(cmd).returncode


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="spiceguard-kicad",
        description="Run spiceguard on a KiCad schematic (.kicad_sch) or exported "
                    "SPICE netlist.",
    )
    ap.add_argument("input", help="A .kicad_sch schematic or an exported netlist file.")
    ap.add_argument("--kicad-cli", default=None, help="Path to kicad-cli.")
    ap.add_argument("--spiceguard", default=None, help="Path to spiceguard.")
    ap.add_argument("--json", action="store_true", help="Pass --json to spiceguard.")
    args = ap.parse_args(argv)

    if not os.path.isfile(args.input):
        sys.stderr.write(f"error: no such file: {args.input}\n")
        sys.exit(64)

    spiceguard = _which_or(args.spiceguard, "spiceguard")

    if args.input.lower().endswith(SCH_EXTS):
        kicad_cli = _which_or(args.kicad_cli, "kicad-cli")
        # Export to a temp .cir next to nothing; spiceguard reads it directly.
        fd, tmp = tempfile.mkstemp(suffix=".cir")
        os.close(fd)
        try:
            export_netlist(args.input, kicad_cli, tmp)
            return run_spiceguard(tmp, spiceguard, args.json)
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass
    else:
        # Already a netlist — check it directly.
        return run_spiceguard(args.input, spiceguard, args.json)


if __name__ == "__main__":
    raise SystemExit(main())
