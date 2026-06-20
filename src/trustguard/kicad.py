"""
KiCad post-simulation hook for trustguard (Task T5, feature C).

Public API
----------
kicad_preflight(netlist_text) -> list[Issue]
    Pure, ngspice-free check for KiCad→ngspice export gotchas.
    Can be called from the KiCad Python console after exporting a SPICE netlist.

check_kicad_netlist(path_or_text, ngspice_path=None) -> Result
    Full evaluation: preflight + ngspice simulation + trust checks.
    Accepts either a file path (str/Path) or raw netlist text.
    Designed for scripted use from KiCad's Python console or CI pipelines.
"""
import tempfile
from pathlib import Path

from trustguard.checks import Issue
from trustguard.netlist import NODE_COUNT

# Severity set that downgrades verdict from TRUSTWORTHY to SUSPECT.
_TRUST_BREAKING = {"FATAL", "SILENT", "WARN"}

# Ground-ish net names that KiCad commonly uses instead of the required node '0'.
# Checked case-insensitively against node tokens found in the netlist.
_GROUND_NETS = {"GND", "GNDA", "0V", "VSS", "AGND", "DGND", "PGND"}


def kicad_preflight(netlist_text: str) -> "list[Issue]":
    """Detect KiCad→ngspice export gotchas.  Returns a (possibly empty) list of Issues.

    Key check: ngspice requires the circuit ground to be node ``0``.  KiCad
    schematics commonly use a ``GND`` net (or GNDA/VSS/0V) that is NOT
    automatically mapped to node 0 on export.  If such a net is present and
    node 0 is absent the simulation will silently float the entire circuit,
    yielding wrong voltages without an error.

    Fix instructions are embedded in the Issue message so that users running
    ``trustguard kicad`` from the command line get actionable KiCad guidance.
    """
    issues: list[Issue] = []

    # Collect every node token mentioned in element lines.
    all_nodes: set[str] = set()
    for line_no, line in enumerate(netlist_text.splitlines()):
        s = line.strip()
        if not s or s[0] in "*.+":
            continue
        toks = s.split()
        n = NODE_COUNT.get(toks[0][0].upper())
        if n is not None and len(toks) >= 1 + n:
            for nd in toks[1 : 1 + n]:
                all_nodes.add(nd)
        elif toks[0][0].upper() == "X" and len(toks) >= 3:
            # X-instance: all tokens between refdes and subckt name are nodes.
            for nd in toks[1:-1]:
                all_nodes.add(nd)

    # Check: ground node '0' absent but a ground-ish alias present.
    if "0" not in all_nodes:
        ground_ish = {nd for nd in all_nodes if nd.upper() in _GROUND_NETS}
        if ground_ish:
            found = ", ".join(sorted(ground_ish))
            issues.append(Issue(
                severity="WARN",
                code="kicad_ground_not_zero",
                message=(
                    f"Ground net(s) {found} found but no node '0'. "
                    f"ngspice requires the ground reference to be exactly node 0. "
                    f"KiCad fix: open Symbol Properties on the GND power symbol, "
                    f"go to Simulation Model → Node mapping and set the net to '0', "
                    f"or place a PWR_FLAG tying {found} to node 0 before exporting "
                    f"the SPICE netlist."
                ),
            ))

    return issues


def check_kicad_netlist(path_or_text, ngspice_path=None):
    """Run kicad_preflight + full evaluation on a KiCad SPICE netlist.

    Parameters
    ----------
    path_or_text:
        Either a filesystem path (str or Path) to the exported ``.cir`` file,
        or the raw netlist text as a string.  When the value resolves to an
        existing file it is evaluated in-place (preserving its parent directory
        as the ngspice working directory for relative ``.include`` paths).
        Otherwise the string is treated as raw netlist text and written to a
        temporary file for evaluation.
    ngspice_path:
        Optional explicit path to the ngspice binary.

    Returns
    -------
    Result
        A trustguard Result with any kicad_preflight findings merged in before
        the verdict is computed.  A ``kicad_ground_not_zero`` WARN on an
        otherwise-clean netlist will yield SUSPECT, not TRUSTWORTHY.
    """
    # Lazy import to keep kicad.py importable without pulling in the full
    # core/ngspice stack at module load time (useful in KiCad Python console).
    from trustguard.core import evaluate
    from trustguard import formats as _formats

    p = Path(str(path_or_text))
    if p.exists() and p.is_file():
        # Use load_as_netlist so that convertible inputs (e.g. .asc) are
        # preflight-checked against the same normalised text that evaluate()
        # actually analyses, not the unconverted raw file bytes.
        text, _src, _conv_warns = _formats.load_as_netlist(str(p))
        result = evaluate(str(p), ngspice_path=ngspice_path)
    else:
        text = str(path_or_text)
        with tempfile.NamedTemporaryFile("w", suffix=".cir", delete=False) as f:
            f.write(text)
            tmp_path = f.name
        try:
            result = evaluate(tmp_path, ngspice_path=ngspice_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    # Merge preflight findings (de-dup by code; preflight inserted first).
    preflight = kicad_preflight(text)
    if preflight:
        existing_codes = {i.code for i in result.issues}
        for pi in reversed(preflight):
            if pi.code not in existing_codes:
                result.issues.insert(0, pi)
                existing_codes.add(pi.code)
        # Recalculate verdict with the augmented issue list.
        trust_breaking = any(i.severity in _TRUST_BREAKING for i in result.issues)
        if result.rc != 0:
            result.verdict = "FAILED"
        elif trust_breaking:
            result.verdict = "SUSPECT"
        else:
            result.verdict = "TRUSTWORTHY"

    return result
