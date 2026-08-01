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
