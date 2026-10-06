# Native KiCad validation — 2026-10-06

KiCad 9.0.7 reports zero ERC violations, zero DRC violations and zero
unconnected items on all four current routed boards. No new DRC exclusions
were used to dismiss routing faults. VALIDATION.json records native-file
hashes and detailed checks. The analyser carrier is pending measurements
and is not included in this passing result.

| Design | Copper layers | ERC | DRC | Unconnected |
|---|---:|---:|---:|---:|
| Backplane | 4 | 0 | 0 | 0 |
| Teensy adapter | 4 | 0 | 0 | 0 |
| Thomas RC voice | 2 | 0 | 0 | 0 |
| MAX9814 microphone | 2 | 0 | 0 | 0 |

Independent manifest / native schematic-netlist / PCB-pad parity covers
715 connected pins with zero differences. Interface checks preserve v2
harness positions/pinout, existing Mega pins, five voice mating pairs,
mirrored adapter contacts, direct microphone networks and the single
AGND/GND bond. Header counts, eight LED polarities, THT pitch-component
spacing, microphone ground pins and mounting-hole/keepout geometry pass.
The carrier's mechanical interface awaits measured module geometry.

The focused specification tests pass: 36 tests (test_shields.py and
test_microphone_board.py). No application or firmware code was changed.
Front/back assembly views were inspected for voice/microphone layouts.
All operating labels remain on silkscreen; some small component references
use the assembly layer and are listed in each reports/silkscreen.json.

These checks establish connectivity and geometric compliance, not acoustic
performance, supply sequencing, current capacity or physical fit. Capsule
pin spacing/part selection is provisional. No fabrication release is issued;
read REVIEW.md and analyser-carrier/README.md before ordering boards.
