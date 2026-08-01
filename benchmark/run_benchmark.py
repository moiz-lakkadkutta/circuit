"""
Silent-failure benchmark: for every corpus netlist, compare what ngspice's
exit code claims against spiceguard's verdict. The headline number is the
silent-lie rate: exit-0 runs that are NOT trustworthy.

Usage: PYTHONPATH=src python3 benchmark/run_benchmark.py [--out benchmark/RESULTS.md]
Requires ngspice.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from spiceguard.core import evaluate  # noqa: E402

CORPUS_DIRS = [
    Path(__file__).parent.parent / "tests" / "netlists",
    Path(__file__).parent / "ai_generated",
]


def collect_rows():
    rows = []
    for d in CORPUS_DIRS:
        if not d.is_dir():
            continue
        for p in sorted(d.rglob("*.cir")):
            r = evaluate(str(p), no_exec=True)
            rows.append({
                "file": p.name,
                "ngspice_exit": r.rc,
                "spiceguard": r.verdict,
                "silent_lie": r.rc == 0 and r.verdict != "TRUSTWORTHY",
            })
    return rows


def format_table(rows):
    exit0 = [r for r in rows if r["ngspice_exit"] == 0]
    lies = [r for r in rows if r["silent_lie"]]
    pct = round(100 * len(lies) / len(exit0)) if exit0 else 0
    lines = [
        "# Silent-failure benchmark",
        "",
        "| netlist | ngspice exit | spiceguard verdict | silent lie? |",
        "|---|---|---|---|",
    ]
    for r in rows:
        exit_str = f"{r['ngspice_exit']} (looks fine)" if r["ngspice_exit"] == 0 \
            else str(r["ngspice_exit"])
        lie = "YES" if r["silent_lie"] else "no"
        lines.append(f"| {r['file']} | {exit_str} | {r['spiceguard']} | {lie} |")
    lines += [
        "",
        f"**{len(lies)} of {len(exit0)} exit-0 runs "
        f"({pct}%) were silently untrustworthy.**",
        "",
    ]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).parent / "RESULTS.md"))
    args = ap.parse_args()
    rows = collect_rows()
    table = format_table(rows)
    Path(args.out).write_text(table)
    print(table)


if __name__ == "__main__":
    main()
