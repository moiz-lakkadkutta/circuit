"""
Netlist sanitizer for no-exec mode.

A SPICE netlist can execute arbitrary shell commands via `.control`/`shell`
blocks, and `.include` reads arbitrary local file paths. Paths that accept
UNTRUSTED netlists (the MCP server, CI on PR-submitted files, the web demo)
must sanitize first. Stripping happens BEFORE parsing and BEFORE ngspice ever
sees the text.
"""
import re
from dataclasses import dataclass, field

_CONTROL_START = re.compile(r"^\s*\.control\b", re.IGNORECASE)
_CONTROL_END = re.compile(r"^\s*\.endc\b", re.IGNORECASE)

# File-splicing directives: any line matching this pulls external file
# content into the netlist before ngspice ever runs it, so it must be
# stripped in no-exec mode exactly like `.control` blocks.
#
# `.inc[a-z]*` covers every prefix-abbreviation ngspice actually honors for
# `.include` — `.inc`, `.incl`, `.inclu`, `.includ`, `.include` — NOT just the
# two spellings a naive `.(include|inc)\b` pattern catches. `.lib <file>
# [section]` splices a (possibly `.control`-bearing) library file exactly
# like `.include` does, and `.endl` is its block terminator; both are
# stripped and counted alongside `.include` lines. The trailing `\b` still
# keeps this from over-matching unrelated directives such as `.ic` (initial
# condition) or a hypothetical `.library` directive.
#
# This is the single source of truth for "this line splices in file
# content" — shared with netlist.py's own include-resolution logic so the
# parser and the sanitizer never disagree about what counts as an include.
INCLUDE_DIRECTIVE = re.compile(r"^\s*\.(inc[a-z]*|lib|endl)\b", re.IGNORECASE)


@dataclass
class SanitizeResult:
    text: str
    removed_blocks: int = 0
    removed_includes: list = field(default_factory=list)


def sanitize_netlist(text):
    """Strip `.control`...`.endc` blocks and file-splicing directive lines
    (`.include`/`.inc*`/`.lib`/`.endl` — see INCLUDE_DIRECTIVE).

    An unterminated `.control` block is stripped through end-of-file (fail
    closed). Returns a SanitizeResult; `text` is always newline-terminated.
    Stripped `.lib`/`.endl` lines are counted in `removed_includes` alongside
    `.include`/`.inc*` lines — they are all file-splicing directives and
    share one accounting bucket so the interface stays stable.
    """
    out = []
    removed_blocks = 0
    removed_includes = []
    in_control = False
    for line in text.splitlines():
        if in_control:
            if _CONTROL_END.match(line):
                in_control = False
            continue
        if _CONTROL_START.match(line):
            in_control = True
            removed_blocks += 1
            continue
        if INCLUDE_DIRECTIVE.match(line):
            removed_includes.append(line.strip())
            continue
        out.append(line)
    return SanitizeResult("\n".join(out) + "\n", removed_blocks, removed_includes)
