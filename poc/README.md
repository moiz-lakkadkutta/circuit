# trustguard (PoC)

Answers one question about a SPICE run: **can I trust this result?**

Most SPICE failures aren't loud crashes. Modern ngspice (v46, KLU + automatic
gmin/source stepping) recovers from many classic convergence problems on its
own — and when it *can't*, it often returns **exit code 0 with a plausible but
wrong answer** (a relaxed fallback estimate, or arbitrary voltages on an
ungrounded circuit). Nothing in the standard flow warns you. trustguard does.

## Usage

```bash
python3 trustguard.py                      # run on all netlists/*.cir
python3 trustguard.py path/to/circuit.cir  # a netlist (ngspice/LTspice/KiCad/PSpice)
python3 trustguard.py path/to/schematic.asc # an LTspice schematic (converted)
echo $?                                     # 0=TRUSTWORTHY 1=FAILED 2=SUSPECT
```

Requires `ngspice` (path hardcoded to `/opt/homebrew/bin/ngspice` for now).

## Input formats

| Input | How it's handled | Reliability |
| --- | --- | --- |
| `.cir/.net/.sp` from **ngspice** | run directly | exact |
| netlist from **KiCad** | run directly (KiCad emits ngspice netlists; ngspice translates PSpice/LTspice/HSpice dialects) | exact |
| netlist exported from **LTspice** (`View > SPICE Netlist`) | run directly | exact |
| **LTspice `.asc` schematic** | converted by `formats.py` (real `.asy` pin geometry + rotation transforms + coordinate union-find) | **experimental** |

The `.asc` converter is scoped to the built-in 2-pin symbols (`res`, `cap`,
`ind`, `voltage`, `current`, `diode`). It prints the generated netlist and a
"verify against LTspice's own netlist" notice. For anything outside that symbol
set, export the netlist from LTspice (one click) — that path is exact. Unknown
symbols are reported and skipped rather than guessed.

## What it does

1. **Static netlist checks** (before trusting any run): missing ground, two ideal
   voltage sources fighting, DC-floating nodes (touch only capacitors), dangling pins.
2. **Failure-log decoding**: turns ngspice's cryptic internal names
   (`check node v1#branch`, `trouble with sw-instance s1`) into the real component
   and a *specific* fix.
3. **Silent-failure detection** (the point): flags exit-0 runs that are still
   untrustworthy —
   - `silent_fallback`: op-point only reached after gmin/source stepping *failed*,
     so the result is a relaxed guess, not a true solution.
   - `no_dc_path`: a node reachable from ground only through capacitors / current
     sources. Its DC voltage is set by tiny gmin leakage, not the circuit. This is
     a **topological** check (graph reachability from node 0 over DC-conducting
     elements), so it flags genuine floating nodes **regardless of voltage
     magnitude** — and therefore does *not* false-positive on legitimately
     above-rail circuits like boost converters, charge pumps, or stacked sources.

Verdict: `TRUSTWORTHY` / `SUSPECT` (silent problem) / `FAILED` (hard error).

## Tested behavior

`python3 test_trustguard.py` — 15 tests, run against **real ngspice output**.
Synthetic fixtures (`netlists/n*.cir`): known failures diagnosed and named,
healthy/converging circuits left alone, exit-code contract. Real-world fixtures
(`netlists/realworld/`): see below.

## Real-world validation

Tested against real, representative circuits NOT designed to trip the detectors
(`netlists/realworld/`):

| Circuit | Verdict | What it proves |
| --- | --- | --- |
| `ce_amplifier.cir` | TRUSTWORTHY | coupling/bypass caps present but nodes DC-referenced via bias resistors — no false `no_dc_path` |
| `bridge_rectifier.cir` | TRUSTWORTHY | 470µF smoothing-cap node has a DC path via the load — the acid test for `no_dc_path` |
| `astable_multivibrator.cir` | FAILED → names node `c2` | a real timestep collapse |

This pass **found and fixed a real false-negative**: ngspice reports the
timestep-collapse culprit in multiple formats (`sw-instance s1` vs `node "c2"`),
and the parser originally handled only the first. Now both are parsed.

## Known limitations (honest)

- Netlist parser is intentionally simple: no `.subckt`/`.include` expansion, no
  line continuations, limited device set. Real netlists will need a fuller parser.
- The `no_dc_path` check treats semiconductors/switches conservatively as DC
  connections (to avoid false positives), so it can *miss* a node that is only
  referenced through a reverse-biased junction. It errs toward silence, not noise.
- ngspice path is hardcoded (`/opt/homebrew/bin/ngspice`).

## Changelog

- **(a)** Replaced the unsound magnitude-based `rail_violation` detector (which
  false-positived on boost converters / stacked sources — see
  `netlists/n8_stacked_sources.cir`) with the topological `no_dc_path` check.
- **(b)** Validated on real-world circuits (`netlists/realworld/`); fixed a
  false-negative where the timestep-collapse parser only handled the
  `sw-instance` phrasing and missed the `node "..."` phrasing.
- **(c)** Added an input-format front-end (`formats.py`): netlists from
  ngspice/KiCad/LTspice/PSpice run directly; LTspice `.asc` schematics are
  converted (built-in 2-pin symbols, verified pin geometry). Also fixed a
  case-sensitivity mismatch between ngspice's lowercased node names and the
  parser's original-case nodes.
