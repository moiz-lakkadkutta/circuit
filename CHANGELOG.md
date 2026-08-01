# Changelog

## 0.3.0 — 2026-08

- New: `--no-exec` mode strips `.control` blocks and `.include` lines before
  simulation — for netlists you did not write (AI-generated, PR-submitted).
- New: `spiceguard.core.evaluate_text()` — evaluate a netlist string directly.
- New: `spiceguard.static_eval.evaluate_static()` — static-only checks with
  no ngspice/subprocess/filesystem (powers the browser demo).
- New: MCP server (`mcp-server/`, published separately as `spiceguard-mcp`).
- New: silent-failure benchmark harness (`benchmark/`).

## 0.2.0

- Initial public PyPI release (CLI, KiCad subcommand, `--json`, VS Code
  extension, Docker image).
