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

Every netlist passed to `check_netlist` is sanitized before simulation,
always — there is no flag to disable this. Sanitization strips:

- `.control` ... `.endc` blocks (arbitrary shell command execution), and
- file-splicing directives: `.include` and every ngspice-honored prefix
  abbreviation of it (`.inc`, `.incl`, `.inclu`, `.includ`), plus `.lib`
  (library file + section) and its `.endl` block terminator.

This is defense-in-depth against those two specific attack surfaces, not a
sandbox guarantee — the underlying spiceguard engine is a local dev/CI
utility. **Only point this server at netlists you trust the AI agent to have
generated**, and treat its verdict as a check on ngspice's result, not a
claim that arbitrary input is safe to evaluate.
