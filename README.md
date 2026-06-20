# circuit / trustguard

This repo started as **CircuitCLI**, an image/photo-to-SPICE-simulation pipeline
(YOLO + OCR + graph → ngspice). That idea was dropped after research showed the
problem it targeted ("redrawing schematics") isn't a pain users actually report,
and the obvious adjacent gaps were already taken or funded.

It is now exploring a different, evidence-led direction: a **SPICE result
trust-guard**.

---

## What is trustguard?

Modern ngspice recovers from many classic convergence problems on its own — and
when it can't, it often returns **exit code 0 with a plausible but wrong answer**
(a relaxed fallback estimate, or arbitrary voltages on an ungrounded node).
Nothing in the standard flow warns you.

`trustguard` answers one question about a SPICE run: **can I trust this result?**

It combines static netlist analysis, ngspice failure-log decoding (cryptic
internal names translated to the real component plus a specific fix), and
silent-failure detection (exit-0 runs that are still untrustworthy). It accepts
netlists from ngspice, KiCad, LTspice, and PSpice, and can convert LTspice `.asc`
schematics (experimental, built-in 2-pin symbols only).

---

## Install

**Requirements:** Python 3.9+, ngspice

```bash
brew install ngspice          # macOS; Linux: apt install ngspice
```

**Install from the repo:**

```bash
pip install .
```

This registers a `trustguard` command on your PATH. Alternatively, run directly
without installing (useful during development):

```bash
PYTHONPATH=src python3 -m trustguard FILE...
```

---

## ngspice path resolution (priority order)

trustguard locates the ngspice binary in this order:

1. `--ngspice PATH` CLI flag — if given and not executable, raises an error immediately (no fallthrough)
2. `$NGSPICE` environment variable — same hard-configured semantics; error if set but not usable
3. `which ngspice` (PATH lookup)
4. Legacy fallback `/opt/homebrew/bin/ngspice`

If none of the above resolves to a usable binary, trustguard exits with code **3**
and prints a clear message listing what was tried. Install ngspice, or point to it
explicitly:

```bash
trustguard --ngspice /usr/local/bin/ngspice mynetlist.cir
# or
export NGSPICE=/usr/local/bin/ngspice
```

---

## CLI usage

```
trustguard [--ngspice PATH] [--version] [--help] FILE...
trustguard kicad [--ngspice PATH] FILE...
```

Pass one or more netlist (or schematic) files. When multiple files are given,
trustguard evaluates each in sequence and exits with the worst verdict across all.

### Options

| Flag | Description |
|------|-------------|
| `FILE...` | One or more netlist or schematic files to check |
| `--ngspice PATH` | Explicit path to the ngspice binary |
| `--version` | Print version and exit |
| `--help` | Show usage |

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | TRUSTWORTHY — ngspice exited 0 and no trust issues found |
| 1 | FAILED — ngspice exited non-zero |
| 2 | SUSPECT — ngspice exited 0 but trust issues were detected |
| 3 | ngspice not found |
| 64 | Usage error (bad arguments) |

### Example

```
$ PYTHONPATH=src python3 -m trustguard tests/netlists/n5_healthy_control.cir

======================================================================
n5_healthy_control.cir
======================================================================
✓  TRUSTWORTHY   (ngspice exit 0)

  No trust issues detected.
```

```
$ PYTHONPATH=src python3 -m trustguard tests/netlists/n1_missing_ground.cir

======================================================================
n1_missing_ground.cir
======================================================================
⚠  SUSPECT   (ngspice exit 0)

  [FATAL] no_ground
  → No node '0' (ground). SPICE has no voltage reference, so it may float the circuit and return arbitrary WRONG voltages with no error. Fix: tie a reference node to '0'.
```

---

## Input formats

| Extension | Handling |
|-----------|----------|
| `.cir`, `.net`, `.sp`, `.spice`, `.ckt` | Passed directly to ngspice |
| Any other netlist | ngspice natively translates KiCad, LTspice, PSpice, HSpice dialects |
| `.asc` | Converted in-process (experimental — see below) |

**LTspice `.asc` (experimental):** trustguard converts `.asc` schematics using
built-in 2-pin symbol geometry (resistor, capacitor, inductor, diode, voltage
source, current source). Net connectivity is recovered by union-find over
wire/pin/flag coordinates. For anything beyond these built-in symbols, export
the netlist from LTspice ("View > SPICE Netlist") and feed that instead — that
path is exact. When a `.asc` is evaluated, the generated netlist is printed at
the end of the report so you can compare it against LTspice's own export.

### Subcircuit support (Feature B)

trustguard's parser handles:

- `.subckt` / `.ends` block collection and extraction
- `X`-instance flattening with automatic node namespacing (internal nodes become
  `instancename:node` to avoid collisions)
- `+` continuation lines rejoined before parsing
- `.include` file resolution (local files only; URL `.include` lines are warned
  and skipped)

Errors detected during subcircuit processing:

- `undefined_subckt` — X-instance references a subckt name not defined in the netlist
- `port_mismatch` — X-instance provides a different number of nodes than the subckt port list
- `subckt_recursion` — self- or mutual-referencing subckts (skipped with a warning)

---

## KiCad workflow (Feature C)

```bash
trustguard kicad myboard.cir
```

The `kicad` subcommand runs the standard trust check **plus** a KiCad-specific
preflight that detects the classic export gotcha:

**`kicad_ground_not_zero`** — ngspice requires the circuit ground to be exactly
node `0`. KiCad schematics commonly use a `GND` net (or `GNDA`, `VSS`, `0V`,
`AGND`, `DGND`, `PGND`) that is NOT automatically mapped to node 0 on SPICE
export. When such a net is present and node 0 is absent, the simulation silently
floats the entire circuit, yielding wrong voltages with no error. The message
includes KiCad-specific fix instructions (set node mapping in Symbol Properties
or place a `PWR_FLAG`).

**Pipe form** — export and check in a single step without writing a file:

```bash
kicad-cli sch export netlist --format spice myboard.kicad_sch -o - \
  | trustguard kicad -
```

**Important:** trustguard is a command-line workflow helper, not a native KiCad
plugin. KiCad has no post-simulation event API, so there is no in-GUI integration;
run `trustguard kicad` from your terminal or CI pipeline.

---

## Verdict model

Every run produces one of three verdicts:

| Verdict | Meaning |
|---------|---------|
| **TRUSTWORTHY** | ngspice exited 0 and no trust-breaking issues found |
| **SUSPECT** | ngspice exited 0 but at least one FATAL/SILENT/WARN issue detected |
| **FAILED** | ngspice exited non-zero |

FAILED outranks SUSPECT, which outranks TRUSTWORTHY (this is why exit code 1 < 2
numerically but FAILED is the worst outcome).

### Detectors

| Code | Severity | Description |
|------|----------|-------------|
| `no_ground` | FATAL | No node '0' — circuit has no voltage reference |
| `source_conflict` | FATAL | Multiple voltage sources forced across the same node pair |
| `no_dc_path` | FATAL | Node reachable only through capacitors/current sources — no DC reference |
| `timestep_collapse` | FATAL | Transient timestep collapsed; specific culprit identified from the log |
| `singular_node` | FATAL | Singular matrix at a node — no defined DC solution |
| `singular_branch` | FATAL | Singular matrix at a branch (current unconstrained) |
| `silent_fallback` | SILENT | ngspice exited 0 after gmin/source stepping **failed**; operating point is a relaxed estimate, not a true solution |
| `kicad_ground_not_zero` | WARN | KiCad export uses GND/GNDA/etc. but no node 0 (kicad subcommand only) |
| `dangling_node` | WARN | Node connects to only one pin — likely a wiring mistake |

---

## Limitations (honest scope)

- **Parser scope:** The static netlist parser covers the element types listed in
  `netlist.py` (`NODE_COUNT`). Exotic or simulator-specific elements not in that
  table are silently skipped (they do not affect the running netlist — ngspice
  still sees the full file).
- **`.asc` is experimental** and scoped to 6 built-in 2-pin symbol types. Any
  schematic with transistors, op-amps, subcircuit blocks, or custom symbols must
  be exported from LTspice first. Always verify the generated netlist against
  LTspice's own "View > SPICE Netlist".
- **Legacy fallback** (`/opt/homebrew/bin/ngspice`) is tier-4 last-resort only.
  It is not the preferred path; prefer `PATH` or the `$NGSPICE` variable.
- **KiCad integration** is a CLI helper, not an in-application plugin.

---

## Development

Run the test suite (no ngspice required for unit tests; integration tests
auto-skip when ngspice is absent):

```bash
PYTHONPATH=src python3 -m pytest -q
```

Observed output on the current suite:

```
82 passed in 3.93s
```

---

## How we got here

1. Audited the original image-to-sim idea (market / engineering / business).
2. Deep research across the full EDA/sim workflow + a competition cross-check.
3. Ruled out taken/funded gaps (AR debugging = Cadence inspectAR; AI autorouting
   = Quilter et al.; SI/PI = heavy field-solver work).
4. Landed on the SPICE result-trustworthiness wedge and built the tool.
