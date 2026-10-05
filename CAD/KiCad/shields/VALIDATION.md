# Native KiCad validation — 2026-10-05

KiCad 9.0.7 reports **zero ERC violations, zero DRC violations and zero
unconnected items on all five routed boards**. No DRC exclusions were added
to dismiss routing faults. `VALIDATION.json` contains the detailed results
and SHA-256 hashes of the checked native files.

The independent comparison covers 840 connected pins across the circuit
manifests, exported native schematic netlists and actual PCB pads. It also
checks the unchanged v2 harness coordinates/pinout, all previously connected
Mega contacts, all five voice mating pairs, the MSGEQ7 mating pair,
the mirrored adapter contacts, the revised Teensy A10-A15 mapping, removal
of identification hardware and the single passive backplane ground bond.
The five direct microphone resistor/capacitor networks, new D26-D30 contacts,
MSGEQ7 USB-5V supply and disconnection of its signals from the Teensy are
checked explicitly. All checks pass. The existing shield-spec pytest suite also passes: 28 tests.

This revision uses 2x3 voice connectors (key 6), 2x11 analyser connectors
(key 22), and silkscreen identification with complete voice population tables.
It is not connector-compatible with the initial EEPROM-equipped prototype.

| Design | Copper layers | ERC | DRC | Unconnected |
|---|---:|---:|---:|---:|
| Backplane | 4 | 0 | 0 | 0 |
| Teensy adapter | 4 | 0 | 0 | 0 |
| MSGEQ7 analyser | 2 | 0 | 0 | 0 |
| Thomas voice | 2 | 0 | 0 | 0 |
| Active voice | 2 | 0 | 0 | 0 |

Each `reports/` folder contains native JSON checks, schematic SVGs, a top
copper preview and front/back assembly drawings. Back assembly drawings
are viewed through the board; use KiCad's bottom view when assembling.
Schematic symbols and all footprints are local to this folder. Some compact
card references are on the assembly layer because there is insufficient
clear silkscreen space; `silkscreen.json` lists them.

These checks establish file connectivity and geometric design-rule compliance.
They do not establish powered-off isolation, acoustic response, EMC, current
capacity, component availability, connector mating height or enclosure fit.
Read `REVIEW.md` before releasing manufacturing artwork. No hardware was
connected or exercised, and the application/firmware was not changed.
