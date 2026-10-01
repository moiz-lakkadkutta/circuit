# Silent-failure benchmark

Compares what ngspice's exit code claims vs what spiceguard's verdict finds,
over (a) the curated test corpus and (b) 20 un-cherry-picked AI-generated
netlists (see ai_generated/PROVENANCE.md). Results are reported per slice in
`RESULTS.md`, plus an overall total.

Run: PYTHONPATH=src python3 benchmark/run_benchmark.py

**Mode:** the harness runs with `no_exec=False` — full simulation, no
`.control`/`.include`-family stripping. This is a deliberate exception to
spiceguard's default untrusted-input posture (`--no-exec`/MCP always
sanitize): the corpus is trusted first-party content, and sanitizing it
would strip the `.control` blocks these netlists rely on to run their
analysis, manufacturing FAILED results and erasing genuine silent failures
from the exit-0 denominator. Only ever point this harness at netlists you
trust as much as the existing corpus.

Want to add a netlist that fooled ngspice? Open an issue with the netlist and
what the correct behaviour should have been — corpus contributions are the
most valuable kind.
