# Silent-failure benchmark

| netlist | ngspice exit | spiceguard verdict | silent lie? |
|---|---|---|---|
| n1_missing_ground.cir | 0 (looks fine) | SUSPECT | YES |
| n2_floating_node.cir | 0 (looks fine) | SUSPECT | YES |
| n3_ideal_switch_smps.cir | 1 | FAILED | no |
| n4_bsource_singular.cir | 1 | FAILED | no |
| n5_healthy_control.cir | 1 | FAILED | no |
| n6_source_conflict.cir | 1 | FAILED | no |
| n7_relaxation_osc.cir | 1 | FAILED | no |
| n8_stacked_sources.cir | 0 (looks fine) | TRUSTWORTHY | no |
| astable_multivibrator.cir | 1 | FAILED | no |
| bridge_rectifier.cir | 1 | FAILED | no |
| ce_amplifier.cir | 1 | FAILED | no |
| kicad_export.cir | 0 (looks fine) | SUSPECT | YES |
| kicad_gnd.cir | 0 (looks fine) | SUSPECT | YES |
| kicad_subckt.cir | 0 (looks fine) | TRUSTWORTHY | no |
| sub_dcpath.cir | 0 (looks fine) | TRUSTWORTHY | no |
| sub_floating.cir | 0 (looks fine) | SUSPECT | YES |
| sub_include.cir | 1 | FAILED | no |
| sub_nested.cir | 0 (looks fine) | TRUSTWORTHY | no |
| sub_twoinst.cir | 0 (looks fine) | TRUSTWORTHY | no |
| sub_undefined.cir | 1 | FAILED | no |
| ai_01_divider.cir | 0 (looks fine) | TRUSTWORTHY | no |
| ai_02_divider_v2.cir | 0 (looks fine) | TRUSTWORTHY | no |
| ai_03_rc_lpf.cir | 1 | FAILED | no |
| ai_04_rc_lpf_v2.cir | 1 | FAILED | no |
| ai_05_led.cir | 0 (looks fine) | TRUSTWORTHY | no |
| ai_06_led_v2.cir | 0 (looks fine) | TRUSTWORTHY | no |
| ai_07_relax_osc.cir | 1 | FAILED | no |
| ai_08_relax_osc_v2.cir | 1 | FAILED | no |
| ai_09_rectifier.cir | 1 | FAILED | no |
| ai_10_rectifier_v2.cir | 1 | FAILED | no |
| ai_11_ce_amp.cir | 0 (looks fine) | TRUSTWORTHY | no |
| ai_12_ce_amp_v2.cir | 0 (looks fine) | TRUSTWORTHY | no |
| ai_13_buck.cir | 1 | FAILED | no |
| ai_14_buck_v2.cir | 1 | FAILED | no |
| ai_15_sallen_key.cir | 1 | FAILED | no |
| ai_16_sallen_key_v2.cir | 1 | FAILED | no |
| ai_17_rc_two_stage.cir | 1 | FAILED | no |
| ai_18_rc_two_stage_v2.cir | 1 | FAILED | no |
| ai_19_mirror.cir | 0 (looks fine) | TRUSTWORTHY | no |
| ai_20_mirror_v2.cir | 0 (looks fine) | TRUSTWORTHY | no |

**5 of 18 exit-0 runs (28%) were silently untrustworthy.**
