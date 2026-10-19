# Native KiCad validation — carrier updated 2026-10-19

KiCad 9.0.7 reports zero ERC violations, zero DRC violations and zero
unconnected items on all five current routed boards. No new DRC exclusions
were used to dismiss routing faults. VALIDATION.json records native-file
hashes and detailed checks. The carrier is included electrically and geometrically; physical module fit
remains unverified because its mounts were inferred from photographs.

| Design | Copper layers | ERC | DRC | Unconnected |
|---|---:|---:|---:|---:|
| Backplane | 4 | 0 | 0 | 0 |
| Teensy adapter | 4 | 0 | 0 | 0 |
| Thomas RC voice | 2 | 0 | 0 | 0 |
| MAX9814 module holder, rev B | 2 | 0 | 0 | 0 |
| DFR0126 carrier | 2 | 0 | 0 | 0 |

Independent manifest / native schematic-netlist / PCB-pad parity covers
751 connected pins with zero differences (26 on the revised holder). Interface checks preserve v2
harness positions/pinout, existing Mega pins, five voice mating pairs,
front-mounted mirrored Mega contacts, unchanged adapter alignment, direct microphone networks and the single
AGND/GND bond. Header counts, eight LED polarities, THT pitch-component
spacing, microphone module contact mapping and mounting-hole/keepout geometry pass.
Holder M1 contacts and both M2 mounts match the rotated local module reference;
its M5 artwork interface remains 50mm/5.5mm NPTH. Native holder ERC/DRC and
unconnected counts are all zero, with 64 tracks/vias and no exclusions.
The carrier's JA1 and retention coordinates match the backplane. All five
module socket pinouts, photo-derived pad coordinates and round/slot drilling
geometry pass independent checks. The carrier now requires modified modules:
remove R3 and jumper R to OUT, with the microphone on L; there are no
module-to-carrier cables. The carrier was re-routed and its native ERC/DRC
and schematic/PCB parity rechecked on 2026-10-19: zero violations and zero
unconnected items. Existing pad positions and mechanical geometry are preserved.
Actual module fit is photo-derived and remains a physical check.

The updated backplane also passes native housing pad/via keepouts and +12V
outer-layer/2mm-minimum rules. Independent checks compare every Mega contact
with the mirrored v2 coordinates and all four computing mounts with the
unchanged adapter. The slim-front mounting footprints require <=4mm OD
front posts/spacers and rear screw heads; hardware fit remains a dry-fit check.

The 2026-10-13 revision moves CM1-CM5 to the adapter front, beside and clear
of the Teensy socket courtyard, with rerouted microphone branches and ground
returns. All five active boards again pass native ERC/DRC with zero violations,
zero unconnected items and zero schematic/PCB parity differences. Independent
verification now rejects any SMD footprint on the back. Front assembly artwork
was visually inspected. Manufacturer ZIPs were regenerated and their archived
file hashes and integrity checked; voice cards and the analyser carrier contain
no machine-placement file or stencil. Only front paste and front SMD placements
are supplied for the three outsourced boards. Production adapter Gerbers were
also regenerated from the checked PCB.

The 2026-10-13 focused and full pytest runs could not collect: the available
Python 3.10 test environment lacks pandas (full run: 65 collection errors).
No application or firmware behavior was changed.

On 2026-10-19 the full suite passed: **1,796 tests** with pandas supplied
from temporary test dependencies. Local socket and temporary archive tests
were run outside the sandbox. Both carrier fabrication packages match the
new source digest; ZIP payload hashes and refreshed 1:1 print scale bars pass.

The previous focused specification tests passed: 37 tests (test_shields.py and
test_microphone_board.py). No application or firmware code was changed.
The full repository pytest suite also passes: 1,665 tests on 2026-10-08.
Front/back assembly views were inspected for voice/microphone layouts;
the carrier front assembly drawing is also inspected.
All operating labels remain on silkscreen; some small component references
use the assembly layer and are listed in each reports/silkscreen.json.

These checks establish connectivity and geometric compliance, not acoustic
performance, supply sequencing, current capacity or physical fit. The violet
module's actual hole/header grid, socket/spacer height and screw fit remain
physical checks. No fabrication release is issued;
read REVIEW.md and analyser-carrier/README.md before ordering boards.
