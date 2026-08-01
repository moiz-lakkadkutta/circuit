# Silent-failure benchmark

Compares what ngspice's exit code claims vs what spiceguard's verdict finds,
over (a) the curated test corpus and (b) 20 un-cherry-picked AI-generated
netlists (see ai_generated/PROVENANCE.md).

Run: PYTHONPATH=src python3 benchmark/run_benchmark.py

Want to add a netlist that fooled ngspice? Open an issue with the netlist and
what the correct behaviour should have been — corpus contributions are the
most valuable kind.
