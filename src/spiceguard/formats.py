"""
Input-format front-end for spiceguard.

Two paths to a runnable SPICE netlist:

1. NETLISTS (.cir/.net/.sp/...): from ngspice, LTspice, KiCad or PSpice. ngspice
   natively translates PSpice/LTspice/HSpice dialects, and KiCad emits ngspice
   netlists directly, so these are read and run as-is.

2. LTspice SCHEMATICS (.asc): converted here. EXPERIMENTAL and scoped to the
   built-in 2-pin symbols (res, cap, ind, voltage, current, diode), whose pin
   geometry is taken verbatim from the LTspice .asy files. Net connectivity is
   recovered by union-find over wire/pin/flag coordinates. For anything beyond
   these symbols, export the netlist from LTspice (View > SPICE Netlist) and feed
   that instead — that path is exact.
"""
import re
from pathlib import Path

NETLIST_EXTS = {".cir", ".net", ".sp", ".spice", ".ckt"}

# Pin offsets verified from LTspice .asy files (evenator/LTSpice-Libraries),
# ordered by SpiceOrder so node order in the emitted line is correct.
LT_PINS = {
    "res":     [(16, 16), (16, 96)],
    "ind":     [(16, 16), (16, 96)],
    "cap":     [(16, 0),  (16, 64)],
    "diode":   [(16, 0),  (16, 64)],   # anode(+), cathode(-)
    "voltage": [(0, 16),  (0, 96)],    # +, -
    "current": [(0, 16),  (0, 96)],
}
LT_PREFIX = {"res": "R", "ind": "L", "cap": "C", "diode": "D",
             "voltage": "V", "current": "I"}

# LTspice orientation transforms (integer grid, Y increases downward).
ROT = {
    "R0":   lambda x, y: (x, y),
    "R90":  lambda x, y: (-y, x),
    "R180": lambda x, y: (-x, -y),
    "R270": lambda x, y: (y, -x),
    "M0":   lambda x, y: (-x, y),
    "M90":  lambda x, y: (y, x),
    "M180": lambda x, y: (x, -y),
    "M270": lambda x, y: (-y, -x),
}


class _UF:
    def __init__(self):
        self.p = {}
    def find(self, a):
        self.p.setdefault(a, a)
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a
    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


def is_netlist(path):
    return Path(path).suffix.lower() in NETLIST_EXTS


class ConversionError(Exception):
    pass


def asc_to_netlist(text):
    """Convert an LTspice .asc schematic (built-in 2-pin symbols) to a netlist.

    Returns (netlist_text, warnings:list[str])."""
    wires, flags, symbols, directives, warnings = [], [], [], [], []
    cur = None
    for raw in text.splitlines():
        s = raw.strip()
        if not s:
            continue
        tok = s.split()
        key = tok[0].upper()
        if key == "WIRE" and len(tok) >= 5:
            wires.append(tuple(int(v) for v in tok[1:5]))
        elif key == "FLAG" and len(tok) >= 4:
            flags.append((int(tok[1]), int(tok[2]), tok[3]))
        elif key == "SYMBOL" and len(tok) >= 5:
            cur = {"sym": tok[1], "x": int(tok[2]), "y": int(tok[3]),
                   "rot": tok[4].upper(), "inst": None, "value": None}
            symbols.append(cur)
        elif key == "SYMATTR" and cur is not None and len(tok) >= 3:
            attr = tok[1].lower()
            if attr == "instname":
                cur["inst"] = tok[2]
            elif attr == "value":
                cur["value"] = " ".join(tok[2:])
        elif key == "TEXT":
            m = re.search(r"!(.+)", s)
            if m:
                # multiple directives in one TEXT are separated by literal \n
                for d in m.group(1).split("\\n"):
                    if d.strip():
                        directives.append(d.strip())

    # union-find over integer coordinate points
    uf = _UF()
    for x1, y1, x2, y2 in wires:
        uf.union((x1, y1), (x2, y2))

    # resolve each symbol's pin world-coordinates
    for sym in symbols:
        base = sym["sym"]
        if base not in LT_PINS:
            warnings.append(f"unsupported symbol '{base}' (instance "
                            f"{sym.get('inst')}) — skipped; export the netlist "
                            f"from LTspice for an exact result.")
            sym["pins"] = None
            continue
        if sym["rot"] not in ROT:
            warnings.append(f"unknown orientation '{sym['rot']}' on "
                            f"{sym.get('inst')} — assuming R0.")
        tf = ROT.get(sym["rot"], ROT["R0"])
        pins = []
        for px, py in LT_PINS[base]:
            dx, dy = tf(px, py)
            pins.append((sym["x"] + dx, sym["y"] + dy))
        sym["pins"] = pins

    # name nets: ground flag '0' wins; other flags name their net; rest auto
    net_name = {}
    for fx, fy, name in flags:
        root = uf.find((fx, fy))
        if name == "0":
            net_name[root] = "0"
        else:
            net_name.setdefault(root, name)
    auto = 0
    def name_of(pt):
        nonlocal auto
        root = uf.find(pt)
        if root not in net_name:
            auto += 1
            net_name[root] = f"N{auto:03d}"
        return net_name[root]

    # emit
    lines = ["* converted from LTspice .asc by spiceguard (experimental)"]
    need_diode_model = False
    for sym in symbols:
        if not sym.get("pins"):
            continue
        prefix = LT_PREFIX[sym["sym"]]
        inst = sym["inst"] or f"{prefix}?"
        if not inst.upper().startswith(prefix):
            inst = prefix + inst
        nets = [name_of(p) for p in sym["pins"]]
        value = sym["value"] or ""
        if sym["sym"] == "diode" and not value:
            value, need_diode_model = "Dmod", True
        lines.append(f"{inst} {' '.join(nets)} {value}".rstrip())
    if need_diode_model:
        lines.append(".model Dmod D(Is=1e-14)")
    lines += directives or [".op"]
    if not any(d.lower().startswith(".end") for d in lines):
        lines.append(".end")
    return "\n".join(lines) + "\n", warnings


def load_as_netlist(path):
    """Return (netlist_text, source_label, warnings)."""
    path = Path(path)
    text = path.read_text()
    if path.suffix.lower() == ".asc":
        netlist, warnings = asc_to_netlist(text)
        return netlist, "LTspice .asc (converted, experimental)", warnings
    return text, "netlist", []
