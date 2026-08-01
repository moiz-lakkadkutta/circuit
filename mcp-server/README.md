# spiceguard-mcp

MCP server that lets AI agents (Claude Code, Cursor, ...) verify SPICE
netlists they generate. ngspice frequently exits 0 with a plausible but wrong
answer; this tool catches that.

## Install

    pip install spiceguard-mcp
    brew install ngspice   # or apt install ngspice

## Claude Code

    claude mcp add spiceguard -- spiceguard-mcp

## Security

Netlists are treated as untrusted: `.control` blocks (arbitrary shell
execution) and `.include` lines (arbitrary file reads) are stripped before
simulation, always. There is no flag to disable this.
