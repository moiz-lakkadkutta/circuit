"""
Silent-failure benchmark: for every corpus netlist, compare what ngspice's
exit code claims against spiceguard's verdict. The headline number is the
silent-lie rate: exit-0 runs that are NOT trustworthy.

Usage: PYTHONPATH=src python3 benchmark/run_benchmark.py [--out benchmark/RESULTS.md]
Requires ngspice.

Mode: this harness runs with no_exec=False (full simulation, no .control/
.include stripping). That is a deliberate, approved deviation from
spiceguard's default untrusted-input posture — the corpus (tests/netlists
and benchmark/ai_generated) is trusted first-party content (see
ai_generated/PROVENANCE.md), and no_exec=True would strip the very
`.control` blocks these netlists use to run their analysis, which manufactures
FAILED results and erases genuine silent failures from the denominator.
Never point this harness at untrusted/third-party netlists without
re-introducing no_exec=True.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import spiceguard  # noqa: E402
from spiceguard.core import evaluate  # noqa: E402

REPRO_CMD = "PYTHONPATH=src python3 benchmark/run_benchmark.py"
MODE_NOTE = (
    "no_exec=False (full simulation) — corpus is trusted first-party content, "
    "see benchmark/ai_generated/PROVENANCE.md"
)

# (slice label, directory) — kept as an ordered list so the report always
# renders curated before AI-generated regardless of filesystem order.
CORPUS_DIRS = [
    ("curated", Path(__file__).parent.parent / "tests" / "netlists"),
    ("ai_generated", Path(__file__).parent / "ai_generated"),
]


def collect_rows():
    rows = []
    for slice_name, d in CORPUS_DIRS:
        if not d.is_dir():
            continue
        for p in sorted(d.rglob("*.cir")):
            r = evaluate(str(p), no_exec=False)
            rows.append({
                "file": p.name,
                "slice": slice_name,
                "ngspice_exit": r.rc,
                "spiceguard": r.verdict,
                "silent_lie": r.rc == 0 and r.verdict != "TRUSTWORTHY",
            })
    return rows


def _summary(rows):
    """(silent-lie rows, exit-0 rows, percentage) for a set of rows."""
    exit0 = [r for r in rows if r["ngspice_exit"] == 0]
    lies = [r for r in rows if r["silent_lie"]]
    pct = round(100 * len(lies) / len(exit0)) if exit0 else 0
    return lies, exit0, pct


def _rows_table(rows):
    lines = [
        "| netlist | ngspice exit | spiceguard verdict | silent lie? |",
        "|---|---|---|---|",
    ]
    for r in rows:
        exit_str = f"{r['ngspice_exit']} (looks fine)" if r["ngspice_exit"] == 0 \
            else str(r["ngspice_exit"])
        lie = "YES" if r["silent_lie"] else "no"
        lines.append(f"| {r['file']} | {exit_str} | {r['spiceguard']} | {lie} |")
    return lines


def _slice_section(rows, title):
    lies, exit0, pct = _summary(rows)
    return [
        f"## {title}",
        "",
        *_rows_table(rows),
        "",
        f"**{len(lies)} of {len(exit0)} exit-0 runs "
        f"({pct}%) were silently untrustworthy.**",
        "",
    ]


def format_header(version=None, mode_note=MODE_NOTE, repro_cmd=REPRO_CMD):
    version = version or spiceguard.__version__
    return "\n".join([
        "# Silent-failure benchmark",
        "",
        f"- spiceguard version: {version}",
        f"- Mode: {mode_note}",
        f"- Reproduce: `{repro_cmd}`",
        "",
    ])


def format_table(rows):
    """Render curated and AI-generated slices as separate sub-tables, plus
    an overall total across both. Rows without a recognised slice are
    reported together under "Other".
    """
    lines = []
    curated = [r for r in rows if r.get("slice") == "curated"]
    ai = [r for r in rows if r.get("slice") == "ai_generated"]
    other = [r for r in rows if r.get("slice") not in ("curated", "ai_generated")]

    if curated:
        lines += _slice_section(curated, "Curated corpus (tests/netlists)")
    if ai:
        lines += _slice_section(ai, "AI-generated corpus (benchmark/ai_generated)")
    if other:
        lines += _slice_section(other, "Other")

    lies, exit0, pct = _summary(rows)
    lines += [
        "## Overall",
        "",
        f"**{len(lies)} of {len(exit0)} exit-0 runs "
        f"({pct}%) were silently untrustworthy across all slices.**",
        "",
    ]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).parent / "RESULTS.md"))
    args = ap.parse_args()
    rows = collect_rows()
    report = format_header() + "\n" + format_table(rows)
    Path(args.out).write_text(report)
    print(report)


if __name__ == "__main__":
    main()
