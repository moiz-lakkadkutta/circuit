# spiceguard ⨯ KiCad

**Honest scope:** KiCad has no native "post-simulation" plugin hook, and its
schematic-side Python API is limited. So this is a **command-line / scripting**
integration, not an in-GUI button. It works today and is CI-friendly.

## Requirements

- `spiceguard` (`pip install spiceguard`) and `ngspice`
- `kicad-cli` (ships with KiCad 7+) — only needed to export from a `.kicad_sch`

## The one-liner (pipe form)

Export the schematic's SPICE netlist and check it in one step:

```bash
kicad-cli sch export netlist --format spice board.kicad_sch -o - \
  | spiceguard kicad -
```

`spiceguard kicad` adds a KiCad-specific preflight on top of the normal trust
check — most importantly **`kicad_ground_not_zero`**, the classic gotcha where a
`GND` net isn't mapped to ngspice's required node `0` (which silently floats the
whole circuit).

## The helper script

[`spiceguard_kicad.py`](spiceguard_kicad.py) wraps export + check and accepts
either a schematic or an already-exported netlist:

```bash
python spiceguard_kicad.py board.kicad_sch     # exports via kicad-cli, then checks
python spiceguard_kicad.py exported.cir        # checks an existing netlist
python spiceguard_kicad.py board.kicad_sch --json
```

Exit codes pass through spiceguard: `0` TRUSTWORTHY, `1` FAILED, `2` SUSPECT,
`3` ngspice not found, `64` usage error, `65` kicad-cli missing/failed.

You can also run it from KiCad's built-in **Tools → Scripting Console**.

## In CI (gate a PR on trustworthy sims)

```yaml
- run: pip install spiceguard
- run: sudo apt-get install -y ngspice kicad   # provides kicad-cli + ngspice
- run: python kicad/spiceguard_kicad.py hardware/board.kicad_sch
```

## Why not a PCM plugin / toolbar button?

KiCad's Plugin & Content Manager add-ons target the PCB editor (`pcbnew`)
toolbar; the SPICE netlist and simulator live in the schematic editor
(`eeschema`), which doesn't expose an equivalent plugin point. Rather than ship a
button in the wrong window, the supported path is the CLI/scripting flow above.
If KiCad's IPC API gains schematic coverage, an in-app action can be layered on
top of the same `spiceguard kicad` entry point.
