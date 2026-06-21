# spiceguard for VS Code

Inline trust checks for SPICE netlists. As you edit a `.cir` / `.net` / `.sp` /
`.spice` / `.ckt` file, this extension runs [`spiceguard`](https://pypi.org/project/spiceguard/)
and surfaces problems — silent/wrong simulation results, missing ground, floating
nodes, source conflicts, convergence culprits — as inline diagnostics.

## Requirements

- **spiceguard** on your PATH: `pip install spiceguard`
- **ngspice** installed (`brew install ngspice` / `apt install ngspice`)

If `spiceguard` isn't found, the extension tells you how to install it.

## What it does

- Runs `spiceguard --json <file>` on save (and on open, configurable).
- Maps each finding to an inline diagnostic, located near the named component or
  node where possible:
  - **Error** — FATAL / SILENT (e.g. `no_ground`, `no_dc_path`, `silent_fallback`)
  - **Warning** — WARN (e.g. `dangling_node`, `kicad_ground_not_zero`)
  - **Information** — INFO
- Command **"spiceguard: Check current netlist"** to run on demand.

## Settings

| Setting | Default | Description |
| --- | --- | --- |
| `spiceguard.enable` | `true` | Enable the checks |
| `spiceguard.path` | `spiceguard` | Path to the spiceguard executable |
| `spiceguard.ngspicePath` | `""` | Optional explicit ngspice path (`--ngspice`) |
| `spiceguard.checkOnOpen` | `true` | Also check when a netlist is opened |

## Notes

A SPICE netlist can contain `.control`/`shell` directives that execute code;
spiceguard (and therefore this extension) runs ngspice on the file, so only open
netlists you trust. See the spiceguard README for details.
