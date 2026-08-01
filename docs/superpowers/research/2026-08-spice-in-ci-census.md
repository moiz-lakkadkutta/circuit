# SPICE-in-CI census (2026-08-01)

Desk validation of "angle B" — trust checks in hardware CI — per the sprint spec's
2-hour kill-check. This is the pre-registered decision procedure and rule,
written **before** running the searches below.

## Decision rule (pre-registered)

Per the spec: if analog-SPICE-in-CI counts are trivial outside open-PDK,
angle B scopes to **open-PDK only**. Concretely:

- Count real, on-topic hits (after removing false positives: unrelated tools,
  name collisions, forked mirrors of the same repo, dependency-bump bots) for
  each query below.
- If the open-PDK-specific query (CACE + ngspice combined) accounts for
  the overwhelming majority of *genuine* "simulation result is being
  trust-checked/gated in CI" hits, and the generic KiCad/PCB query returns only
  a handful of hobbyist repos with no result-trust-checking (just export/build
  steps), the verdict is **open-PDK only**.
- If PCB/KiCad hobbyist CI shows a comparable or larger population actually
  gating on simulation results (not just running/exporting them), the verdict
  is **open-PDK + PCB teams**.
- If total genuine hits across all queries are near-zero, the verdict is
  **effectively empty** and angle B is deprioritized entirely in favor of
  angle A (the CLI/local trust checker).

## Method and provenance

All GitHub numbers below are from the GitHub REST code-search API
(`gh api search/code?q=...`), run 2026-08-01, authenticated as
`moiz-lakkadkutta`. GitHub's code-search index only covers the *default
branch* of *indexed* repos (a known undercount, noted in the spec), and its
`filename:`/bare-term qualifiers do prefix/substring matching (e.g.
`filename:cace` also matches `cacert`), so every query below was sanity-checked
by manually inspecting hits and, where noisy, re-run with a stricter filter.
The exact query string is given for every count so it can be reproduced.

### Query 1 — `ngspice` in `.github/workflows`

Query: `gh api 'search/code?q=ngspice+path:.github/workflows'`
**Total hits: 212** (GitHub-reported `total_count`; code search returns at
most ~100 concrete items, so this is an index count, not all enumerable).

Sample of 30 inspected — mixed population, roughly three clusters:

1. **ngspice-as-dependency / tooling repos** (majority): projects that build,
   wrap, or mirror ngspice itself, or use it as a library dependency in CI —
   not "trust-checking" a simulation result. E.g. `danchitnis/ngspice` (mirror
   build), `ra3xdh/qucs_s` (deploy pipeline for a GUI that bundles ngspice),
   `eelab-dev/EEcircuit`, `mfiumara/spice-ts`, `JaimeHW/RSpice`,
   `NyanCAD/Mosaic`, `hdl/conda-eda`.
2. **Open-PDK / silicon-adjacent repos**: `fossi-foundation/globalfoundries-pdk-libs-gf180mcu_fd_pr`
   (`models_ngspice.yml` — PDK device-model regression), `sgherbst/sky130-hello-world`
   (`regression.yml`), `iic-jku/SG13CMOS_SPARX` (`regression.yml`),
   `ucb-substrate/sram22`, `ucb-substrate/substrate`.
3. **Generic CI incidental matches**: false-positive-adjacent hits where
   `ngspice` appears in an unrelated file path echoed into a workflow log
   (e.g. `OpenCircuits/OpenCircuits :: playwright.yml`,
   `joeyparrish/kinetoscope :: sym-lib-table` — KiCad symbol library table
   files that happen to reference a library named with "spice" in it, not
   actual simulation runs).

Notable repos (10): `fossi-foundation/globalfoundries-pdk-libs-gf180mcu_fd_pr`,
`sgherbst/sky130-hello-world`, `iic-jku/SG13CMOS_SPARX`, `ucb-substrate/sram22`,
`ucb-substrate/substrate`, `ankur-gupta-29/ngspice_sim`, `danchitnis/ngspice`,
`ra3xdh/qucs_s`, `hdl/conda-eda`, `NyanCAD/Mosaic`.

**On-topic count for this query, defined and derived:** "on-topic" here means
cluster 2 only — a workflow that runs ngspice as part of an open-PDK
device/IP regression check (cluster 1, tooling/dependency repos, and
cluster 3, incidental matches, are excluded because they aren't evidence of
*anyone gating on a simulation result*, which is the thing angle B cares
about). Cluster 2 has **5 repos** in the 30-item sample:
`fossi-foundation/globalfoundries-pdk-libs-gf180mcu_fd_pr`,
`sgherbst/sky130-hello-world`, `iic-jku/SG13CMOS_SPARX`,
`ucb-substrate/sram22`, `ucb-substrate/substrate`. This is a **lower bound**,
since only 30 of the 212 raw-indexed hits were manually inspected — the true
on-topic count within the full 212 is almost certainly higher, but this
report only tallies confirmed (manually inspected) hits rather than
extrapolating from the sample ratio, to avoid overstating the total. None of
these 5 repos overlap with the Q3/Q3b repo lists below (checked by name).

### Query 2 — `"kicad-cli sch export netlist"` in `.github/workflows`

Query: `gh api 'search/code?q=%22kicad-cli+sch+export+netlist%22+path:.github/workflows'`
**Total hits: 10** (all 10 items returned — no pagination cutoff, this is the
complete population GitHub's index has). This is a phrase match on the exact
CLI invocation, so it is close to precise (no substring-matching noise
observed on manual inspection).

All 10, by repo: `electron-rare/Kill_LIFE` (×3 workflows),
`acha666/Zigbee-Air-Sensor`, `acha666/ADUMx165_USB_Isolator`,
`grahame-white/kicad_automation` (×2 — including a file literally named
`spice_sim.yml`), `acha666/IP6557_Charger`, `acha666/Fan_Controller`,
`acha666/kicad-ci`.

That is **7 distinct repos**, all personal/hobbyist PCB projects, none of
which appeared to gate CI on a *checked* SPICE result (they export the
netlist and/or run a simulation as a build artifact step; none of the
inspected workflow files assert on simulation output correctness — they'd
pass even on a garbage result, which is exactly the "angle B" failure mode
spiceguard targets, and exactly why none of them already do this). This is
the generic-PCB-teams population size: **7 real repos, all hobbyist-scale,
zero currently doing result trust-checking.**

### Query 3 — CACE (open-PDK characterization tool)

Bare `cace path:.github/workflows` is dominated by an unrelated substring
match: GitHub's index treats `cacert*` (certificate-bundle update workflows,
completely unrelated) as matching `cace` — a `filename:cace` query returned
**54** raw hits, of which manual regex filtering (`path` ending in
`/cace.yml` or `/cace.yaml`) leaves the real population:

Query: `gh api 'search/code?q=path:.github/workflows+filename:cace'` (raw:
54), filtered to exact `cace.yml`/`cace.yaml` workflow files:
**14 real hits**, all open-PDK silicon IP repos: `RTimothyEdwards/sky130_ef_ip__opamp`,
`mole99/sky130_leo_ip__ota5t`, `efabless/sky130_pa_ip__instramp`,
`fossi-foundation/sky130_ef_ip__simple_por`, `fossi-foundation/sky130_pa_ip__instramp`,
`efabless/sky130_ef_ip__template`, `PravinduG/sky130_op_amp`,
`mole99/tt08-aicd-playground`, `efabless/sky130_ef_ip__simple_por`,
`mole99/sky130_leo_ip__rdac_8bit`, `mole99/sg13g2_leo_ip__ota5t`,
`mole99/sky130_leo_ip__levelshifter`, `mole99/sky130_leo_ip__comparator`,
`watbulb/tt-ring-oscillator-test`. **All 14 are open-PDK (sky130/sg13g2 IP
blocks), 100% concentration in the open-PDK segment.**

Stricter combined query — `cace ngspice path:.github/workflows`:
Query: `gh api 'search/code?q=cace+ngspice+path:.github/workflows'`
**Total hits: 2** — `iic-jku/ihp-sg13g2-ams-chip-template` and
`iic-jku/TinyWhisper` (both `regression.yml`, both IHP-PDK academic IC
templates). This is the narrowest, cleanest signal: repos that both run CACE
*and* explicitly invoke ngspice in the same CI workflow. Both are open-PDK.

### Query 4 — `"spiceguard"` (anyone already mentioning us)

Query: `gh api 'search/code?q=spiceguard'`
**Total hits: 70**, but on inspection this is almost entirely noise:

- Our own repo (`moiz-lakkadkutta/circuit`) — 15+ of the hits.
- Unrelated name collisions: `Alexundr38/Messenger-Orbit` has an unrelated
  C++ class `SpiceGuard`; `dot-do/startups.do` has an auto-generated startup
  directory entry `spiceguard.mdx` for an unrelated food-labeling-compliance
  product called "SpiceGuard Compliance AI" (confirmed by reading the file —
  totally different domain, NAICS code 311942, food manufacturing); a PyPI
  mirror-data repo (`szabgab/pydigger-data`) just indexes our own published
  package metadata (a side effect of us existing on PyPI, not organic
  mention); several Lua/game-server repos matching on unrelated substrings.

**Real organic third-party mentions of the spiceguard project: 0.** No one
has publicly referenced this project outside our own repo and its
downstream package-index mirrors.

## Totals and verdict inputs

"On-topic" is defined per-query above; in every case it means "a workflow
that runs an open-PDK/analog simulation as part of a CI-gated check," not
merely a text match. Each row's on-topic count is either a complete
enumeration (Q2, Q3, Q3b, Q4 — GitHub returned every item, or the filtering
was exhaustive over the returned set) or an explicit lower-bound sample
count (Q1 — only 30 of 212 raw hits were manually inspected; see Query 1
above for the derivation).

| Query | Raw index count | On-topic hits | How derived | Segment concentration |
|---|---|---|---|---|
| Q1 `ngspice` in workflows | 212 | **5** (lower bound, from a 30-item manual sample) | Cluster-2 repos in the sample; clusters 1 (tooling/dependency) and 3 (incidental) excluded as not gating on a result | open-PDK |
| Q2 `kicad-cli sch export netlist` | 10 | **7** (complete — all 10 raw hits map to 7 distinct repos) | Manual inspection of all 10 hits, none assert on simulation output | 100% PCB/KiCad hobbyist, **0% doing result trust-checks** |
| Q3 CACE (filtered) | 54 raw (noisy, `cacert*` substring collisions) | **14** (complete enumeration of the 54 raw hits) | Regex-filtered to exact `cace.yml`/`cace.yaml` paths | 100% open-PDK |
| Q3b CACE+ngspice combined | 2 | **2** (complete — GitHub returned exactly 2 raw hits, both on-topic) | Manual inspection, both are IHP-PDK regression jobs | 100% open-PDK |
| Q4 "spiceguard" | 70 raw | **0** | Manual inspection of all 70 hits — all are either our own repo or unrelated name collisions | n/a |

**Total on-topic hits across all queries: 5 + 7 + 14 + 2 + 0 = 28.**
Repo-name cross-check confirms no overlap between the Q1 sample's 5, Q3's 14,
and Q3b's 2 (three disjoint sets, summed directly with no double-counting).
This total is itself a **floor**, not a ceiling: Q1 alone was only 30%
sampled, and GitHub's index is a known undercount (default-branch-only,
indexing lag) on top of that — so the true population is at least 28 and
plausibly larger, concentrated overwhelmingly in the open-PDK segment (16 of
the 28, i.e. Q3+Q3b, come from queries that specifically target open-PDK
CACE workflows; the generic ngspice query (Q1) also resolved entirely to
open-PDK hits in its sampled on-topic set; only Q2's 7 are PCB/KiCad, and
those 7 have zero existing result-gating to extend).

The open-PDK segment (CACE + ngspice in PDK IP-block CI) is the only segment
where hits are concentrated, homogeneous, and already exercising a
CI-gated simulation flow (i.e., a spiceguard integration has an existing
hook point: the CACE regression job). The PCB/KiCad hobbyist segment has a
real but small (7-repo) population, and **none of them currently trust-check
simulation results** — they run/export SPICE as a build step, meaning there
is no existing CI gate to plug into; adoption there would require convincing
hobbyists to add a new CI step from scratch, a much higher-friction ask than
"add spiceguard to the CACE job you already run."

## Verdict

**Angle B target segment: open-PDK only, based on 28 total on-topic hits**
(5 + 7 + 14 + 2 + 0, see the reconciled table above — dominated by the
14-repo CACE/sky130/sg13g2 cluster and the 2-repo CACE+ngspice cluster, with
Q1's sampled open-PDK hits adding 5 more; the PCB/KiCad population is real
but tiny (7 repos, all of Q2) and structurally weaker — no existing CI gate
to extend, versus open-PDK's existing CACE regression jobs). 21 of the 28
(75%) are open-PDK; the PCB/KiCad segment is the remaining 7 (25%) and has
zero repos already trust-checking a result. Per the pre-registered rule:
this counts as "trivial outside open-PDK," so angle B scopes to open-PDK
only for this sprint. Outreach and the NLnet application (below) are scoped
accordingly.
