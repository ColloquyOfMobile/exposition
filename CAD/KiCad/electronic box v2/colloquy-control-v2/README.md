# Colloquy control PCB v2 — revision A prototype

Open **`colloquy-control-v2.kicad_pro` in KiCad 9**. The project contains the
complete schematic and routed replacement for the electronic-box board. Its
fixed harness and firmware-4 interfaces come from `../NETLIST.md` and
`Source code/Python/colloquy/hardware/electronics/NEXT_PCB.md`.

## Files and editing

- `colloquy-control-v2.kicad_sch`: overview with controller, power, harness,
  I/O, and five audio channel sheets.
- `colloquy-control-v2.kicad_pcb`: canonical board to edit and manufacture.
- `Colloquy.kicad_sym`, `Colloquy.pretty/`, and library tables: local design
  libraries, including recovered custom footprints.
- `circuit.json`: explicit pin-to-net design contract; `footprint-map.json`
  relates upstream identifiers to the local footprints.
- `reports/`: electrical checks, board checks, and inspection exports.
- `manufacturing/`: prototype fabrication and assembly outputs.

`manufacturing/ASSEMBLY_NOTES.md` lists sockets, mating headers, and mounting
hardware in addition to the electrical BOM. It explains the inherited Mega
footprint's position-file convention and the solid ground-pad connections.

Edit the native KiCad files normally. The scripts in `scripts/` are optional
regeneration tools; they do not observe subsequent manual edits. In particular,
`build_schematic.py` regenerates the sheets and circuit contract, while
`build_board.py` produces a separate `-placed.kicad_pcb`. Never overwrite a
manually edited or routed design unintentionally. The repository-root
`next_pcb.py` still generates the older, incomplete planning netlist one
directory above; it does not regenerate this completed project.

## Chosen construction

Two copper layers, nominal 1.6 mm FR-4, 35 µm finished copper per side,
lead-free finish, solder mask both sides, and component legends. Outline:
210 × 297 mm with 5 mm corner radii. Existing connectors, Mega shield, and
U2D2 locations remain fixed. The Mega plugs into the **bottom** of the PCB.

Four additional 3.2 mm M3 standoff holes have 8 mm copper keepouts. Four
existing U2D2 apertures become 4.5 mm NPTH drills; the jack locating aperture
becomes a 1.6 mm NPTH drill. There are no additional large cutouts. See
`../MECHANICAL_REVIEW.md` for coordinates and the dry-fit checks.

Nominal routing: 0.30 mm signals, 0.50 mm analogue supplies/ground,
2.00 mm body-power trunks; 0.25 mm clearance. Standard vias are 0.80/0.40 mm
diameter/drill, with 1.20/0.60 mm vias for body power. The board and Mega
5 V rails remain separate. JP1 is the sole on-board AGND–GND bond.

## Assembly and commissioning

This is a **prototype design**, not a measured replacement-board qualification.
Read `CIRCUIT_NOTES.md` for receiver changes and assembly options. Fit MSGEQ7P
DIP-8 devices in sockets, 1% resistors, and C0G/NP0 33 pF oscillator capacitors.
Use at least 16 V-rated supply capacitors; select filter capacitors with the
stated values, appropriate lead pitch, and preferably 5% tolerance.

1. Print the mechanical drawing at 1:1 and dry-fit the enclosure, connectors,
   Mega underside clearance, U2D2, and new standoffs.
2. Check continuity, polarity, and isolation between BOARD +5V and MEGA_5V.
   Bring up with current-limited supplies before connecting the harness.
3. Measure the provisional 10 kΩ photosensor loads against the installed
   sensors; replace their values where calibration requires it.
4. Verify all five filter outputs and analyser bands using firmware 4. Leave
   microphone attenuation bypasses open until measured headroom permits them.
5. Test a full-length body cable with NeoPixels and servos active. Confirm rail
   voltage drop and connector temperature under the actual load. Initially
   limit each external rail to 2 A total and each powered DSUB branch to 1 A;
   these are commissioning ceilings, not established hardware ratings.

The body amplifiers are external to this PCB. Their supply voltage must follow
the selected module's actual rating; the previously damaged GF1002 is not
assumed to accept 12 V. This design preserves both existing harness rails.

## Reproducibility and library provenance

Use KiCad's bundled Python for PCB scripts because it includes `pcbnew`.
Run `export_release.py` with an ordinary Python installation; the Windows
KiCad-bundled interpreter can cause its CLI child process to fail at startup.
Routing uses Freerouting 2.4.1 with a separately supplied Java 25 runtime; the
script runs locally with network services and analytics disabled. It preserves
the placed input and requires a different output filename. DRC and exported
netlist comparison must be repeated after design edits.

`scripts/export_release.py` runs ERC, DRC, native schematic/PCB parity, and
the explicit circuit-contract comparison before generating fabrication files.
Any reported error or warning stops export. It also verifies all nine NPTH
drill hits by diameter and coordinate. Use the generated Gerber ZIP for the
fabricator; its contents come exclusively from that export run. Release hashes
cover every schematic sheet, the board, project settings, and local libraries.

Standard footprints derive from the KiCad 9 library, maintained by the KiCad
community under [CC-BY-SA 4.0 with the KiCad exception](https://www.kicad.org/libraries/license/).
Custom jack, bridge, U2D2, and Mega geometry derives from the existing project;
the source identifiers are retained in `circuit.json`. The jack retention pads
have enlarged annular rings, and round mechanical apertures were converted to
NPTH pads. Standard 3D models use KiCad's optional model installation. Custom
device 3D bodies are absent; the 3D view does not establish enclosure fit.
