"""
Netlist parsing and DC-topology helpers.
"""
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

NODE_COUNT = {
    "R": 2, "C": 2, "L": 2, "V": 2, "I": 2, "D": 2,
    "B": 2, "Q": 3, "J": 3, "M": 4, "E": 4, "G": 4,
    "S": 4, "W": 4, "T": 4,
}

# Cap on subcircuit instantiation nesting depth. A cycle is already caught by
# the ancestor_chain guard; this bounds pathologically deep *acyclic* nesting so
# a crafted netlist can't exhaust the Python recursion stack (RecursionError).
MAX_SUBCKT_DEPTH = 50


@dataclass
class Element:
    refdes: str
    nodes: list
    raw: str

    @property
    def kind(self):
        # Strip any namespace prefix (e.g. "X1:C1" -> "C1") so that flattened
        # elements report their actual element type, not the instance prefix.
        base = self.refdes.rsplit(":", 1)[-1]
        return base[0].upper()


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
    """Parse netlist with subcircuit flattening.

    Returns (elements, node_elems, parse_issues).

    Handles:
    - AC-B1: continuation lines ('+')
    - AC-B2: .subckt/.ends block collection and X-instance flattening with namespacing
    - AC-B3: port count mismatch detection
    - AC-B4: .include file resolution (local files only)
    - AC-B5: soundness — subckt DC paths propagate; internal floating nodes caught
    - AC-B6: undefined subckt detection
    - Recursion guard for self/mutual referencing subckts
    """
    # Lazy import to avoid circular import (checks imports from netlist).
    def _make_issue(severity, code, message):
        try:
            from trustguard.checks import Issue  # noqa: PLC0415
        except ImportError:
            from dataclasses import make_dataclass
            Issue = make_dataclass("Issue", ["severity", "code", "message"])
        return Issue(severity, code, message)

    parse_issues = []
    base_dir = Path(base_dir)

    # --- Step 1: load text, handle .include, rejoin continuation lines -----------

    def _load_lines(src_text, src_dir, visited=None):
        """Rejoin continuation lines and splice .include content.

        Returns a flat list of preprocessed line strings.
        """
        if visited is None:
            visited = set()

        # Rejoin '+' continuation lines first.
        # Per SPICE spec, '+' continues the previous non-comment logical line.
        # Do NOT append onto a comment line (starting with '*').
        raw_lines = []
        for line in src_text.splitlines():
            s = line.strip()
            if s.startswith("+") and raw_lines and not raw_lines[-1].startswith("*"):
                raw_lines[-1] = raw_lines[-1] + " " + s[1:].strip()
            else:
                raw_lines.append(s)

        # Process .include directives.
        # Match ".include" or ".inc" as whole directive tokens (word-boundary)
        # to avoid over-matching directives like ".initial", ".incantation", etc.
        result = []
        for line in raw_lines:
            sl = line.lower()
            if re.match(r'\.(include|inc)\b', sl):
                m = re.match(r'\.inc(?:lude)?\s+"?([^"\s]+)"?', line, re.I)
                if m:
                    fname = m.group(1).strip()
                    if re.match(r'https?://', fname, re.I) or re.match(r'ftp://', fname, re.I):
                        parse_issues.append(_make_issue("WARN", "include_url",
                            f".include '{fname}' looks like a URL; skipping."))
                        continue
                    inc_path = (src_dir / fname).resolve()
                    if inc_path in visited:
                        parse_issues.append(_make_issue("WARN", "include_cycle",
                            f".include '{fname}' already included; skipping cycle."))
                        continue
                    try:
                        inc_text = inc_path.read_text()
                        visited.add(inc_path)
                        result.extend(_load_lines(inc_text, inc_path.parent, visited))
                    except (OSError, UnicodeDecodeError) as exc:
                        # OSError: missing/unreadable/dir. UnicodeDecodeError: a
                        # binary file pointed at by a (mistaken or hostile) include.
                        parse_issues.append(_make_issue("WARN", "missing_include",
                            f".include '{fname}' could not be read: {exc}"))
                    continue
            result.append(line)
        return result

    all_lines = _load_lines(text, base_dir)

    # --- Step 2: collect .subckt definitions ------------------------------------

    def _collect_defs(lines):
        """Extract .subckt/.ends blocks.

        Returns (defs, remaining_lines).
        defs maps SUBCKT_NAME -> {'ports': [str, ...], 'body': [str, ...]}.
        remaining_lines is the list of lines outside any .subckt block.
        """
        defs = {}
        remaining = []
        nesting = 0
        current_name = None
        current_ports = []
        current_body = []

        for line in lines:
            sl = line.lower().strip()
            if sl.startswith(".subckt"):
                nesting += 1
                if nesting == 1:
                    toks = line.split()
                    current_name = toks[1].upper() if len(toks) > 1 else ""
                    current_ports = [p.upper() for p in toks[2:]]
                    current_body = []
                else:
                    # nested .subckt inside body — keep for body
                    current_body.append(line)
            elif sl.startswith(".ends"):
                if nesting > 0:
                    nesting -= 1
                    if nesting == 0:
                        defs[current_name] = {
                            "ports": current_ports,
                            "body": current_body,
                        }
                        current_name = None
                        current_ports = []
                        current_body = []
                    else:
                        current_body.append(line)
                # stray .ends outside any .subckt: ignore
            elif nesting > 0:
                current_body.append(line)
            else:
                remaining.append(line)

        return defs, remaining

    defs, top_lines = _collect_defs(all_lines)

    # --- Step 3: helper to strip trailing param tokens from X-instance lines ----

    def _strip_x_params(toks):
        """Strip trailing key=value params (and optional PARAMS: keyword) from
        an already-split X-instance token list.

        SPICE syntax: X<name> node1 ... nodeK SUBCKTNAME [PARAMS:] [key=val ...]
        After stripping, toks[-1] is the subckt name and toks[1:-1] are ext nodes.
        """
        t = list(toks)
        # Remove trailing tokens that contain '=' (key=value params).
        while len(t) > 2 and "=" in t[-1]:
            t.pop()
        # Remove a trailing bare 'PARAMS:' or 'PARAMS' keyword if present.
        if len(t) > 2 and t[-1].upper().rstrip(":") == "PARAMS":
            t.pop()
        return t

    # --- Step 4: node mapping helper --------------------------------------------

    def _map_node(node, port_map, instance_name):
        """Map a single node name for a flattened instance.

        Ground '0' is always preserved.
        Ports map to their corresponding external node.
        Internal nodes are namespaced as 'instance_name:node'.
        """
        if node == "0":
            return "0"
        upper = node.upper()
        if upper in port_map:
            return port_map[upper]
        return f"{instance_name}:{node}" if instance_name else node

    # --- Step 4: recursive body flattener ---------------------------------------

    def _flatten_body(body_lines, port_map, instance_name, ancestor_chain):
        """Flatten a subckt body into Element objects.

        port_map: {PORT_UPPER: external_node_str}
        instance_name: str used to namespace internal nodes
        ancestor_chain: frozenset of subckt names being expanded (cycle guard)
        """
        if len(ancestor_chain) > MAX_SUBCKT_DEPTH:
            parse_issues.append(_make_issue("WARN", "subckt_too_deep",
                f"Subcircuit nesting exceeded {MAX_SUBCKT_DEPTH} levels at "
                f"instance '{instance_name}'. Stopping expansion here."))
            return []
        flat = []
        for line in body_lines:
            s = line.strip()
            if not s or s[0] in "*.":
                continue
            toks = s.split()
            first_upper = toks[0][0].upper()

            if toks[0][0].upper() == "X":
                # Nested X-instance inside subckt body.
                if len(toks) < 3:
                    continue
                toks = _strip_x_params(toks)
                xname = toks[0]
                sub_ref = toks[-1].upper()
                ext_raw = toks[1:-1]
                # Map the external nodes through the current port_map.
                ext_nodes = [_map_node(n, port_map, instance_name) for n in ext_raw]

                if sub_ref in ancestor_chain:
                    parse_issues.append(_make_issue("WARN", "subckt_recursion",
                        f"Subckt recursion: '{sub_ref}' is an ancestor of "
                        f"instance '{xname}'. Skipping."))
                    continue

                if sub_ref not in defs:
                    parse_issues.append(_make_issue("WARN", "undefined_subckt",
                        f"Instance '{xname}' references undefined subckt '{sub_ref}'."))
                    continue

                sub_def = defs[sub_ref]
                sub_ports = sub_def["ports"]
                if len(ext_nodes) != len(sub_ports):
                    parse_issues.append(_make_issue("WARN", "port_mismatch",
                        f"Instance '{xname}' of '{sub_ref}' provides "
                        f"{len(ext_nodes)} nodes but subckt declares "
                        f"{len(sub_ports)} ports."))
                    continue

                nested_port_map = dict(zip(sub_ports, ext_nodes))
                nested_name = f"{instance_name}:{xname}" if instance_name else xname
                nested_chain = ancestor_chain | frozenset([sub_ref])

                flat.extend(_flatten_body(
                    sub_def["body"], nested_port_map, nested_name, nested_chain
                ))
            else:
                # Regular element in subckt body.
                n = NODE_COUNT.get(first_upper)
                if n is None or len(toks) < 1 + n:
                    continue
                mapped = [_map_node(nd, port_map, instance_name)
                          for nd in toks[1:1 + n]]
                # Namespace the refdes with the instance name so that two
                # instances of the same subckt never produce colliding refdes
                # (which would cause set-collapse in node_elems and spurious
                # dangling_node / undercounting).
                namespaced_refdes = (
                    f"{instance_name}:{toks[0]}" if instance_name else toks[0]
                )
                flat.append(Element(namespaced_refdes, mapped, s))
        return flat

    # --- Step 5: parse top-level lines ------------------------------------------

    elements = []
    node_elems = defaultdict(set)

    for line in top_lines:
        s = line.strip()
        if not s or s[0] in "*.":
            continue
        toks = s.split()
        first_upper = toks[0][0].upper()

        if first_upper == "X":
            # Top-level X-instance.
            if len(toks) < 3:
                parse_issues.append(_make_issue("WARN", "undefined_subckt",
                    f"Instance '{toks[0]}' has too few tokens to parse."))
                continue
            toks = _strip_x_params(toks)
            xname = toks[0]
            sub_ref = toks[-1].upper()
            ext_nodes = toks[1:-1]

            if sub_ref not in defs:
                parse_issues.append(_make_issue("WARN", "undefined_subckt",
                    f"Instance '{xname}' references undefined subckt '{sub_ref}'."))
                continue

            sub_def = defs[sub_ref]
            sub_ports = sub_def["ports"]
            if len(ext_nodes) != len(sub_ports):
                parse_issues.append(_make_issue("WARN", "port_mismatch",
                    f"Instance '{xname}' of '{sub_ref}' provides "
                    f"{len(ext_nodes)} nodes but subckt declares "
                    f"{len(sub_ports)} ports."))
                continue

            port_map = {p: ext_nodes[i] for i, p in enumerate(sub_ports)}
            ancestor_chain = frozenset([sub_ref])

            for el in _flatten_body(sub_def["body"], port_map, xname, ancestor_chain):
                elements.append(el)
                for nd in el.nodes:
                    node_elems[nd].add(el.refdes)
        else:
            n = NODE_COUNT.get(first_upper)
            if n is None or len(toks) < 1 + n:
                continue
            el = Element(toks[0], toks[1:1 + n], s)
            elements.append(el)
            for nd in el.nodes:
                node_elems[nd].add(el.refdes)

    return elements, node_elems, parse_issues


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
