# Silent-failure benchmark

- spiceguard version: 0.3.0
- Mode: no_exec=False (full simulation) — corpus is trusted first-party content, see benchmark/ai_generated/PROVENANCE.md
- Reproduce: `PYTHONPATH=src python3 benchmark/run_benchmark.py`

## Curated corpus (tests/netlists)

| netlist | ngspice exit | spiceguard verdict | silent lie? |
|---|---|---|---|
| n1_missing_ground.cir | 0 (looks fine) | SUSPECT | YES |
| n2_floating_node.cir | 0 (looks fine) | SUSPECT | YES |
| n3_ideal_switch_smps.cir | 0 (looks fine) | TRUSTWORTHY | no |
| n4_bsource_singular.cir | 0 (looks fine) | TRUSTWORTHY | no |
| n5_healthy_control.cir | 0 (looks fine) | TRUSTWORTHY | no |
| n6_source_conflict.cir | 1 | FAILED | no |
| n7_relaxation_osc.cir | 1 | FAILED | no |
| n8_stacked_sources.cir | 0 (looks fine) | TRUSTWORTHY | no |
| astable_multivibrator.cir | 1 | FAILED | no |
| bridge_rectifier.cir | 0 (looks fine) | TRUSTWORTHY | no |
| ce_amplifier.cir | 0 (looks fine) | TRUSTWORTHY | no |
| kicad_export.cir | 0 (looks fine) | SUSPECT | YES |
| kicad_gnd.cir | 0 (looks fine) | SUSPECT | YES |
| kicad_subckt.cir | 0 (looks fine) | TRUSTWORTHY | no |
| sub_dcpath.cir | 0 (looks fine) | TRUSTWORTHY | no |
| sub_floating.cir | 0 (looks fine) | SUSPECT | YES |
| sub_include.cir | 0 (looks fine) | TRUSTWORTHY | no |
| sub_nested.cir | 0 (looks fine) | TRUSTWORTHY | no |
| sub_twoinst.cir | 0 (looks fine) | TRUSTWORTHY | no |
| sub_undefined.cir | 1 | FAILED | no |

**5 of 16 exit-0 runs (31%) were silently untrustworthy.**

## AI-generated corpus (benchmark/ai_generated)

| netlist | ngspice exit | spiceguard verdict | silent lie? |
|---|---|---|---|
| ai_01_divider.cir | 0 (looks fine) | TRUSTWORTHY | no |
| ai_02_divider_v2.cir | 0 (looks fine) | TRUSTWORTHY | no |
| ai_03_rc_lpf.cir | 0 (looks fine) | TRUSTWORTHY | no |
| ai_04_rc_lpf_v2.cir | 0 (looks fine) | TRUSTWORTHY | no |
| ai_05_led.cir | 0 (looks fine) | TRUSTWORTHY | no |
| ai_06_led_v2.cir | 0 (looks fine) | TRUSTWORTHY | no |
| ai_07_relax_osc.cir | 0 (looks fine) | SUSPECT | YES |
| ai_08_relax_osc_v2.cir | 1 | FAILED | no |
| ai_09_rectifier.cir | 0 (looks fine) | TRUSTWORTHY | no |
| ai_10_rectifier_v2.cir | 0 (looks fine) | TRUSTWORTHY | no |
| ai_11_ce_amp.cir | 0 (looks fine) | TRUSTWORTHY | no |
| ai_12_ce_amp_v2.cir | 0 (looks fine) | TRUSTWORTHY | no |
| ai_13_buck.cir | 0 (looks fine) | TRUSTWORTHY | no |
| ai_14_buck_v2.cir | 0 (looks fine) | TRUSTWORTHY | no |
| ai_15_sallen_key.cir | 0 (looks fine) | SUSPECT | YES |
| ai_16_sallen_key_v2.cir | 0 (looks fine) | SUSPECT | YES |
| ai_17_rc_two_stage.cir | 0 (looks fine) | TRUSTWORTHY | no |
| ai_18_rc_two_stage_v2.cir | 0 (looks fine) | TRUSTWORTHY | no |
| ai_19_mirror.cir | 0 (looks fine) | TRUSTWORTHY | no |
| ai_20_mirror_v2.cir | 0 (looks fine) | TRUSTWORTHY | no |

**3 of 19 exit-0 runs (16%) were silently untrustworthy.**

## Overall

**8 of 35 exit-0 runs (23%) were silently untrustworthy across all slices.**
