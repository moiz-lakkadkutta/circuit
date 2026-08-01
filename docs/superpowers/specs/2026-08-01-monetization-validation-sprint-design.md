# spiceguard Monetization: 6-Week Validation Sprint

**Date:** 2026-08-01
**Status:** Approved framing; sprint not yet started
**Owner:** Moiz Lakkadkutta

## Context

spiceguard is a published PyPI package (~1,300 LOC Python, MIT, zero runtime
deps) that answers "can I trust this SPICE simulation result?" It has three
distribution surfaces (Docker, VS Code extension, KiCad CLI workflow), a
`--json` output mode, and meaningful exit codes.

Constraints that shape the strategy:

- **Goal:** startup ambition — looking for a real wedge, not a tip jar.
- **Traction:** zero. No meaningful downloads, stars, or user contact.
- **Founder profile:** software-first; the domain knowledge is researched, not
  lived. No existing audience in electronics.
- **Capacity:** 5–10 hrs/week, go/no-go signal wanted within ~6 weeks.
- **Moat reality:** the code is MIT and public; the durable assets are the
  detector knowledge base and any distribution/community built around it.

## Market read

The natural user base (ngspice/KiCad/LTspice users) skews hobbyist, student,
and academic — segments with very low willingness to pay. Professionals who do
pay for simulation live inside Cadence/Synopsys/Keysight ecosystems that are
not accessible to an outside solo founder. Therefore: **monetization requires
finding an adjacent wedge with repeat-simulation buyers, not paywalling the
current CLI.**

## Angles considered and rejected

| Angle | Why rejected |
|---|---|
| Donations / GitHub Sponsors | Near-zero revenue at zero traction; not startup-shaped |
| Paid VS Code extension | No native marketplace payments; tiny audience |
| Consulting on sim flows | Requires domain credibility not yet established |
| Courses / content | Monetizes attention, not the product; slow |
| License engine to EDA vendor (Flux.ai, CircuitLab, Altium) | An endgame, not a strategy; needs traction first for leverage |

## The three live angles

### A. Open-core community tool (funnel, not business)

Push distribution hard, grow free users, later add a paid Pro tier. Ceiling is
side income at best. Its strategic role is **top-of-funnel** for angles B and C
— every other path needs users this one generates.

### B. SPICE-in-CI SaaS ("Codecov for circuit simulation")

Hardware-as-code is real: teams version KiCad projects in git, run ERC/DRC in
CI; the open-silicon world (Tiny Tapeout etc.) runs sims in pipelines.
spiceguard's `--json` + exit codes are ~80% of a GitHub Action already. The
paid product is a hosted dashboard: trust verdicts on every PR, regression
tracking, team seats. Most genuinely SaaS-shaped angle. **Key risk:** the
"teams running SPICE in CI" segment may be too small today — this is exactly
what the sprint measures.

### C. Trust layer for AI-generated circuits

People increasingly generate netlists with LLMs (Flux Copilot; hobbyists
pasting ChatGPT netlists into LTspice). AI-generated netlists are precisely the
kind that fail silently — plausible, exit-0, wrong. Reposition spiceguard as
the verification/guardrail layer for AI-generated hardware. Cheapest concrete
move: an **MCP server** so AI agents verify circuits they generate. Rides a
rising wave; timing is the bet.

## The sprint (6 weeks, ~5–10 hrs/week)

The three angles share one funnel, so test them in parallel and let the market
pick.

### Week 1–2: Ship the cheap artifacts

1. **GitHub Action** (`spiceguard-action`): thin wrapper over the CLI; runs on
   PRs, fails the build on FAILED/SUSPECT verdicts, posts a summary comment.
2. **MCP server**: exposes check-netlist as a tool over the existing `--json`
   output so Claude Code / Cursor / other agents can verify generated circuits.
3. **Landing page** for "spiceguard CI" with a beta waitlist ("trust checks on
   every PR"). No backend — waitlist only.

### Week 2–3: Distribution burst

- Show HN (lead with the AI-verification framing — it is the novel story).
- KiCad forum, EEVblog forum, r/PrintedCircuitBoard, r/AskElectronics.
- Tiny Tapeout / open-silicon Discord communities.
- MCP directory listing(s).

### Week 3–6: Talk to humans

- Target: **10 real conversations** with people who engage.
- Listen specifically for anyone running sims *repeatedly* (CI, regression,
  AI-generation loops) — they are the only plausible payers.

## Go/no-go criteria (week 6)

**GO signals (any of):**

- Waitlist signups from identifiable teams/companies (not hobbyists).
- Inbound "can it do X" requests from repeat-simulation users.
- Real MCP adoption (agents/tools actually calling it, not just stars).

**NO-GO:** none of the above materialize. Outcome is still positive: a
portfolio piece, a validated dead end (the second one, done properly), and a
community asset that retains option value.

## What we deliberately do NOT build during the sprint

- No billing, no auth, no hosted backend, no dashboard.
- No new detectors (unless a conversation demands one as proof).
- Every hour on backend/billing before demand exists is wasted.

## Success metrics

| Metric | Instrument |
|---|---|
| PyPI downloads | pypistats / pepy.tech |
| GitHub stars / issues from strangers | repo insights |
| Waitlist signups (team vs hobbyist) | landing page form |
| MCP server installs/calls | directory stats, anecdotal reports |
| Conversations held | manual count, notes per conversation |
