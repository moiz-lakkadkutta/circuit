# circuit

This repo started as **CircuitCLI**, an image/photo-to-SPICE-simulation pipeline
(YOLO + OCR + graph → ngspice). That idea was dropped after research showed the
problem it targeted ("redrawing schematics") isn't a pain users actually report,
and the obvious adjacent gaps were already taken or funded.

It is now exploring a different, evidence-led direction: a **SPICE result
trust-guard**.

## Current direction: trustguard

Modern ngspice recovers from many classic convergence problems on its own — and
when it can't, it often returns **exit code 0 with a plausible but wrong answer**
(a relaxed fallback estimate, or arbitrary voltages on an ungrounded node).
Nothing in the standard flow warns you. `trustguard` answers one question about a
SPICE run: **can I trust this result?**

It combines static netlist analysis, ngspice failure-log decoding (cryptic
internal names → the real component + a specific fix), and silent-failure
detection (exit-0 runs that are still untrustworthy). It accepts netlists from
ngspice/KiCad/LTspice/PSpice and (experimentally) LTspice `.asc` schematics.

→ **See [`poc/`](poc/) for the working tool, tests, and full documentation.**

```bash
cd poc
python3 trustguard.py            # diagnose the bundled example circuits
python3 test_trustguard.py       # 15 tests against real ngspice
```

Requires `ngspice` (`brew install ngspice`).

## Status

Proof of concept. Validated on synthetic + real-world circuits with a passing
test suite. It is a focused power-user utility, not a finished product — see
`poc/README.md` for honest scope and limitations.

## How we got here

1. Audited the original image-to-sim idea (market / engineering / business).
2. Deep research across the full EDA/sim workflow + a competition cross-check.
3. Ruled out taken/funded gaps (AR debugging = Cadence inspectAR; AI autorouting
   = Quilter et al.; SI/PI = heavy field-solver work).
4. Landed on the SPICE result-trustworthiness wedge and built `poc/`.
