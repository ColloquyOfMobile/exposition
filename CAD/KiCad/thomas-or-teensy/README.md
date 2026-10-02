# Colloquy — Thomas or Teensy

Open **`thomas-or-teensy.kicad_pro`** in KiCad 9. The native root schematic is
`thomas-or-teensy.kicad_sch`, and the main PCB is `thomas-or-teensy.kicad_pcb`.
The `-placed.kicad_pcb` is the preserved placement before routing. All schematic
symbols and footprints are project-local; no third-party KiCad plugin is needed.

This implements `Source code/Python/colloquy/hardware/electronics/THOMAS_OR_TEENSY.md`
in a separate project. Read **[REVIEW.md](REVIEW.md)** for the identified specification
problems, exact substitutions, verified pinouts and remaining hardware checks.
The v2 project and the original specification are not modified.

The board contains five SMD Thomas filter/MSGEQ7 channels, three PCM5102A DACs,
six buffered Teensy microphone inputs, three mode relays, two Teensy sockets,
bench connectors and protected MODE/UART crossings. The original harness,
Mega underside footprint, U2D2 mount and enclosure interface are preserved.
The finished PCB has **four copper layers at 1.6mm overall thickness**: signals
on the two outer layers and split AGND/GND planes on the two inner layers.
The preserved `-placed` file is the two-layer input to the routing stage.

`reports/schematic.pdf` and `reports/board-preview.png` are review views.
`reports/validation-summary.json`, ERC, DRC and connectivity reports record the
actual verification state; **a preview is not a fabrication release**. This is
a review prototype, and physical operation has not been tested.

## Assembly

- Fit the original fixed connectors, Mega mating headers underneath, and two
  24-way Teensy sockets on top. JT1/JT2 pin1 is at the USB end; follow GPIO names
  in the schematic, not socket pad numbers. Teensy gets its own USB power.
- Fit all three non-latching relays even for Thomas-only use. JM1 pins1–2 select
  Thomas, pins2–3 select Teensy; no shunt selects Thomas. Stop sound first.
- Fit MSGEQ7N SOIC-8 parts from an authorised source. JS1–JS5 stay **open**.
  The photosensor loads RP1–RP11 are provisional 10k in replaceable 1206 cases.
- Use PPS/C0G parts for the Thomas filters; the 470nF stages are three parallel
  parts each. Do not substitute X7R. Follow the PPS solder-paste and reflow limits.
- JP1 is the sole carrier AGND/GND bond. Do not add a second ground strap.
  Keep USB shields/external ground paths in mind during bench measurements.
- Bench output is line level for a powered speaker. The external body amplifier
  and its permitted rail are not selected by this board.
- `assembly/bom.csv` includes ordering descriptions and the plug-in Teensy/shunt.
  Common passives still require procurement choices meeting the stated package,
  value, dielectric, tolerance and voltage rating. Copper-only test points and
  open solder jumpers are not purchased components.

## Regeneration and checking

Native files can be edited normally. Scripts **do not preserve manual edits**;
use them only when deliberately regenerating this design. Use KiCad's bundled
Python for board scripts, and ordinary Python for `export_review.py`.

1. `build_design.py` writes the circuit contract and schematic.
2. `build_board.py` writes the separate `-placed` board and local footprints.
3. Call `build_design.schematic()` on the saved contract to update the schematic
   with the vendored footprint identifiers. Do not rebuild the original contract
   between placement and this call.
4. `route_board.py` takes explicit input/output paths, a local Freerouting JAR
   and Java runtime. It never overwrites its input. Routing is not validation.
5. `complete_routing.py` widens automatic neck-downs to 0.20mm, connects the
   two translator DIR supply branches, and routes the relay return around the
   analog region. Run it once on the fresh imported route; it changes copper.
   `route_coil_supply.py` moves the matching 2mm supply trunk around that region.
6. `route_clocks.py` brings the five I2S crossings beside JP1 and moves the
   clock test points alongside that crossing.
7. `finish_board.py` adds the two internal ground planes, fills the separate
   ground regions, assigns intentional NC
   nets and arranges silkscreen. Run final checks after any change to copper.
8. `check_design.py` runs seven independent interface/pinout/mechanical checks.
   `verify_schematic.py` compares exported native schematic nets with both the
   circuit contract and every PCB pad.
9. `audit_copper.py` measures widths and routing lengths;
   `check_clock_ground.py` samples the actual inner-plane coverage.
   `check_coil_supply.py` checks the physical supply path to all three coils.
   `export_review.py` refreshes the review package and records all findings.

Standard footprints derive from KiCad 9 under its library licence; see
`Colloquy.pretty/KICAD-LICENSE.md`. Fixed custom geometry comes from the v2
project. `PPS_6041` is drawn from Panasonic's recommended land pattern.
The preview lacks some custom/module 3D bodies, so it cannot establish fit.
