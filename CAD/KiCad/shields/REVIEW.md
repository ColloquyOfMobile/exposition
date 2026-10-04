# SHIELDS specification review — 2026-10-04

Source: `Source code/Python/colloquy/hardware/electronics/SHIELDS.md`, dated
2026-10-03, and the completed v2 circuit and fixed mechanical geometry.
This directory contains six PCB projects; the Mega and U2D2 are purchased
modules, not additional PCB designs. Existing installation harness boards do
not change. Firmware 5 is separate work and has not been implemented here.

## Corrections and explicit interpretations

* The final paragraph says “four small projects” but lists five. There are
  **six designs including the backplane**.
* Voice slot order is female1, female2, female3, male1, male2. Some examples in
  section 3 use historical component numbering instead. The implementation
  follows net names and the v2 circuit: female1 is R303, female2 R403, female3
  R503, male1 R103, male2 R203. The same mapping applies to the analyser ICs.
* The 2x7 and 2x12 slot footprints have no last pad/pin. The sockets must have
  that cavity blocked. Pin coordinates are specified in the board's top view;
  socket assembly is on the card's underside. The mating coordinate check is
  authoritative; do not substitute a socket by footprint name alone.
* Cards are 30 x 42 mm (the specification says “about 30 x 40”). Both voice
  designs use identical connector and retention coordinates. Both analysers
  use a 150 x 55 mm outline and identical connector/two retention coordinates.
* The adapter's contact coordinates are mirrored from v2 into its own
  component-side view, since its components face away from the backplane.
  The six ICSP positions are omitted, as required by section 5b. The Mega
  footprint's physical pad numbers are distinct from Teensy socket numbers.
* The Thomas card has three capacitor lands in parallel per stage. The 470nF
  variant uses 220nF PPS + 220nF PPS + 30nF C0G. The other populations use the
  same PCB. This retains the exact specified capacitances without inventing a
  470nF PPS orderable part. Unused lands are DNP, not jumpers.

## Manufacturer checks

* TI's [SN74LV4T125 datasheet](https://www.ti.com/lit/ds/symlink/sn74lv4t125.pdf)
  specifies 3.3-to-5V translation and partial-power-down Ioff support. The
  adapter uses SN74LV4T125PWR in TSSOP-14, USB-derived VIN supply, grounded
  active-low enables, and grounded unused input. Each package has 100nF bypass.
* ST's [M24C02-R datasheet](https://www.st.com/resource/en/datasheet/m24c02-r.pdf)
  defines E0/E1/E2 address inputs. M24C02-RMN6TP is the selected SO8 part;
  voice addresses come from the slot and analyser straps select 0x55.
  A 10k write-protect pull-up and normally open programming jumper are fitted.
* [MSGEQ7 manufacturer datasheet](https://mix-sig.com/images/datasheets/MSGEQ7.pdf):
  supply 2.7–5.5V; pin 6 is its internal reference and is bypassed, never tied
  directly to ground. The oscillator resistor is supplied from IOREF.
* [MCP6024](https://www.microchip.com/en-us/product/mcp6024) is the 10MHz
  rail-to-rail active-card amplifier; [MCP6004](https://www.microchip.com/en-us/product/MCP6004)
  is the direct analyser's 1MHz amplifier. Both use the SOIC-14 quad pinout.
* [PJRC Teensy 4.1](https://www.pjrc.com/store/teensy41.html) documents the
  3.3V-only input range and USB/VIN power constraint. The adapter draws from
  VIN; it never feeds VIN. A Schottky points from VIN toward MEGA_5V.
  The selected [Diodes 1N5819HW](https://www.diodes.com/part/view/1N5819HW)
  is SOD-123; this avoids assigning the larger SS14 package to SOD-123 lands.
* The project-local PPS footprint is the earlier reviewed Panasonic 6041
  pattern. See the [Panasonic ECHU catalogue](https://mediap.industry.panasonic.eu/assets/imported/industrial.panasonic.com/cdbs/www-data/pdf/RDI0000/ABD0000C173.pdf).

## Specification issues that prevent an unconditional fabrication release

The statement that independently powered domains can never partially power
one another is stronger than the specified circuit supports:

1. Eleven 100k/150k dividers limit current from live photosensors into an
   unpowered Teensy, but do not isolate its pin clamps. Nominal current limits
   are not a proof against phantom powering, including the aggregate current.
2. The direct analyser is DC coupled from externally powered microphones into
   IOREF-powered op-amps. Its 10k input resistor limits injection; the op-amp
   is not specified as a powered-off isolator.
3. The active card can receive a USB-powered 5V square while its own +5V rail
   is off. Its 15k input resistor likewise limits current without isolation.

The schematics implement the specified networks faithfully. These cases need
an agreed power-sequencing constraint or added powered-off isolation before
release. The older Thomas/Teensy project's TMUX1511 solution is a relevant
starting point, not evidence that this unswitched circuit has been qualified.

The inherited backplane Mega footprint omitted its mounting holes. Four
peripheral 3.2mm holes are now added to both mating boards from Arduino's
official `MEGA2560_Rev3e.brd` CAD, with exact transforms recorded in
`mechanical.json`. Its two optional central holes are unused.

Still outstanding: enclosure front/back height, gold-contact part numbers,
keying plugs, stack heights, high-value C0G stock, photosensor calibration,
rail/current budget and the harness measurements remain physical checks.

The backplane is four-layer: F.Cu signals, In1.Cu GND, In2.Cu +5V with two
photosensor routes, B.Cu signals and local AGND. The Teensy adapter is also
four-layer: F.Cu signals, In1.Cu GND, In2.Cu a congested tone route, B.Cu
signals/GND. Audio cards are two-layer with an AGND pour. JP1 is still the
single passive GND/AGND bond. Plane connections are solid; finished copper
weight, laminate construction and permissible temperature rise must be set
with the fabricator. DRC does not qualify the 12V harness current or vias.

No hardware is attached or exercised by the generation and validation scripts.
ERC/DRC results cannot establish the powered-off, acoustic or mechanical tests
above. Follow SHIELDS.md section 13 for assembly and bring-up order.
