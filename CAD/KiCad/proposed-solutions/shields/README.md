# Colloquy shield PCB set

Updated for SHIELDS.md revision d076edc (2026-10-13) and MICROPHONE_BOARD.md.
All current KiCad 9 projects and their shared library are in this folder.

Matching functional pinouts show signal origins and destinations around a
rectangle, with processor pins in its centre:
[Arduino Mega](<../../../../Source code/Python/colloquy/server2/static/hardware/shields-mega-pinout.svg>)
and [Teensy](<../../../../Source code/Python/colloquy/server2/static/hardware/shields-teensy-pinout.svg>).
`SHIELDS.md` section 1a shows both. Regenerate from the repository root with
`py export_shields_pinout.py`; the generator checks its mapping against the PCBs.

| Project | Function | Quantity |
|---|---|---|
| backplane | Harness, power, shield slots, eight LEDs and 26 test headers | 1 |
| teensy-adapter | Teensy 4.1 in the Mega slot; three power test headers | 1 |
| voice-thomas | Thomas RC filter for either processor; THT pitch components | 5, more as needed |
| microphone-flex | Rev C MAX9814 holder, 32 x 62 mm, left/right/up module sockets, removable selectors | 6 (one spare) |
| analyser-carrier | Five converted DFRobot modules, direct plug-in sockets | 1 |

The active filter is obsolete. One voice layout supports all five Thomas
populations and thirteen new-pitch populations. See ASSEMBLY.md and its BOMs.
The old active voice and bare-chip analyser files are clearly archived under
../../old-reference/superseded-shields/ and are not current build inputs.

Open each current .kicad_pro. Main .kicad_pcb files are routed; -placed files
are unrouted checkpoints. Backplane/adapter use four copper layers; voice/mic
two; nominal thickness is 1.6 mm. Symbols and footprints are local.
Native ERC/DRC, netlist parity and interface results are in VALIDATION.md/json.

Current order packages are in ../../production/assembly/; see ../../README.md.
The analyser carrier uses user-authorized photo-derived mounts with tolerance slots; confirm fit with its 1:1 template. The microphone
module's actual pin/hole grid and seated connector height must be confirmed. REVIEW.md
lists outstanding physical checks. The carrier retains the original 150 x 55mm backplane envelope and retention points.

Generation: scripts/design.py, boards.py, variants.py with KiCad's Python.
The analyser carrier has its own generator, scripts/carrier.py; the microphone
holder is microphone-flex/microphone-flex.kicad_pcb; its README documents the
approved placement, routing and initial selector settings. The old holder generator
is historical and must not replace the selected flex board.
Routing: scripts/route.py with Freerouting 2.4.1. After routing, run labels.py,
finish.py, planes.py, check.py and verify.py. Preserve mechanical holes and
validated connector positions when regenerating. Historical migration scripts
are one-time tools, not general rebuild commands. Router files stay in tmp/.
positions.csv contains front SMD placements for outsourced boards; fit THT parts manually from BOMs
and assembly views. Filter all populations by their selected BOM.

All SMD parts are on the front. The adapter's CM1-CM5 are beside the Teensy
socket, clear of its body. Outsource front SMD assembly for the backplane,
adapter, voice card (R3) and flex microphone holder. Current manufacturing ZIPs
include exact SMD BOMs and matching CPL files. Fit through-hole parts and modules
by hand; the analyser carrier has no SMD population.

## Microphone on the module's L input — 2026-10-19

Each DFRobot module now takes its microphone on L, so the conversion moves to
the right channel: remove R3 (the right-input 22K) and jumper the isolated R
to OUT. The carrier schematic, routed copper, silkscreen and fabrication
packages now follow SHIELDS.md 4b and analyser-carrier/README.md
(RELEASE_REVIEW.md F7, resolved). All module and retention positions are preserved.

## Front computing slot and servo supply — 2026-10-08

The 2026-10-08 backplane also puts the computing slot on the DSUB/front face,
mirrored about x=167.83 mm, with holes matching the unchanged Teensy adapter.
USB/jack rule areas exclude pads and vias. Computing-slot spacers must be
round and <=4 mm OD on the front, with screw heads on the rear (ASSEMBLY.md).
+12V is routed at >=2 mm entirely on outer copper, enforced by native DRC
rules and independent verification.

## Direct-plug carrier revision — 2026-10-07

The analyser carrier now uses female sockets beneath modified modules. No
module-to-carrier leads remain. Each module requires removal of its left-input
22K resistor R4, an on-module jumper from isolated L to OUT, and downward
male headers (since 2026-10-19: R3 and R instead, above). Read
analyser-carrier/README.md before assembly. Socket positions
are photo-derived; check all contacts against the updated 1:1 template.

## Restored enclosure mounts — 2026-10-21

The backplane now retains the four original 8 mm enclosure cutouts recovered
from `CAD/KiCad/old-reference/original-supplied-boards/electronic box/`. Their centres are measured from the
outside board envelope, preserving the original pattern exactly. TPL3 moved
locally and affected tracks were rerouted to clear the centre and left holes.
See [the dimensions and transfer notes](<backplane/ENCLOSURE_MOUNTING.md>) and
[the mounting layout](<backplane/enclosure-mounting-layout.svg>).
After regenerating a staging board, run `scripts/restore_enclosure_holes.py`
before routing; rerun DRC and export fabrication files after any layout edit.
