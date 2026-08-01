# Validation Sprint Weeks 0–2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the sprint's two artifacts (landing page with client-side demo, MCP server with silent-failure benchmark) plus the security gate, repo launch hygiene, and outbound infrastructure defined in `docs/superpowers/specs/2026-08-01-monetization-validation-sprint-design.md` (v2).

**Architecture:** A new `sanitize` module gives the core package a `--no-exec` static-safe mode (strips `.control` blocks and `.include` lines before simulation). `evaluate_text()` and `evaluate_static()` expose text-input and no-ngspice entry points; the MCP server (separate optional package under `mcp-server/`) and the Pyodide landing page consume them. A benchmark harness runs the corpus through raw-ngspice-exit-code vs spiceguard-verdict and emits the launch miss-table.

**Tech Stack:** Python 3.9+ (core: zero runtime deps — this is a hard rule), `mcp` SDK (only in the separate `mcp-server/` package), Pyodide + micropip (browser), GitHub Pages via Actions, pytest.

## Global Constraints

- Core package (`src/spiceguard/`) must keep **zero third-party runtime dependencies** (README and pyproject advertise this).
- Python floor: **3.9** (no `match`, no `X | Y` type syntax, no `dataclass(kw_only=...)`).
- Tests run with: `PYTHONPATH=src python3 -m pytest -q` from repo root. Integration tests that need ngspice must auto-skip when it is absent (existing convention).
- Exit-code contract is frozen: 0 TRUSTWORTHY, 1 FAILED, 2 SUSPECT, 3 ngspice-not-found, 64 usage error. `INFO` severity never lowers a verdict (`TRUST_BREAKING = {"FATAL", "SILENT", "WARN"}` in `core.py`).
- Working branch: create `sprint/week0-2` off `docs/monetization-sprint-spec` (the spec lives there; it is not yet merged to main).
- Commit after every green task; message style: short imperative, e.g. `Add .control/.include sanitizer for no-exec mode`.
- Version bumps to **0.3.0** in Task 8 only — do not touch `pyproject.toml`/`__init__.py` version before that.
- Never weaken the existing security hardening: `-n/--no-spiceinit`, fixed argv, no `shell=True`, mkstemp temp files (guarded by `tests/test_security.py`).

---

### Task 1: `.control`/`.include` sanitizer module

**Files:**
- Create: `src/spiceguard/sanitize.py`
- Test: `tests/test_sanitize.py`

**Interfaces:**
- Produces: `sanitize_netlist(text: str) -> SanitizeResult` where `SanitizeResult` is a dataclass with fields `text: str` (cleaned netlist, always newline-terminated), `removed_blocks: int` (count of `.control`…`.endc` blocks removed), `removed_includes: list` (the stripped `.include`/`.inc` lines, whitespace-trimmed). Tasks 2, 3, 4 consume this exact signature.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_sanitize.py
"""Tests for the no-exec netlist sanitizer (security gate for MCP/CI paths)."""
from spiceguard.sanitize import sanitize_netlist


def test_strips_control_block():
    text = (
        "v1 1 0 5\n"
        ".control\n"
        "shell rm -rf /\n"
        "run\n"
        ".endc\n"
        "r1 1 0 1k\n"
        ".end\n"
    )
    res = sanitize_netlist(text)
    assert ".control" not in res.text.lower()
    assert "shell" not in res.text.lower()
    assert "v1 1 0 5" in res.text
    assert "r1 1 0 1k" in res.text
    assert res.removed_blocks == 1


def test_strips_control_case_insensitive_and_multiple():
    text = ".CONTROL\nrun\n.ENDC\nv1 1 0 1\n.Control\nprint all\n.EndC\n.end\n"
    res = sanitize_netlist(text)
    assert res.removed_blocks == 2
    assert "run" not in res.text
    assert "print all" not in res.text


def test_unterminated_control_block_strips_to_eof():
    text = "v1 1 0 5\n.control\nshell echo pwned\n"  # no .endc
    res = sanitize_netlist(text)
    assert "shell" not in res.text
    assert res.removed_blocks == 1


def test_strips_include_and_inc_lines():
    text = "v1 1 0 5\n.include /etc/passwd\n.INC secrets.lib\nr1 1 0 1k\n.end\n"
    res = sanitize_netlist(text)
    assert ".include" not in res.text.lower()
    assert ".inc" not in res.text.lower()
    assert res.removed_includes == [".include /etc/passwd", ".INC secrets.lib"]


def test_does_not_strip_element_lines_containing_inc_substring():
    # 'rinc' is an element name, not a directive; '.ic' is a legit directive.
    text = "rinc 1 0 1k\n.ic v(1)=0\n.end\n"
    res = sanitize_netlist(text)
    assert "rinc 1 0 1k" in res.text
    assert ".ic v(1)=0" in res.text
    assert res.removed_includes == []


def test_clean_netlist_passes_through_unchanged_content():
    text = "v1 1 0 5\nr1 1 0 1k\n.op\n.end\n"
    res = sanitize_netlist(text)
    assert res.text == text
    assert res.removed_blocks == 0
    assert res.removed_includes == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python3 -m pytest tests/test_sanitize.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'spiceguard.sanitize'`

- [ ] **Step 3: Write the implementation**

```python
# src/spiceguard/sanitize.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src python3 -m pytest tests/test_sanitize.py -v`
Expected: 6 passed

- [ ] **Step 5: Run the full suite to check for regressions**

Run: `PYTHONPATH=src python3 -m pytest -q`
Expected: 88 passed (82 existing + 6 new)

- [ ] **Step 6: Commit**

```bash
git add src/spiceguard/sanitize.py tests/test_sanitize.py
git commit -m "Add .control/.include sanitizer for no-exec mode"
```

---

### Task 2: `evaluate_text()` + `no_exec` wiring + CLI `--no-exec` flag

**Files:**
- Modify: `src/spiceguard/core.py` (add `evaluate_text`, refactor `evaluate` to delegate)
- Modify: `src/spiceguard/cli.py` (add `--no-exec` flag, thread through both dispatch paths)
- Test: `tests/test_no_exec.py`

**Interfaces:**
- Consumes: `sanitize_netlist` from Task 1.
- Produces:
  - `core.evaluate_text(text: str, ngspice_path=None, no_exec=False, label="<netlist>", cwd=None, extra_issues=None) -> Result` — evaluates a netlist given as a string (no file needed). Task 4 (MCP) calls this with `no_exec=True`.
  - `core.evaluate(path, ngspice_path=None, no_exec=False) -> Result` — existing signature plus `no_exec` keyword; existing callers unaffected.
  - When sanitization removed anything, the Result contains an `Issue("INFO", "no_exec_stripped", ...)`. INFO does not change the verdict.
  - CLI: `spiceguard --no-exec FILE...` and `spiceguard kicad --no-exec FILE...` (kicad path gains it via `evaluate` inside `check_kicad_netlist`? — no: `check_kicad_netlist` takes text; the CLI kicad branch does NOT get `--no-exec` in this task; the flag applies to the default review path only, and `--help` says so).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_no_exec.py
"""Tests for no-exec mode wiring through core and CLI."""
import pytest

from spiceguard import core
from spiceguard.checks import Issue


@pytest.fixture
def fake_ngspice(monkeypatch):
    """Capture the text handed to ngspice; pretend the sim succeeded."""
    captured = {}

    def fake_run(text, ngspice_path=None, cwd=None):
        captured["text"] = text
        return 0, "No. of Data Rows : 1\n"

    monkeypatch.setattr(core, "run_ngspice_text", fake_run)
    return captured


HOSTILE = (
    "v1 1 0 5\n"
    "r1 1 0 1k\n"
    ".control\n"
    "shell echo pwned\n"
    ".endc\n"
    ".include /etc/passwd\n"
    ".op\n"
    ".end\n"
)


def test_evaluate_text_no_exec_strips_before_ngspice(fake_ngspice):
    r = core.evaluate_text(HOSTILE, no_exec=True)
    assert "shell" not in fake_ngspice["text"]
    assert ".include" not in fake_ngspice["text"]
    codes = [i.code for i in r.issues]
    assert "no_exec_stripped" in codes
    stripped = next(i for i in r.issues if i.code == "no_exec_stripped")
    assert stripped.severity == "INFO"


def test_evaluate_text_no_exec_info_does_not_lower_verdict(fake_ngspice):
    clean_plus_control = "v1 1 0 5\nr1 1 0 1k\n.control\nrun\n.endc\n.op\n.end\n"
    r = core.evaluate_text(clean_plus_control, no_exec=True)
    assert r.verdict == "TRUSTWORTHY"


def test_evaluate_text_default_mode_leaves_text_alone(fake_ngspice):
    core.evaluate_text(HOSTILE, no_exec=False)
    assert ".control" in fake_ngspice["text"]


def test_evaluate_text_label_becomes_result_path(fake_ngspice):
    r = core.evaluate_text("v1 1 0 5\n.op\n.end\n", label="from-mcp")
    assert r.path == "from-mcp"


def test_evaluate_file_passes_no_exec_through(fake_ngspice, tmp_path):
    p = tmp_path / "hostile.cir"
    p.write_text(HOSTILE)
    r = core.evaluate(str(p), no_exec=True)
    assert "shell" not in fake_ngspice["text"]
    assert "no_exec_stripped" in [i.code for i in r.issues]


def test_cli_accepts_no_exec_flag(monkeypatch, tmp_path, capsys):
    from spiceguard import cli

    p = tmp_path / "ok.cir"
    p.write_text("v1 1 0 5\nr1 1 0 1k\n.control\nrun\n.endc\n.op\n.end\n")

    def fake_run(text, ngspice_path=None, cwd=None):
        assert ".control" not in text
        return 0, "No. of Data Rows : 1\n"

    monkeypatch.setattr(core, "run_ngspice_text", fake_run)
    rc = cli.main(["--no-exec", str(p)])
    assert rc == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python3 -m pytest tests/test_no_exec.py -v`
Expected: FAIL — `evaluate_text` does not exist; `--no-exec` unrecognized (exit 64).

- [ ] **Step 3: Implement `evaluate_text` and refactor `evaluate` in core.py**

Replace the current `evaluate()` in `src/spiceguard/core.py` with (imports: add `from spiceguard.sanitize import sanitize_netlist` at top):

```python
def evaluate_text(text, ngspice_path=None, no_exec=False, label="<netlist>",
                  cwd=None, extra_issues=None):
    """Evaluate a netlist given as text and return a Result.

    no_exec=True strips .control blocks and .include lines BEFORE parsing and
    simulation (see sanitize.py) — required for untrusted input (MCP, CI on
    PR-submitted netlists). Stripping is recorded as an INFO issue and never
    changes the verdict.
    """
    issues = list(extra_issues) if extra_issues else []
    if no_exec:
        san = sanitize_netlist(text)
        text = san.text
        if san.removed_blocks or san.removed_includes:
            issues.append(Issue(
                "INFO", "no_exec_stripped",
                f"no-exec mode removed {san.removed_blocks} .control block(s) "
                f"and {len(san.removed_includes)} .include line(s) before "
                f"simulation; results may differ from a full run."))

    base_dir = cwd if cwd is not None else Path(".")
    elements, node_elems, parse_issues = parse_and_flatten(text, base_dir)
    rc, log = run_ngspice_text(text, ngspice_path=ngspice_path, cwd=cwd)
    sig = extract_signals(log, rc)

    issues += parse_issues \
        + static_checks(elements, node_elems) \
        + log_checks(sig, node_elems) \
        + silent_checks(sig)

    # de-dup by code, keep most severe ordering
    seen, deduped = set(), []
    for i in sorted(issues, key=lambda x: SEVERITY_ORDER.get(x.severity, 9)):
        if i.code not in seen:
            seen.add(i.code)
            deduped.append(i)

    return Result(label, verdict_from(rc, deduped), rc, deduped, sig, "netlist", text)


def evaluate(path, ngspice_path=None, no_exec=False):
    """Evaluate a netlist (or convertible schematic) file and return a Result."""
    netlist_text, source, conv_warnings = formats.load_as_netlist(path)
    extra = [Issue("WARN", "conversion", w) for w in conv_warnings]
    if source != "netlist":
        extra.append(Issue("INFO", "converted",
            f"Input read as {source}. Verify the generated netlist below against "
            f"LTspice's own 'View > SPICE Netlist' before trusting the result."))
    r = evaluate_text(netlist_text, ngspice_path=ngspice_path, no_exec=no_exec,
                      label=str(path), cwd=Path(path).parent, extra_issues=extra)
    r.source = source
    return r
```

- [ ] **Step 4: Add the CLI flag in cli.py**

In `_build_parser()`, after the `--json` argument:

```python
    parser.add_argument(
        "--no-exec",
        action="store_true",
        dest="no_exec",
        help="Strip .control blocks and .include lines before simulation. "
             "Use for netlists you did not write (AI-generated, PR-submitted). "
             "Applies to the default review mode.",
    )
```

In `main()`, default review loop, change the `evaluate` call to:

```python
            r = evaluate(p, ngspice_path=ngspice_path, no_exec=args.no_exec)
```

- [ ] **Step 5: Run tests to verify they pass, then full suite**

Run: `PYTHONPATH=src python3 -m pytest tests/test_no_exec.py -v` → 6 passed
Run: `PYTHONPATH=src python3 -m pytest -q` → 94 passed

- [ ] **Step 6: Commit**

```bash
git add src/spiceguard/core.py src/spiceguard/cli.py tests/test_no_exec.py
git commit -m "Add evaluate_text and --no-exec mode for untrusted netlists"
```

---

### Task 3: `evaluate_static()` — no-ngspice evaluation for the browser demo

**Files:**
- Create: `src/spiceguard/static_eval.py`
- Test: `tests/test_static_eval.py`

**Interfaces:**
- Consumes: `sanitize_netlist` (Task 1), `parse_and_flatten`, `static_checks`, `SEVERITY_ORDER`.
- Produces: `evaluate_static(text: str) -> dict` returning
  `{"mode": "static-only", "verdict": "SUSPECT"|"PASSED_STATIC", "issues": [{"severity", "code", "message"}, ...]}`.
  It must be importable and runnable with **no ngspice, no subprocess, no filesystem access** — Pyodide (Task 6) calls exactly this. `PASSED_STATIC` (not `TRUSTWORTHY`) is deliberate: static checks alone must never claim full trust.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_static_eval.py
"""Tests for the static-only evaluator (Pyodide/browser path)."""
from spiceguard.static_eval import evaluate_static


def test_missing_ground_flagged_without_ngspice():
    r = evaluate_static("v1 1 2 5\nr1 1 2 1k\n.op\n.end\n")
    assert r["mode"] == "static-only"
    assert r["verdict"] == "SUSPECT"
    assert "no_ground" in [i["code"] for i in r["issues"]]


def test_healthy_netlist_passes_static_not_trustworthy():
    r = evaluate_static("v1 1 0 5\nr1 1 0 1k\n.op\n.end\n")
    assert r["verdict"] == "PASSED_STATIC"
    assert r["verdict"] != "TRUSTWORTHY"  # static-only must never claim full trust


def test_hostile_input_is_sanitized_and_never_executed():
    r = evaluate_static(".control\nshell echo pwned\n.endc\nv1 1 0 5\n.op\n.end\n")
    assert isinstance(r, dict)  # completes without subprocess/OS access


def test_no_subprocess_import():
    import spiceguard.static_eval as m
    import inspect
    src = inspect.getsource(m)
    assert "subprocess" not in src
    assert "run_ngspice" not in src
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python3 -m pytest tests/test_static_eval.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# src/spiceguard/static_eval.py
"""
Static-only evaluation: parser + static checks, NO ngspice, NO subprocess,
NO filesystem. Safe to run in the browser (Pyodide) on untrusted input.

Deliberately does NOT return "TRUSTWORTHY": without running the simulator we
cannot check log/silent failures, so the best possible verdict here is
PASSED_STATIC.
"""
from pathlib import Path

from spiceguard.checks import static_checks
from spiceguard.core import SEVERITY_ORDER
from spiceguard.netlist import parse_and_flatten
from spiceguard.sanitize import sanitize_netlist


def evaluate_static(text):
    """Run sanitization + static checks on netlist text; return a plain dict."""
    san = sanitize_netlist(text)
    elements, node_elems, parse_issues = parse_and_flatten(san.text, Path("."))
    issues = parse_issues + static_checks(elements, node_elems)

    seen, deduped = set(), []
    for i in sorted(issues, key=lambda x: SEVERITY_ORDER.get(x.severity, 9)):
        if i.code not in seen:
            seen.add(i.code)
            deduped.append(i)

    trust_breaking = any(i.severity in ("FATAL", "SILENT", "WARN") for i in deduped)
    return {
        "mode": "static-only",
        "verdict": "SUSPECT" if trust_breaking else "PASSED_STATIC",
        "issues": [
            {"severity": i.severity, "code": i.code, "message": i.message}
            for i in deduped
        ],
    }
```

Note: `parse_and_flatten` receives already-sanitized text, so its `.include` resolution path is never reached (includes were stripped) — no filesystem access happens. `Path(".")` is a dummy base dir.

- [ ] **Step 4: Run tests, then full suite**

Run: `PYTHONPATH=src python3 -m pytest tests/test_static_eval.py -v` → 4 passed
Run: `PYTHONPATH=src python3 -m pytest -q` → 98 passed

- [ ] **Step 5: Commit**

```bash
git add src/spiceguard/static_eval.py tests/test_static_eval.py
git commit -m "Add static-only evaluator for browser/Pyodide use"
```

---

### Task 4: MCP server package (`mcp-server/`)

**Files:**
- Create: `mcp-server/pyproject.toml`
- Create: `mcp-server/src/spiceguard_mcp/__init__.py`
- Create: `mcp-server/src/spiceguard_mcp/server.py`
- Create: `mcp-server/README.md`
- Test: `tests/test_mcp_impl.py` (tests the impl functions directly; MCP protocol layer is exercised by the manual smoke test)

**Interfaces:**
- Consumes: `core.evaluate_text(text, no_exec=True, label=...)` (Task 2), `static_eval.evaluate_static` (Task 3), `ngspice_available()` from `spiceguard.ngspice`.
- Produces: pip-installable package `spiceguard-mcp` with console script `spiceguard-mcp` (stdio MCP server) exposing one tool `check_netlist(netlist: str) -> dict`. The impl function `check_netlist_impl(netlist: str) -> dict` is importable for testing. **Every** simulation goes through `no_exec=True` — there is no bypass flag.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_mcp_impl.py
"""Tests for the MCP server implementation functions (not the protocol layer)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "mcp-server" / "src"))

from spiceguard import core  # noqa: E402
from spiceguard_mcp.server import check_netlist_impl  # noqa: E402


def test_returns_structured_dict_with_verdict(monkeypatch):
    monkeypatch.setattr(core, "run_ngspice_text",
                        lambda text, ngspice_path=None, cwd=None: (0, "ok"))
    out = check_netlist_impl("v1 1 0 5\nr1 1 0 1k\n.op\n.end\n")
    assert out["verdict"] in ("TRUSTWORTHY", "SUSPECT", "FAILED")
    assert out["mode"] == "no-exec"
    assert isinstance(out["issues"], list)


def test_hostile_netlist_never_reaches_ngspice_unsanitized(monkeypatch):
    seen = {}

    def fake_run(text, ngspice_path=None, cwd=None):
        seen["text"] = text
        return 0, "ok"

    monkeypatch.setattr(core, "run_ngspice_text", fake_run)
    check_netlist_impl(".control\nshell echo pwned\n.endc\nv1 1 0 5\n.op\n.end\n")
    assert "shell" not in seen["text"]


def test_falls_back_to_static_when_ngspice_missing(monkeypatch):
    import spiceguard_mcp.server as srv
    monkeypatch.setattr(srv, "ngspice_available", lambda: False)
    out = check_netlist_impl("v1 1 2 5\nr1 1 2 1k\n.op\n.end\n")
    assert out["mode"] == "static-only"
    assert "no_ground" in [i["code"] for i in out["issues"]]
    assert "install ngspice" in out["note"].lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python3 -m pytest tests/test_mcp_impl.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'spiceguard_mcp'`

- [ ] **Step 3: Create the package**

`mcp-server/pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "spiceguard-mcp"
version = "0.1.0"
description = "MCP server so AI agents can check whether a SPICE simulation result can be trusted."
readme = "README.md"
requires-python = ">=3.10"
license = { text = "MIT" }
authors = [{ name = "Moiz Lakkadkutta", email = "moizlakkadkutta1@gmail.com" }]
dependencies = ["mcp>=1.0", "spiceguard>=0.3.0"]

[project.scripts]
spiceguard-mcp = "spiceguard_mcp.server:main"

[tool.setuptools.packages.find]
where = ["src"]
```

(Note: `mcp` SDK requires Python ≥3.10; that constraint stays in THIS package only — core stays 3.9.)

`mcp-server/src/spiceguard_mcp/__init__.py`:

```python
__version__ = "0.1.0"
```

`mcp-server/src/spiceguard_mcp/server.py`:

```python
"""
spiceguard MCP server: lets AI agents verify SPICE netlists they generate.

Security: every netlist is treated as UNTRUSTED. Simulation always runs in
no-exec mode (.control blocks and .include lines stripped before ngspice sees
the text). There is deliberately no flag to disable this.
"""
from mcp.server.fastmcp import FastMCP

from spiceguard.core import evaluate_text
from spiceguard.ngspice import ngspice_available
from spiceguard.static_eval import evaluate_static

mcp = FastMCP("spiceguard")


def check_netlist_impl(netlist):
    """Core logic behind the check_netlist tool (plain function for tests)."""
    if not ngspice_available():
        out = evaluate_static(netlist)
        out["note"] = (
            "ngspice is not installed, so only static checks ran. "
            "Install ngspice for full verification (silent-failure detection "
            "needs a real simulation run)."
        )
        return out
    r = evaluate_text(netlist, no_exec=True, label="agent-netlist")
    return {
        "mode": "no-exec",
        "verdict": r.verdict,
        "ngspice_exit": r.rc,
        "issues": [
            {"severity": i.severity, "code": i.code, "message": i.message}
            for i in r.issues
        ],
    }


@mcp.tool()
def check_netlist(netlist: str) -> dict:
    """Check whether a SPICE simulation of this netlist can be trusted.

    ngspice often exits 0 with a plausible but WRONG answer (ungrounded
    circuits, relaxed fallback estimates). Call this after generating any
    SPICE netlist. verdict=TRUSTWORTHY means simulated clean; SUSPECT means
    exit 0 but trust issues were found (read the issues and fix them);
    FAILED means the simulation errored.
    """
    return check_netlist_impl(netlist)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
```

`mcp-server/README.md`:

```markdown
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
```

- [ ] **Step 4: Install the mcp SDK into the dev environment and run tests**

Run: `python3 -m pip install "mcp>=1.0"` (dev-only dependency; core package remains zero-dep)
Run: `PYTHONPATH=src python3 -m pytest tests/test_mcp_impl.py -v`
Expected: 3 passed. If the sandbox blocks pip, record the block and run the tests in whatever environment the user uses for development.

- [ ] **Step 5: Manual smoke test (requires ngspice; skip and note if absent)**

Run: `PYTHONPATH=src:mcp-server/src python3 -c "from spiceguard_mcp.server import check_netlist_impl; import json; print(json.dumps(check_netlist_impl('v1 1 2 5\nr1 1 2 1k\n.op\n.end\n'), indent=2))"`
Expected: JSON with `"verdict": "SUSPECT"` and a `no_ground` issue.

- [ ] **Step 6: Run full suite, commit**

Run: `PYTHONPATH=src python3 -m pytest -q` → 101 passed

```bash
git add mcp-server/ tests/test_mcp_impl.py
git commit -m "Add spiceguard-mcp: MCP server with always-on no-exec mode"
```

---

### Task 5: Silent-failure benchmark harness + AI-generated corpus

**Files:**
- Create: `benchmark/run_benchmark.py`
- Create: `benchmark/README.md`
- Create: `benchmark/ai_generated/` (~20 `.cir` files + `PROVENANCE.md`)
- Test: `tests/test_benchmark.py`

**Interfaces:**
- Consumes: `core.evaluate(path, no_exec=True)`.
- Produces: `python3 benchmark/run_benchmark.py [--out benchmark/RESULTS.md]` — runs every `.cir` under `tests/netlists/` and `benchmark/ai_generated/`, emits a markdown table. Pure function `format_table(rows: list[dict]) -> str` where each row is `{"file", "ngspice_exit", "spiceguard", "silent_lie"}` — this is the unit-testable seam. `silent_lie` is True iff ngspice exit == 0 AND verdict != TRUSTWORTHY: the headline number for the launch post.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_benchmark.py
"""Tests for the benchmark table formatter."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "benchmark"))

from run_benchmark import format_table  # noqa: E402


def test_table_counts_silent_lies():
    rows = [
        {"file": "a.cir", "ngspice_exit": 0, "spiceguard": "TRUSTWORTHY", "silent_lie": False},
        {"file": "b.cir", "ngspice_exit": 0, "spiceguard": "SUSPECT", "silent_lie": True},
        {"file": "c.cir", "ngspice_exit": 1, "spiceguard": "FAILED", "silent_lie": False},
    ]
    out = format_table(rows)
    assert "| b.cir | 0 (looks fine) | SUSPECT | YES |" in out
    assert "1 of 2 exit-0 runs (50%) were silently untrustworthy" in out


def test_table_handles_zero_exit_zero_runs():
    rows = [{"file": "c.cir", "ngspice_exit": 1, "spiceguard": "FAILED", "silent_lie": False}]
    out = format_table(rows)
    assert "0 of 0" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python3 -m pytest tests/test_benchmark.py -v`
Expected: FAIL with import error.

- [ ] **Step 3: Write the harness**

```python
# benchmark/run_benchmark.py
"""
Silent-failure benchmark: for every corpus netlist, compare what ngspice's
exit code claims against spiceguard's verdict. The headline number is the
silent-lie rate: exit-0 runs that are NOT trustworthy.

Usage: PYTHONPATH=src python3 benchmark/run_benchmark.py [--out benchmark/RESULTS.md]
Requires ngspice.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from spiceguard.core import evaluate  # noqa: E402

CORPUS_DIRS = [
    Path(__file__).parent.parent / "tests" / "netlists",
    Path(__file__).parent / "ai_generated",
]


def collect_rows():
    rows = []
    for d in CORPUS_DIRS:
        if not d.is_dir():
            continue
        for p in sorted(d.rglob("*.cir")):
            r = evaluate(str(p), no_exec=True)
            rows.append({
                "file": p.name,
                "ngspice_exit": r.rc,
                "spiceguard": r.verdict,
                "silent_lie": r.rc == 0 and r.verdict != "TRUSTWORTHY",
            })
    return rows


def format_table(rows):
    exit0 = [r for r in rows if r["ngspice_exit"] == 0]
    lies = [r for r in rows if r["silent_lie"]]
    pct = round(100 * len(lies) / len(exit0)) if exit0 else 0
    lines = [
        "# Silent-failure benchmark",
        "",
        "| netlist | ngspice exit | spiceguard verdict | silent lie? |",
        "|---|---|---|---|",
    ]
    for r in rows:
        exit_str = f"{r['ngspice_exit']} (looks fine)" if r["ngspice_exit"] == 0 \
            else str(r["ngspice_exit"])
        lie = "YES" if r["silent_lie"] else "no"
        lines.append(f"| {r['file']} | {exit_str} | {r['spiceguard']} | {lie} |")
    lines += [
        "",
        f"**{len(lies)} of {len(exit0)} exit-0 runs "
        f"({pct}%) were silently untrustworthy.**",
        "",
    ]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).parent / "RESULTS.md"))
    args = ap.parse_args()
    rows = collect_rows()
    table = format_table(rows)
    Path(args.out).write_text(table)
    print(table)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python3 -m pytest tests/test_benchmark.py -v` → 2 passed

- [ ] **Step 5: Generate the AI corpus (~20 netlists)**

Create `benchmark/ai_generated/` and generate 20 netlists by prompting an LLM (Claude) with realistic requests a hobbyist would make — do NOT cherry-pick for failures; take the first answer each time. Ten prompts, two variants each, e.g.:

1. "Write a SPICE netlist for a voltage divider: 9V battery, 10k and 4.7k resistors, measure the midpoint."
2. "SPICE netlist for an RC low-pass filter, 1kHz cutoff, transient analysis."
3. "Netlist for an LED + current-limiting resistor from 5V."
4. "A 555-timer-style relaxation oscillator using a comparator model."
5. "Half-wave rectifier with 1N4148 and smoothing cap, 50Hz input."
6. "Common-emitter NPN amplifier, 12V rail, show the bias point."
7. "Buck converter power stage with ideal switch, 12V→5V."
8. "Two op-amp Sallen-Key low-pass at 10kHz (use a subcircuit)."
9. "Capacitively coupled two-stage RC network, AC analysis."
10. "Current mirror with two NPNs from a 1mA reference."

Save as `ai_01_divider.cir` … `ai_20_mirror_v2.cir`. Write `benchmark/ai_generated/PROVENANCE.md` recording: model used, date, the exact prompt per file, and the no-cherry-picking rule. This provenance is what makes the launch number defensible.

- [ ] **Step 6: Run the real benchmark (requires ngspice)**

Run: `PYTHONPATH=src python3 benchmark/run_benchmark.py`
Expected: `benchmark/RESULTS.md` written; table includes both corpora. Record the silent-lie percentage — it is the launch headline. If ngspice is unavailable in this environment, mark this step deferred and run before launch.

- [ ] **Step 7: Write `benchmark/README.md`**

```markdown
# Silent-failure benchmark

Compares what ngspice's exit code claims vs what spiceguard's verdict finds,
over (a) the curated test corpus and (b) 20 un-cherry-picked AI-generated
netlists (see ai_generated/PROVENANCE.md).

Run: PYTHONPATH=src python3 benchmark/run_benchmark.py

Want to add a netlist that fooled ngspice? Open an issue with the netlist and
what the correct behaviour should have been — corpus contributions are the
most valuable kind.
```

- [ ] **Step 8: Full suite + commit**

```bash
PYTHONPATH=src python3 -m pytest -q   # 103 passed
git add benchmark/ tests/test_benchmark.py
git commit -m "Add silent-failure benchmark harness and AI-generated corpus"
```

---

### Task 6: Landing page with Pyodide demo + waitlist + GitHub Pages deploy

**Files:**
- Create: `site/index.html`
- Create: `site/app.js`
- Create: `site/style.css`
- Create: `.github/workflows/pages.yml`

**Interfaces:**
- Consumes: `spiceguard.static_eval.evaluate_static` (Task 3) via a wheel built in CI and loaded by micropip.
- Produces: static site deployed to GitHub Pages. Waitlist form posts to a Formspree endpoint with a **required** `usage` select (`ci` / `ai-agent` / `editor` / `other`) — this is the spec's attribution question. Links shared per-channel get `?src=<channel>`; the form stores it in a hidden field.

- [ ] **Step 1: Create the page skeleton**

`site/index.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>spiceguard — can you trust that SPICE result?</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<main>
  <h1>ngspice said exit 0.<br>The answer was still wrong.</h1>
  <p class="lead">
    Modern ngspice recovers from many problems on its own — and when it can't,
    it often returns <strong>exit code 0 with a plausible but wrong answer</strong>:
    a relaxed fallback estimate, or arbitrary voltages on an ungrounded node.
    Nothing warns you. <code>spiceguard</code> answers one question:
    <em>can I trust this result?</em>
  </p>

  <section id="demo">
    <h2>Try it — right here, no install</h2>
    <p>Static checks run in your browser via Pyodide. Nothing is uploaded.</p>
    <textarea id="netlist" rows="10" spellcheck="false">* AI-generated "voltage divider" — spot the problem
v1 1 2 9
r1 1 2 10k
r2 2 3 4.7k
.op
.end</textarea>
    <button id="check" disabled>Loading Python…</button>
    <pre id="result" hidden></pre>
    <p class="fineprint">Static checks only — the full CLI also runs the
      simulation and decodes ngspice's failure log.
      <code>pip install spiceguard</code></p>
  </section>

  <section id="waitlist">
    <h2>Trust checks where you actually need them</h2>
    <p>We're building spiceguard into CI pipelines and AI-agent workflows.
       Join the beta list:</p>
    <form id="signup" action="https://formspree.io/f/FORMSPREE_ID" method="POST">
      <input type="email" name="email" required placeholder="you@company.com">
      <select name="usage" required>
        <option value="" disabled selected>How would you use this?</option>
        <option value="ci">CI checks on pull requests</option>
        <option value="ai-agent">Verifying AI-generated circuits</option>
        <option value="editor">Checks in my editor</option>
        <option value="other">Something else</option>
      </select>
      <input type="hidden" name="src" id="src-field" value="direct">
      <button type="submit">Join the beta</button>
    </form>
  </section>

  <footer>
    <a href="https://github.com/moiz-lakkadkutta/circuit">GitHub</a> ·
    <a href="https://pypi.org/project/spiceguard/">PyPI</a> · MIT licensed ·
    zero runtime dependencies
  </footer>
</main>
<script type="module" src="app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Write the Pyodide glue**

`site/app.js`:

```js
const btn = document.getElementById("check");
const result = document.getElementById("result");
const netlist = document.getElementById("netlist");

// Per-channel attribution: links are shared as ?src=hn, ?src=kicad-forum, ...
const src = new URLSearchParams(location.search).get("src");
if (src) document.getElementById("src-field").value = src;

async function boot() {
  const { loadPyodide } = await import(
    "https://cdn.jsdelivr.net/pyodide/v0.26.1/full/pyodide.mjs");
  const pyodide = await loadPyodide();
  await pyodide.loadPackage("micropip");
  const micropip = pyodide.pyimport("micropip");
  // The wheel is built and copied into site/wheels/ by the Pages workflow.
  const wheelName = document.querySelector('meta[name="spiceguard-wheel"]')
    ?.content ?? "wheels/spiceguard-0.3.0-py3-none-any.whl";
  await micropip.install(wheelName);

  btn.disabled = false;
  btn.textContent = "Check my netlist";
  btn.addEventListener("click", () => {
    pyodide.globals.set("netlist_text", netlist.value);
    const raw = pyodide.runPython(`
import json
from spiceguard.static_eval import evaluate_static
json.dumps(evaluate_static(netlist_text))
`);
    const r = JSON.parse(raw);
    result.hidden = false;
    const lines = [`verdict: ${r.verdict}  (${r.mode})`];
    for (const i of r.issues) {
      lines.push(`\n[${i.severity}] ${i.code}\n→ ${i.message}`);
    }
    if (r.issues.length === 0) lines.push("\nNo static trust issues found.");
    result.textContent = lines.join("\n");
  });
}

boot().catch((e) => {
  btn.textContent = "Demo failed to load — see console";
  console.error(e);
});
```

`site/style.css` — minimal, dark-friendly:

```css
:root { color-scheme: light dark; }
body { font: 16px/1.6 system-ui, sans-serif; margin: 0; }
main { max-width: 42rem; margin: 0 auto; padding: 2rem 1rem 4rem; }
h1 { font-size: 2rem; line-height: 1.2; }
.lead { font-size: 1.1rem; }
textarea { width: 100%; font-family: ui-monospace, monospace; font-size: 0.9rem;
  box-sizing: border-box; }
button { padding: 0.6rem 1.2rem; font-size: 1rem; cursor: pointer; }
pre { background: rgba(127,127,127,0.12); padding: 1rem; overflow-x: auto; }
form { display: grid; gap: 0.5rem; max-width: 24rem; }
input, select { padding: 0.5rem; font-size: 1rem; }
.fineprint { font-size: 0.85rem; opacity: 0.75; }
footer { margin-top: 3rem; font-size: 0.9rem; opacity: 0.8; }
```

- [ ] **Step 3: Create the Pages workflow**

`.github/workflows/pages.yml`:

```yaml
name: Deploy site
on:
  push:
    branches: [main]
    paths: ["site/**", "src/**", "pyproject.toml", ".github/workflows/pages.yml"]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - name: Build wheel into site/wheels
        run: |
          python -m pip install build
          python -m build --wheel --outdir site/wheels
          ls site/wheels
      - name: Point the page at the built wheel
        run: |
          WHEEL=$(basename site/wheels/*.whl)
          sed -i "s|wheels/spiceguard-[^\"']*\.whl|wheels/$WHEEL|" site/app.js
      - uses: actions/upload-pages-artifact@v3
        with: { path: site }
      - id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 4: External-service setup (founder action, ~10 min)**

1. Create a free Formspree form; replace `FORMSPREE_ID` in `site/index.html` with the real form id.
2. In repo Settings → Pages, set Source to "GitHub Actions".
These are the only two manual configuration points; both are grep-able (`grep -rn FORMSPREE_ID site/`).

- [ ] **Step 5: Local verification**

Run: `cd site && python3 -m http.server 8080` and open `http://localhost:8080?src=test`.
Check: demo loads (needs a locally built wheel: `python3 -m build --wheel --outdir site/wheels` first), the sample netlist yields `SUSPECT` with `no_ground`, the hidden `src` field is `test`, and the form refuses to submit without a `usage` selection.

- [ ] **Step 6: Commit**

```bash
printf "site/wheels/\n" >> .gitignore
git add site/ .github/workflows/pages.yml .gitignore
git commit -m "Add landing page with in-browser static demo and beta waitlist"
```

---

### Task 7: README launch cleanup, CONTRIBUTING + DCO, repo hygiene

**Files:**
- Modify: `README.md` (restructure lead; history section moves out)
- Create: `docs/HISTORY.md`
- Create: `CONTRIBUTING.md`
- Modify: `.gitignore` (ignore `build/`)

**Interfaces:** none produced; this is launch-surface work gated by the spec ("repo currently leads with the dead CircuitCLI pivot").

- [ ] **Step 1: Move the pivot history out of the README**

Create `docs/HISTORY.md` containing the current README sections "This repo started as CircuitCLI…" (lines 1–9) and "How we got here" (the numbered list at the bottom), with a one-line header: `# Project history`.

- [ ] **Step 2: Rewrite the README lead**

Replace the current first 9 lines of `README.md` with:

```markdown
# spiceguard

**ngspice said exit 0. The answer was still wrong.**

Modern ngspice recovers from many classic convergence problems on its own —
and when it can't, it often returns **exit code 0 with a plausible but wrong
answer** (a relaxed fallback estimate, or arbitrary voltages on an ungrounded
node). Nothing in the standard flow warns you. This bites hardest on netlists
you didn't write yourself: AI-generated circuits and PR submissions.

`spiceguard` answers one question about a SPICE run: **can I trust this
result?** It combines static netlist analysis, ngspice failure-log decoding,
and silent-failure detection — as a CLI, an [MCP server for AI
agents](mcp-server/), a [VS Code extension](vscode/), and a [KiCad
workflow](kicad/).

*Project history (image-to-SPICE origins and the pivot): [docs/HISTORY.md](docs/HISTORY.md).*
```

Then delete the now-duplicated "What is spiceguard?" paragraph if it repeats the same content, keep the rest of the README structure, and: (a) document `--no-exec` in the Options table (`| --no-exec | Strip .control/.include before simulation — for netlists you did not write |`), (b) add an "MCP server" row to the Integrations table pointing at `mcp-server/`, (c) add one line to the Security section: "For untrusted netlists (AI-generated, PR-submitted) use `--no-exec`, which strips `.control` blocks and `.include` lines before simulation; the MCP server does this unconditionally.", (d) remove the "How we got here" section (now in HISTORY.md).

- [ ] **Step 3: Create CONTRIBUTING.md with DCO (the spec's licensing decision)**

```markdown
# Contributing

Thanks for helping catch silent SPICE failures!

## The most valuable contribution: netlists that fooled ngspice

Open an issue with (1) the netlist, (2) what ngspice reported, (3) what the
correct behaviour should have been. The failure corpus is the heart of this
project.

## Developer Certificate of Origin

Contributions require a DCO sign-off (`git commit -s`), certifying
https://developercertificate.org/. This keeps future licensing decisions
(e.g. dual-licensing a hosted service) possible while the project is young.
The core CLI is MIT and will stay MIT.

## Tests

    PYTHONPATH=src python3 -m pytest -q

Integration tests auto-skip when ngspice is absent.
```

- [ ] **Step 4: Repo hygiene**

```bash
printf "build/\n" >> .gitignore
git rm -r --cached build 2>/dev/null || true
```

Check `git status` — `build/` must no longer be tracked.

- [ ] **Step 5: Verify + commit**

Run: `PYTHONPATH=src python3 -m pytest -q` (unchanged — docs only) and re-read the new README top-to-bottom once for stale cross-references (the LTspice `.asc` and subcircuit sections must survive intact).

```bash
git add README.md docs/HISTORY.md CONTRIBUTING.md .gitignore
git rm -r --cached build 2>/dev/null
git commit -m "Launch-ready README, CONTRIBUTING with DCO, untrack build/"
```

---

### Task 8: Version 0.3.0 release

**Files:**
- Modify: `pyproject.toml` (version), `src/spiceguard/__init__.py` (`__version__`)
- Create: `CHANGELOG.md`

**Interfaces:**
- Consumes: everything above. The published 0.3.0 wheel is what `spiceguard-mcp` depends on (`spiceguard>=0.3.0`) and what the Pages workflow builds for the browser demo.

- [ ] **Step 1: Bump versions**

Set `version = "0.3.0"` in `pyproject.toml` and `__version__ = "0.3.0"` in `src/spiceguard/__init__.py` (verify the attribute exists there first; if version lives elsewhere, update where `--version` reads it — `cli.py` uses `spiceguard.__version__`).

- [ ] **Step 2: Write CHANGELOG.md**

```markdown
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
```

- [ ] **Step 3: Full suite, tag, release**

```bash
PYTHONPATH=src python3 -m pytest -q            # all green
git add pyproject.toml src/spiceguard/__init__.py CHANGELOG.md
git commit -m "Release 0.3.0"
```

Then: open a PR from `sprint/week0-2`, merge after review, and tag `v0.3.0` on main — the existing trusted-publishing workflow (added in commit 030a815) publishes to PyPI on tag. Verify with `pip index versions spiceguard` (or the PyPI page) that 0.3.0 is live **before** publishing `spiceguard-mcp` (its dependency pin needs it). Publish `spiceguard-mcp` 0.1.0 from `mcp-server/` (`python3 -m build && twine upload` or extend the publish workflow — decide at PR time based on how the existing workflow is scoped).

---

### Task 9: Desk validation, outreach infrastructure, NLnet draft (ops)

**Files:**
- Create: `docs/superpowers/research/2026-08-spice-in-ci-census.md`
- Create: `docs/templates/outreach-tracker.csv` (template only — the filled copy stays private)
- Create: `outreach/` locally + add `outreach/` to `.gitignore` (private working dir: filled tracker, NLnet draft)

**Interfaces:** none; produces the sprint's decision inputs. This task is research/writing, not code — steps are actions with defined outputs, not TDD.

- [ ] **Step 1: Desk validation of angle B (the spec's 2-hour kill-check)**

Run these GitHub code searches (web UI, logged in) and record hit counts + up to 10 notable repos each in `docs/superpowers/research/2026-08-spice-in-ci-census.md`:

1. `path:.github/workflows ngspice` — workflows invoking ngspice
2. `path:.github/workflows "kicad-cli sch export netlist"` — SPICE export in CI
3. `path:.github/workflows cace` and `cace ngspice` — open-PDK characterization users
4. `"spiceguard"` — anyone already mentioning us

The doc must end with a filled-in verdict line (this is the pre-registered decision, written before searching): "Angle B target segment: [open-PDK only / open-PDK + PCB teams / effectively empty] based on N total real hits." Per the spec: if analog-SPICE-in-CI counts are trivial outside open-PDK, angle B scopes to open-PDK only.

- [ ] **Step 2: Create the outreach tracker template**

`docs/templates/outreach-tracker.csv`:

```csv
name,affiliation,segment,channel,contact,date_contacted,replied,conversation_held,angle_signal,quote,next_step
```

Segments (from spec): `open-pdk`, `kibot-maintainer`, `hn-commenter`, `paper-author`, `instructor`, `other`. Copy to `outreach/tracker.csv` (gitignored) and seed it with the first 10 named targets from the spec's list (CACE/KiBot maintainers and contributors, HN Claude-Code-SPICE thread commenters, AnalogCoder/AMSbench/Masala-CHAI authors, 2 instructors) — finding names/handles is part of this step.

- [ ] **Step 3: Draft the NLnet NGI Zero application**

Write `outreach/nlnet-draft.md` (private) answering NLnet's actual form fields (check current form at nlnet.nl before writing; the known core fields are): project name; requested amount (€15,000); synopsis (~1200 chars) — use: "ngspice, the open-source SPICE simulator underpinning KiCad and the open-PDK silicon ecosystem, frequently reports success (exit 0) for simulations whose results are wrong — floating circuits, relaxed fallback estimates. spiceguard is a zero-dependency verification layer that detects these silent failures, with a public regression corpus of netlists that fool the simulator. Funding would support corpus expansion, deeper ngspice failure-log coverage, and integration into open hardware CI flows (KiCad, CACE/open-PDK)."; "Have you been paid for this work before" (no); "Compare with existing efforts" (ngspice's own SOA warnings check device limits, not result trustworthiness; commercial EDA verifies within closed platforms); budget breakdown (corpus + detectors: €9k, CI/tooling integrations: €4k, docs/community: €2k). Submit in the next open call — record the deadline in the doc.

- [ ] **Step 4: Commit the public pieces**

```bash
printf "outreach/\n" >> .gitignore
git add docs/superpowers/research/2026-08-spice-in-ci-census.md docs/templates/outreach-tracker.csv .gitignore
git commit -m "Add SPICE-in-CI census and outreach tracker template"
```

---

## Explicitly out of scope (per spec)

- No billing, auth, hosted backend, or dashboard.
- No maintained GitHub Action / marketplace listing — the README gets a 20-line workflow *snippet* only if a conversation asks for it.
- No new detectors.
- Forum account creation, posting, Show HN submission, and the outreach sending itself are founder actions scheduled by the spec's week 2–3 plan — this plan only builds the artifacts and templates they need.

## Task order and dependencies

1 → 2 → 3 are strictly sequential (each consumes the previous interface).
4 (MCP) needs 2+3. 5 (benchmark) needs 2. 6 (site) needs 3. 7 (README) needs 4+6 to exist so links resolve. 8 (release) needs 1–7 merged. 9 (ops) is independent and can run any time — do Step 1 (desk validation) FIRST if time-boxed, since its outcome can rescope angle B.
