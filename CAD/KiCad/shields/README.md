# Colloquy shield PCB set

All six native KiCad 9 projects and their common footprint library live here.

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
The `-placed.kicad_pcb` files are staging layouts. Routing and validation status
must be read from the reports; an outline and placed footprints are not a
finished PCB. No manufacturing files should be ordered from staging layouts.

Each project includes editable hierarchical schematics, a circuit connectivity
manifest and a BOM. `Shields.pretty` is shared by all six via relative library
paths. Open each `.kicad_pro` to load its local symbol/footprint tables.

Rebuild circuit sources with `scripts/design.py`, then placements with
`scripts/boards.py`, using the Python interpreter shipped with KiCad 9.
These scripts read earlier designs without changing them. Regeneration is
explicit; the board generator never overwrites a routed board.
