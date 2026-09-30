# Revision A design-file validation

Verified with KiCad 9.0.7 on 2026-09-30.

| Check | Result |
| --- | --- |
| Electrical rules, all ten schematic sheets | 0 violations |
| PCB design rules, including filled zones | 0 violations |
| Open PCB connections | 0 |
| Native schematic/PCB parity | 0 findings |
| Circuit contract / exported netlist / PCB pad comparison | 376 connected pads, 106 functional nets; exact match |
| Intentional unused controller pads | 48 explicitly named NC nets |
| Original mating connector drilling and new mounting geometry | All 30 independent checks pass |
| NPTH drill export | All nine centres and diameters match the design |
| Released native files and fabrication ZIP | SHA-256 manifest verified |

The board has 132 footprints (128 circuit items and four standoffs), 1,235
track segments, and 59 vias. Nominal signal routing is 0.30 mm; two short
connector-area clearances use 0.28 mm tracks, above the 0.25 mm design minimum.
Via drills are at least 0.40 mm. There are no ERC or DRC exclusions.

External +5 V, +12 V, and GND power routes stay outside the central audio
rectangle and are locked. Separate front/back AGND pours include the audio
channels and sensor-load bank. JP1 is the intended sole on-board AGND–GND
component bond. Perimeter GND fills surround that region. All filled-copper
checks pass; the sensor loads and selected ground pads use solid connections
where thermal reliefs could not form complete spokes.

The top-side render and assembly plots were inspected. The assembly sheets
use A3 portrait at nominal 1:1 scale; disable printer scaling for the dry-fit.
Custom Mega, U2D2, bridge, and jack 3D bodies are absent from the render.

These checks establish consistency and manufacturable geometry of the files.
They do not establish real enclosure fit, cable noise performance, photosensor
calibration, amplifier supply ratings, or harness current capacity. Follow
the project README and manufacturing assembly notes for prototype bring-up.

Machine-readable evidence: `erc.json`, `drc.json`, `connectivity-parity.json`,
`final-geometry-review.json`, `npth-drill-check.json`, and `release-hashes.json`.
`routing-summary.json` records the routing checkpoint before zone filling;
`drc.json` is the final board check.
