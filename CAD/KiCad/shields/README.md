# Colloquy shield PCB set

Updated for SHIELDS.md revision 2d9fe1d and MICROPHONE_BOARD.md (2026-10-05).
All current KiCad 9 projects and their shared library are in this folder.

| Project | Function | Quantity |
|---|---|---|
| backplane | Harness, power, shield slots, eight LEDs and 26 test headers | 1 |
| teensy-adapter | Teensy 4.1 in the Mega slot; three power test headers | 1 |
| voice-thomas | Thomas RC filter for either processor; THT pitch components | 5, more as needed |
| microphone | MAX9814 body microphone, 20 x 62 mm, two M5 holes | 6 (one spare) |
| analyser-carrier | Five purchased DFRobot modules | Pending module measurement |

The active filter is obsolete. One voice layout supports all five Thomas
populations and thirteen new-pitch populations. See ASSEMBLY.md and its BOMs.
The old active voice and bare-chip analyser files are clearly archived under
obsolete/ and are not current build inputs.

Open each current .kicad_pro. Main .kicad_pcb files are routed; -placed files
are unrouted checkpoints. Backplane/adapter use four copper layers; voice/mic
two; nominal thickness is 1.6 mm. Symbols and footprints are local.
Native ERC/DRC, netlist parity and interface results are in VALIDATION.md/json.

Engineering prototypes: no fabrication release or Gerber order package.
The analyser carrier requires actual module measurements. The microphone
capsule's exact stocked part and land pattern must be confirmed. REVIEW.md
lists outstanding physical checks. The old analyser envelope on the backplane
remains provisional until the carrier is sized.

Generation: scripts/design.py, boards.py, variants.py with KiCad's Python.
Routing: scripts/route.py with Freerouting 2.4.1. After routing, run labels.py,
finish.py, planes.py, check.py and verify.py. Preserve mechanical holes and
validated connector positions when regenerating. Historical migration scripts
are one-time tools, not general rebuild commands. Router files stay in tmp/.
positions.csv contains SMD-only placements; fit THT parts manually from BOMs
and assembly views. Filter all populations by their selected BOM.
