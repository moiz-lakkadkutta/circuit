# spiceguard Monetization: 6-Week Validation Sprint (v2, post-red-team)

**Date:** 2026-08-01
**Status:** Revised after 4-lens red-team review (market/GTM, competition/timing, execution, missed-angles)
**Owner:** Moiz Lakkadkutta

## Context

spiceguard is a published PyPI package (~1,300 LOC Python, MIT, zero runtime
deps) that answers "can I trust this SPICE simulation result?" It has three
distribution surfaces (Docker, VS Code extension, KiCad CLI workflow), a
`--json` output mode, and meaningful exit codes.

Constraints that shape the strategy:

- **Goal:** startup ambition — looking for a real wedge, not a tip jar.
- **Traction:** zero. No meaningful downloads, stars, or user contact.
- **Founder profile:** software-first; domain knowledge researched, not lived.
  No existing audience in electronics (fresh accounts on every forum).
- **Capacity:** 5–10 hrs/week ⇒ **30–60 total hours**. Every line item below
  carries an hour cost for that reason.
- **Moat reality:** code is MIT and public. The durable assets are (a) the
  **test-netlist corpus of known silent failures** and (b) distribution/
  citations — not the 9 detectors, which an ngspice maintainer could absorb
  upstream in a weekend. Absorption-with-attribution is a good outcome, not a
  threat; plan for it.

## Competitive landscape (red-team verified)

| Player | What they do | Implication |
|---|---|---|
| **AllSpice.io** | Funded "DevOps/CI for electronics" — hosted hub, PR reviews, CI Actions; KiCad/Altium/OrCad | Angle B cannot be "build the Codecov" — teams doing hardware CI are already in AllSpice's funnel. Be a *check inside* existing pipelines instead. |
| **SPICEBridge + ≥4 other SPICE/ngspice MCP servers** | 28 tools incl. netlist validation, spec compare; 28 stars max; its Show HN got 1 point | "An MCP server" is not novel. The differentiator is the exit-0-lie detection; prove it with a benchmark, not a listing. |
| **Flux ($37M), Diode ($11.4M), Quilter ($25M), Circuit Mind** | AI circuit design with *internal* self-verification | Closed loops won't buy a third-party guardrail. Angle C's real ICP is open-loop users: general coding agents (Claude Code/Cursor) + ngspice locally. |
| **Academic LLM-circuit work** (AnalogCoder 57.3% valid, LaMAGIC 68.2%, AMSbench, Masala-CHAI, AnalogTester) | Published validity rates for LLM-generated netlists; all need a programmatic validity oracle | Free ammunition for the landing page, and the best unclaimed wedge: become the *cited validity checker* in these benchmarks. A citation is a moat MIT can't erode. |
| **ngspice upstream / KiCad ERC** | SOA warnings exist; `kicad_ground_not_zero` is one upstream fix from obsolete | Reinforces: corpus + distribution are the assets, not detectors. |
| **Open-PDK analog flows** (CACE, IIC-OSIC-TOOLS, SkyWater/IHP/GF180) | Already run ngspice repeatedly in Docker CI for characterization | **The SPICE-in-CI segment exists and is named** — it is not PCB teams, it is open-silicon analog. Target it directly. |

Key market correction: Tiny Tapeout CI sims are digital (cocotb/iverilog), not
SPICE. Analog-SPICE-in-CI among PCB teams is nearly nonexistent; among open-PDK
IC teams it is standard practice.

## The three angles (re-scoped)

- **A. Open-core community tool** — funnel and credibility, not a business.
- **B. Trust check inside existing hardware-CI pipelines** — a check line in
  KiBot/AllSpice/CACE workflows, targeting the open-PDK analog segment first.
  Standalone-SaaS framing is dropped until demand proves otherwise.
- **C. Trust layer for AI-generated circuits, scoped to open loops** —
  (1) developers using general coding agents on SPICE workflows (MCP server),
  (2) academic benchmark authors needing a validity oracle (integration +
  citation). Walled-garden platforms are evidence of demand and eventual
  acquirer conversations, not addressable market.

## Security gate (blocking, before any artifact ships)

The README documents that netlists can execute arbitrary shell commands via
`.control`/`shell` directives. Both flagship artifacts run **untrusted**
netlists (AI-generated; PR-submitted). Therefore:

1. **MCP path:** add a `--no-exec` / static-safe mode that strips or refuses
   `.control` blocks (netlist.py already tokenizes lines). Budget 3–5 hrs.
   Say so prominently — it is on-brand for a trust tool.
2. **CI guidance:** document running in the Docker image with no token and
   network disabled; `pull_request`, never `pull_request_target`.
3. Put the threat model *in* the launch post; an HN commenter will otherwise
   put it there for us.

## Pre-registered go/no-go (write once, never edit after launch)

**GO** requires at least one of:

- **≥5 waitlist signups** from distinct company/edu email domains, with the
  form's required "how would you use this" answer indicating repeat simulation
  (CI / agent loop / regression).
- **≥3 conversations** where the person describes an *existing* repeat-
  simulation workflow unprompted AND says they would deploy or pay (logged
  with a quote).
- **≥3 distinct strangers** with humanly-attributable evidence of MCP/tool use
  (issue, Discord message, config screenshot), or **1 benchmark/paper
  integration** (spiceguard cited or wired into an LLM-circuit eval repo).

**Denominator rule (prevents false "validated dead end"):** a NO-GO verdict is
only claimable after **≥40 documented outreach touches** and **≥8
conversations**. Short of that, the week-6 verdict is "distribution
insufficient — extend or stop," not "market invalidated."

**Signals that do NOT count:** PyPI download counts, stars, MCP directory
stats, anonymous traffic. Only humanly-attributable events decide.

**Week-3 checkpoint (pre-registered):** if <3 waitlist signups AND <2
conversations booked → stop all building; every remaining hour goes to direct
outreach. If ≥1 GO-quality signal concentrates on one angle → drop the other
two immediately.

## The sprint (re-sequenced; hour-costed)

### Week 0–1: Groundwork (~8–12 hrs)

- **Desk validation of angle B (2 hrs):** GitHub code search for workflows
  invoking `ngspice`; census CACE/open-PDK repos. If analog-SPICE-in-CI counts
  are trivial outside open-PDK, scope B to that segment only.
- **Licensing decision (1 hr, before any stranger contributes):** add DCO/CLA
  to keep relicensing a sole-founder option, and declare now that any hosted
  product/corpus expansion may be proprietary/BUSL. Deciding "later" =
  deciding MIT-forever.
- **Forum account aging starts now:** create accounts, answer existing threads
  with free diagnostic value (the KiCad `GND`-vs-node-0 gotcha is the hook).
  No promotion yet.
- **NLnet NGI Zero application (~4 hrs, one evening):** non-dilutive €5k–50k;
  NLnet funded KiCad and comparable solo tools. Pure option value.
- **README launch cleanup (2–3 hrs):** repo currently leads with the dead
  CircuitCLI pivot; move history to the bottom, lead with the silent-failure
  hook + demo GIF, reconcile repo name vs `spiceguard`, gitignore `build/`.

### Week 1–2: Two artifacts, not three (~14–20 hrs)

1. **Landing page + live demo + waitlist (~6–8 hrs):** static page; Pyodide
   runs the zero-dep static detectors client-side (paste netlist → trust
   report; no backend). Waitlist form has one required attribution question:
   "How would you use this: CI on PRs / AI-agent verification / editor
   checks." UTM-tagged links per channel.
2. **MCP server + silent-failure benchmark (~8–12 hrs):** MCP server in
   static-safe mode, plus the launch asset: run existing MCP validate tools
   (SPICEBridge et al.) and bare ngspice against the test-netlist corpus and
   publish the miss table — "N netlists that fool exit codes; here's who
   catches what."

**Deferred:** the GitHub Action as a maintained marketplace artifact. Ship a
20-line workflow snippet in the README instead; build the real Action (with
trust badge) only when a CI-angle conversation asks for it.

### Week 2–3: Distribution burst (~8–12 hrs)

Channel priority inverted from v1 — B/C audiences first, hobbyist forums last:

1. **Show HN** — lead with the benchmark demo ("I had Claude design N
   circuits; X% simulated 'successfully' and were silently wrong"), not with
   "an MCP server." Precedent: the closed-loop verification demo format got
   121 points; the bare MCP-server format got 1.
2. **Open-silicon channels:** CACE/IIC-JKU/FOSSi communities; offer an
   integration PR, not a pitch.
3. **MCP directories** (AI framing is native there) + Homebrew tap +
   awesome-electronics/awesome-kicad PRs + **Hackaday tip**.
4. **Hobbyist forums last**, via aged accounts and sanctioned venues (KiCad
   forum projects category, EEVblog Projects board), led by the TIL content.

### Week 1–6 (continuous): Outbound + conversations (~12–16 hrs)

Passive inbound will not produce 10 conversations; outbound is the primary
mechanism:

- **Named list of ~40 targets, built week 1:** CACE/KiBot maintainers and
  contributors; open-PDK analog designers (GitHub-visible); commenters on the
  HN Claude-Code-SPICE thread (self-identified target users); **5 authors** of
  LLM-circuit papers (AnalogCoder/AMSbench/Masala-CHAI) with an integration
  offer; **2 instructors** teaching circuits labs (GitHub Classroom
  autograding angle; August = fall course prep).
- Tracking sheet per touch: target, source, date, response, angle, quote.
- Target: **10 conversations** (≈25% reply on 40 personalized touches).

## What we deliberately do NOT build

- No billing, auth, hosted backend, or dashboard.
- No maintained GitHub Action until a conversation demands it.
- No new detectors — except a corpus addition when a conversation supplies a
  netlist that fooled ngspice (corpus growth IS the moat; a "submit a netlist
  that fooled ngspice" issue template is encouraged).

## Metrics that decide vs. metrics we merely watch

| Decides week 6 | Instrument |
|---|---|
| Waitlist signups (domain + attribution answer) | form export |
| Conversations meeting GO bar | notes + quotes |
| Humanly-attributable adoption events | issues/Discord/email |
| Benchmark/paper integrations | repo links, citations |

| Watched only (never decides) | Why |
|---|---|
| PyPI downloads | mirror/bot noise exceeds real usage at this scale |
| Stars, directory stats | vanity; SPICEBridge has 28 stars and ~no users |

## Revision history

- v1 (2026-08-01): initial sprint design.
- v2 (2026-08-01): post-red-team. Added competitive landscape and security
  gate; re-scoped B (check-in-pipeline, open-PDK segment) and C (open-loop
  agents + academic oracle); cut to two artifacts; added week-0 groundwork
  (desk validation, licensing, account aging, NLnet, README cleanup);
  pre-registered numeric go/no-go with denominator rule and week-3 checkpoint;
  replaced passive inbound with a 40-target outbound list; demoted
  download-shaped metrics to non-deciding.
