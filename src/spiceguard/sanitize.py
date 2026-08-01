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
_INCLUDE = re.compile(r"^\s*\.(include|inc)\b", re.IGNORECASE)


@dataclass
class SanitizeResult:
    text: str
    removed_blocks: int = 0
    removed_includes: list = field(default_factory=list)


def sanitize_netlist(text):
    """Strip `.control`...`.endc` blocks and `.include`/`.inc` lines.

    An unterminated `.control` block is stripped through end-of-file (fail
    closed). Returns a SanitizeResult; `text` is always newline-terminated.
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
        if _INCLUDE.match(line):
            removed_includes.append(line.strip())
            continue
        out.append(line)
    return SanitizeResult("\n".join(out) + "\n", removed_blocks, removed_includes)
