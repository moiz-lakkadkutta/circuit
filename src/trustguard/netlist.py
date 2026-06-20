"""
Netlist parsing and DC-topology helpers.
"""
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

NODE_COUNT = {
    "R": 2, "C": 2, "L": 2, "V": 2, "I": 2, "D": 2,
    "B": 2, "Q": 3, "J": 3, "M": 4, "E": 4, "G": 4,
    "S": 4, "W": 4, "T": 4,
}


@dataclass
class Element:
    refdes: str
    nodes: list
    raw: str

    @property
    def kind(self):
        return self.refdes[0].upper()


def parse_netlist(text):
    """Parse SPICE netlist text.

    Returns (elements, node_elems, title).
    """
    elements, node_elems, title = [], defaultdict(set), ""
    for i, line in enumerate(text.splitlines()):
        s = line.strip()
        if i == 0:
            title = s.lstrip("* ").strip()
        if not s or s[0] in "*.+":
            continue
        toks = s.split()
        n = NODE_COUNT.get(toks[0][0].upper())
        if n is None or len(toks) < 1 + n:
            continue
        el = Element(toks[0], toks[1:1 + n], s)
        elements.append(el)
        for nd in el.nodes:
            node_elems[nd].add(el.refdes)
    return elements, node_elems, title


def parse_and_flatten(text, base_dir):
    """Parse netlist and return (elements, node_elems, parse_issues).

    base_dir is a Path; ignored for now (reserved for future subcircuit resolution).
    parse_issues is always [] in this implementation.
    """
    elements, node_elems, _title = parse_netlist(text)
    return elements, node_elems, []


# Element kinds that pass DC current (provide a galvanic reference path).
# Capacitors are open at DC; current sources and VCCS (G) present infinite
# impedance, so they do NOT establish a node's DC voltage.
NON_DC_KINDS = {"C", "I", "G"}


def dc_edges(el):
    """Node pairs this element galvanically connects at DC (for reference reachability)."""
    if el.kind in NON_DC_KINDS:
        return []
    nd = el.nodes
    if el.kind in ("Q", "J") and len(nd) >= 3:          # BJT/JFET: all terminals
        return [(nd[0], nd[1]), (nd[1], nd[2]), (nd[0], nd[2])]
    if el.kind == "M" and len(nd) >= 4:                 # MOSFET d g s b: skip gate
        return [(nd[0], nd[1]), (nd[0], nd[3]), (nd[1], nd[3])]
    # R,L,V,D,B (2 terminals) and E,S,W (output/switched path = first two nodes)
    return [(nd[0], nd[1])]


def nodes_with_dc_path_to_ground(elements):
    """BFS from node '0' over DC-conducting elements; returns the reachable set."""
    adj = defaultdict(set)
    for el in elements:
        for a, b in dc_edges(el):
            adj[a].add(b)
            adj[b].add(a)
    reachable, frontier = {"0"}, ["0"]
    while frontier:
        n = frontier.pop()
        for m in adj[n]:
            if m not in reachable:
                reachable.add(m)
                frontier.append(m)
    return reachable
