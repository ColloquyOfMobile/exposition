# Colloquy shield PCB set

All six native KiCad 9 projects implement the simplified 2026-10-04 spec.
Their common footprint library lives here too. No identification chips or I2C
bus remain. Voice headers are keyed 2x3; analyser headers are keyed 2x11.

Build the backplane, five Thomas cards and MSGEQ7 analyser first for the
exhibition. The Teensy adapter, direct analyser and active cards follow.

| Project | Function | Quantity in the full comparison set |
|---|---|---:|
| `backplane/backplane.kicad_pro` | Fixed harness, power and shield slots | 1 |
| `teensy-adapter/teensy-adapter.kicad_pro` | Teensy 4.1 in the Mega computing slot | 1 |
| `analyser-msgeq7/analyser-msgeq7.kicad_pro` | Five original band analysers | 1 |
| `analyser-direct/analyser-direct.kicad_pro` | Five raw-microphone filters | 1 |
| `voice-thomas/voice-thomas.kicad_pro` | Passive original voice, five BOM variants | 5 |
| `voice-active/voice-active.kicad_pro` | Fourth-order voice, thirteen BOM variants | As required |

**Engineering prototypes, not a fabrication release.** Read `REVIEW.md` for
specification discrepancies and unresolved electrical/mechanical issues.
The main `.kicad_pcb` in each project is the routed layout. The `-placed`
files are unrouted regeneration checkpoints, not manufacturing inputs.
The backplane and Teensy adapter use four copper layers; the four audio
designs use two. All are nominally 1.6 mm thick.

Each project includes editable hierarchical schematics, a circuit connectivity
manifest, BOM, component placement CSV and native validation reports.
`ASSEMBLY.md` describes the five Thomas and thirteen active-card populations.
`VALIDATION.json` records ERC, DRC, connectivity and mating checks.
`Shields.pretty` is shared by all six via relative library
paths. Open each `.kicad_pro` to load its local symbol/footprint tables.

Rebuild circuit sources with `scripts/design.py`, then placements with
`scripts/boards.py`, using the Python interpreter shipped with KiCad 9.
These scripts read earlier designs without changing them. Regeneration is
explicit; the board generator never overwrites a routed board.

Routing uses `scripts/route.py` with an official Freerouting 2.4.1 JAR,
using the existing two/four-layer stackups. `scripts/inner_routes.py` is
retained only as a historical tool for the first prototype.
Run `mechanical.py` before routing, then `planes.py`, `finish.py`, `check.py`
and `verify.py`; `labels.py` applies the specified operating text and variant
tables before finishing. `update_simplified.py` is a one-time migration from
the original prototype; do not re-run it on updated boards.
 `trim_stubs.py` removes native-DRC-confirmed dead ends and
must be followed by another plane fill and check. `variants.py` creates assembly variants. Scripts require
KiCad's Python; `check.py` also uses its CLI. Router intermediates belong in
a temporary directory outside this deliverable. Do not run inner_routes.py
twice on an already completed board; restore the outer-route checkpoint first.

No Gerber order package is supplied while the electrical release issues in
`REVIEW.md` remain open. These are editable, routed engineering prototypes.

`positions.csv` is KiCad's SMD-only placement export in mm with its absolute
origin and positive Y pointing up. It includes optional lands: filter it by
the selected variant BOM's Assembly column before use. Through-hole headers,
modules and retention hardware are manually fitted from the assembly drawings.
