# Project history

This repo started as **CircuitCLI**, an image/photo-to-SPICE-simulation pipeline
(YOLO + OCR + graph → ngspice). That idea was dropped after research showed the
problem it targeted ("redrawing schematics") isn't a pain users actually report,
and the obvious adjacent gaps were already taken or funded.

It is now exploring a different, evidence-led direction: a **SPICE result
trust-guard**.

## How we got here

1. Audited the original image-to-sim idea (market / engineering / business).
2. Deep research across the full EDA/sim workflow + a competition cross-check.
3. Ruled out taken/funded gaps (AR debugging = Cadence inspectAR; AI autorouting
   = Quilter et al.; SI/PI = heavy field-solver work).
4. Landed on the SPICE result-trustworthiness wedge and built the tool.
